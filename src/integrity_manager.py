import re
import os
import json
from time import time, sleep
from inputimeout import inputimeout, TimeoutOccurred
from src.spotify_helper import SpotifyHelper

class IntegrityManager:

    def __init__(self, logger, api, config):
        self.logger = logger.getChild('IntegrityManager')
        self.api = api
        self.config = config
        self.spotify_helper = SpotifyHelper(self.logger, api=self.api)

        # to avoid uncertainty of whether a forward slash needs to be appended to the backup path
        while self.config['BACKUP_PATH'][-1] == '/':
            self.config['BACKUP_PATH'] = self.config['BACKUP_PATH'][:-1]


    def run(self, playlist):
        pl_id = self.spotify_helper.get_playlist_id(playlist)
        self.logger.info('Verifying integrity of playlist with ID \'%s\'', pl_id)

        latest_backup = self.find_latest_backup(pl_id)
        if latest_backup is None:
            self.logger.info('Playlist with ID \'%s\' currently has no backup for comparison', pl_id)
            self.backup_playlist(pl_id)
            return

        removals = self.get_removals(pl_id, latest_backup)
        try:
            unapproved_removals = self.get_unapproved_removals(removals, latest_backup['name'])
        except TimeoutOccurred as err:
            self.logger.warning('No response given for an approval request')
            self.logger.warning('Skipping track restoration for playlist with ID \'%s\' until next run', pl_id)
            return

        if isinstance(unapproved_removals, list) and len(unapproved_removals) > 0:
            try:
                self._restore_removals(pl_id, unapproved_removals)
            except Exception as err:
                self.logger.error('Failed to restore unapproved removals. Error: \'%s\'', err)
                return
            else:
                self.logger.info('Successfully restored unapproved removals')

        self.backup_playlist(pl_id)
        self.manage_redundant_backups(pl_id)
        self.logger.info('Integrity of playlist with ID \'%s\' has been verified', pl_id)


    def find_latest_backup(self, playlist_id):
        backup_files = os.listdir(self.config['BACKUP_PATH'])
        relevant_backups = []
        for backup in backup_files:
            match = re.search('^%s_[0-9]{10}\.[0-9]+\.backup\.json$' % playlist_id, backup)
            if match is not None:
                ts_span = re.search('[0-9]{10}.[0-9]+', backup).span()
                relevant_backups.append({
                    'filename': '%s/%s' % (self.config['BACKUP_PATH'], backup),
                    'timestamp': float(backup[ts_span[0] : ts_span[1]])
                })

        if len(relevant_backups) == 0:
            return None

        relevant_backups.sort(reverse=True, key=lambda x: x['timestamp'])
        return self._load_backup_from_file(relevant_backups[0]['filename'])


    def get_removals(self, playlist_id, backup_info):
        current_items = self.spotify_helper.get_all_items_in_playlist(
            playlist_id, fields='items.track(uri)', api=self.api)
        removals = []

        for backup_item in backup_info['items']:
            still_in_playlist = False

            for current_item in current_items:
                if backup_item['uri'] == current_item['track']['uri']:
                    still_in_playlist = True
                    break
            if not still_in_playlist:
                removals.append(backup_item)

        return removals


    def get_unapproved_removals(self, removals, playlist_name):
        unapproved = []
        for removal in removals:
            try:
                if not self._user_approves_removal(removal, playlist_name, 20):
                    unapproved.append(removal)
            except TimeoutOccurred as err:
                raise err
        return unapproved


    def backup_playlist(self, playlist_id):
        playlist_info = self.api.playlist(playlist_id, fields='name')
        playlist_items = self.spotify_helper.get_all_items_in_playlist(
            playlist_id, fields='items(track(name,uri, artists.name)),total', api=self.api)
        formatted_items = []

        self.logger.info("Backing up playlist with ID \'%s\'", playlist_id)
        for item in playlist_items:
            formatted_items.append({
                'name': item['track']['name'],
                'artists': self._get_artists_string([
                    artist['name'] for artist in item['track']['artists']
                ]),
                'uri': item['track']['uri'],
                'position': item['position']
            })

        backup = {
            'name': playlist_info['name'],
            'items': formatted_items
        }

        backup_file_path = '%s/%s_%s.backup.json' % (self.config['BACKUP_PATH'], playlist_id, str(time()))
        self.logger.debug('Saving backup \'%s\'', backup_file_path)
        backup_file = open(backup_file_path, 'w')
        backup_file.write(json.dumps(backup))
        backup_file.close()
        sleep(0.2) # for stability
        self.logger.info("Completed backup of playlist with ID \'%s\'", playlist_id)


    def manage_redundant_backups(self, playlist_id):
        desired_num_backups = self.config['MAX_BACKUPS_PER_PLAYLIST']
        backup_files = os.listdir(self.config['BACKUP_PATH'])
        timestamp_re = '[0-9]{10}\.[0-9]+'
        filename_re = '^%s_%s\.backup\.json$' % (playlist_id, timestamp_re)
        relevant_backups = []

        for filename in backup_files:
            if re.search(filename_re, filename) != None:
                ts_match_span = re.search(timestamp_re, filename).span()
                relevant_backups.append({
                    'filename': '%s/%s' % (self.config['BACKUP_PATH'], filename),
                    'timestamp': float(filename[ts_match_span[0] + 1 : ts_match_span[1]])
                })

        num_backups = len(relevant_backups)
        if num_backups > desired_num_backups:
            self.logger.info('Playlist with ID \'%s\' has more backups than the desired maximum', playlist_id)
            self.logger.info('Deleting redundant backups for playlist with ID \'%s\'', playlist_id)

            # as expected, the oldest, most out-of-date backups are deleted
            relevant_backups.sort(key=lambda x: x['timestamp'], reverse=False)
            for index in range(0, num_backups - desired_num_backups):
                self.logger.debug('Deleting backup \'%s\'', relevant_backups[index]['filename'])
                os.remove(relevant_backups[index]['filename'])
            self.logger.info('Completed deletion of redundant backups for playlist with ID \'%s\'', playlist_id)


    def _user_approves_removal(self, removal, playlist_name, timeout_after_secs):
        try:
            input = inputimeout(prompt='Do you approve the removal of \'%s - %s\' from playlist \'%s\'? (Y/n): '
                                % (removal['artists'], removal['name'], playlist_name), timeout=timeout_after_secs)
            if input in ['Y', 'y', 'YES', 'Yes', 'yes']:
                return True
        except TimeoutOccurred as err:
            raise err
        return False


    def _get_artists_string(self, artist_names):
        combined = ''
        for name in artist_names:
            combined += '%s, ' % name
        if combined != '':
            combined = combined[:-2]
        return combined


    def _restore_removals(self, playlist_id, removals):
        for removal in removals:
            self.logger.info('Restoring track \'%s\'', removal['name'])
        self.spotify_helper.add_items_to_playlist(playlist_id, removals)


    def _load_backup_from_file(self, filename):
        if not os.path.isfile(filename):
            self.logger.error('Backup file \'%s\' does not exist', filename)
            return None

        backup_file = open(filename, 'r')
        backup_info = None
        try:
            backup_info = json.loads(backup_file.read())
        except json.JSONDecodeError as err:
            self.logger.error('Backup file \'%s\' is invalid JSON. Error: \'%s\'', filename, err)
            return None
        except Exception as err:
            self.logger.error('Could not read backup file \'%s\'. Error: \'%s\'', filename, err)
            return None
        finally:
            backup_file.close()

        return backup_info if self._backup_info_is_valid(backup_info, filename) else None


    def _backup_info_is_valid(self, backup_info, filename):

        # name is needed for the user to be able to identify the playlist
        if ('name' not in backup_info.keys()
            or not isinstance(backup_info['name'], str)
            or backup_info['name'] == ''):
            self.logger.error('Backup file \'%s\' is invalid', filename)
            self.logger.error('The \'name\' attribute/property is either missing or not a valid playlist name')
            return False

        # cannot restore a playlist to a state of its constituent items are not known
        # it is okay for a playlist to have no items but this needs to be explicitly known
        elif ('items' not in backup_info.keys()
              or not isinstance(backup_info['items'], list)):
            self.logger.error('Backup file \'%s\' is invalid', filename)
            self.logger.error('The \'items\' attribute/property is either missing or not a valid list')
            return False

        # cannot restore constituent items if their URIs are not known
        # item names are needed for the user to identify them and choose which backup to restore from
        item_num = 1
        for item in backup_info['items']:
            if not isinstance(item, dict):
                self.logger.error('Backup file \'%s\' is invalid', filename)
                self.logger.error('Item number %d is not a valid object/dict/map', item_num)
                return False
            elif ('uri' not in item.keys() or not isinstance(item['uri'], str)
                  or re.search('^spotify:track:[A-Za-z0-9]{22}$', item['uri']) is None):
                self.logger.error('Backup file \'%s\' is invalid', filename)
                self.logger.error('Item number %d does not have a valid track URI', item_num)
                return False
            elif 'name' not in item.keys() or not isinstance(item['name'], str) or item['name'] == '':
                self.logger.error('Backup file \'%s\' is invalid', filename)
                self.logger.error('Item number %d (URI: %s) does not have a valid name', item_num, item['uri'])
                return False

            item_num += 1
        return True

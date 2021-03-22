from src.spotify_helper import SpotifyHelper

class PlaylistCleaner:

    def __init__(self, logger, api, playlist_creator_id, config):
        self.logger = logger
        self.api = api
        self.playlist_creator_id = playlist_creator_id
        self.config = config
        self.spotify_helper = SpotifyHelper(self.logger)

    def run(self):
        self.logger.info('Initiating playlist scanning/cleaning procedire')
        playlists_to_scan = self.config['PROTECTED_PLAYLISTS']
        if self.config['PROTECT_ALL']:
            playlists_to_scan = self.spotify_helper.get_all_collab_playlists(api=self.api)

        for playlist in playlists_to_scan:
            playlist_id = self.spotify_helper.get_playlist_id(playlist)
            unauth_additions = self.find_unauthorized_additions(playlist_id, self.playlist_creator_id)
            self.remove_playlist_items(playlist_id, unauth_additions)

        self.logger.info('Completed playlist scanning/cleaning procedure')
        self.logger.info('Another playlist scannning/cleaning run should start in roughly %d minutes'
                         % self.config['FREQUENCY'])


    def find_unauthorized_additions(self, playlist_id):
        pl_uri = 'spotify:playlist:' + playlist_id
        all_items = self.spotify_helper.get_all_items_in_playlist(
            playlist_id, fields='items(added_at,added_by.id,track(name,uri)),total', api=self.api)
        unauth_additions = []

        for item in all_items:
            if not self.playlist_addition_is_authorized(item['added_by']['id'], playlist_id):
                unauth_additions.append({
                    'name': item['track']['name'],
                    'uri': item['track']['uri'],
                    'added_at': item['added_at'],
                    'added_by': item['added_by']['id']
                })

        pl_details = self.api.playlist(playlist_id, fields='name')
        self.logger.info('Identified %d unauthorized track additions to playlist `%s` (ID: %s)'
                         % (len(unauth_additions), pl_details['name'], playlist_id))

        return unauth_additions


    def remove_playlist_items(self, playlist_id, items):
        pl_details = self.api.playlist(playlist_id, fields='name')
        item_ids = [ self.spotify_helper.get_track_id(item['uri']) for item in items ]
        item_limit = 100
        lower_bound = 0
        upper_bound = 100
        more_to_process = True

        self._log_playlist_item_removal(pl_details['name'], items)
        while more_to_process:
            more_to_process = upper_bound < len(item_ids)
            self.api.playlist_remove_all_occurrences_of_items(playlist_id, item_ids[lower_bound:upper_bound])
            lower_bound = upper_bound
            upper_bound = (lower_bound + item_limit
                        if lower_bound + item_limit < len(item_ids)
                        else len(item_ids))


    def playlist_addition_is_authorized(self, adder_id, playlist_id):
        if adder_id == self.playlist_creator_id:
            return True
       
        local_auth = self._local_authorization(adder_id, playlist_id)
        return (local_auth == 'authorized'
                or (local_auth == 'neutral'
                    and self._global_authorization(adder_id) == 'authorized'))


    def _global_authorization(self, adder_id):
        # Return values:
        # 'neutral' - neither explicitly authorized nor explicitly unauthorized
        # 'authorized' - explicitly authorized
        # 'unauthorized' - explicitly authorized

        if 'DEFAULT_MODE' in self.config.keys():
            if self.config['DEFAULT_MODE'] == 'blacklist':
                return 'unauthorized' if adder_id in self.config['GLOBAL_BLACKLIST'] else 'authorized'
            elif self.config['DEFAULT_MODE'] == 'whitelist':
                return 'authorized' if adder_id in self.config['GLOBAL_WHITELIST'] else 'unauthorized'
        return 'neutral'


    def _local_authorization(self, adder_id, playlist_id):
        # Return values:
        # 'neutral' - neither explicitly authorized nor explicitly unauthorized
        # 'authorized' - explicitly authorized
        # 'unauthorized' - explicitly authorized
        
        playlist_config = self._get_playlist_config(playlist_id)

        if playlist_config is not None:
            if 'blacklist' in playlist_config.keys():
                return 'unauthorized' if adder_id in playlist_config['blacklist'] else 'authorized'
            elif 'whitelist' in playlist_config.keys():
                return 'authorized' if adder_id in playlist_config['whitelist'] else 'unauthorized'
        return 'neutral'


    def _log_playlist_item_removal(self, playlist_name, items):
        for item in items:
            self.logger.info("REMOVING: `%s` added by user `%s` at %s (URI: %s) from playlist `%s``"
                             % (item['name'], item['added_by'], item['added_at'], item['uri'], playlist_name))

    def _get_playlist_config(self, playlist_id):
        pl_uri = 'spotify:playlist:' + playlist_id
        if 'PROTECTED_PLAYLISTS' not in self.config.keys():
            return None

        for playlist in self.config['PROTECTED_PLAYLISTS']:
            if pl_uri == playlist['uri']:
                return playlist
        return None
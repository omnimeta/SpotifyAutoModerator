import logging
import re
import os
from src.spotify_helper import SpotifyHelper

class ConfigValidator:

    def __init__(self, playlist={}, log={}, account={}):
        self.playlist = playlist
        self.log = log
        self.account = account

        self.logger = logging.getLogger('ConfigValidator')
        handler = logging.StreamHandler()
        handler.setLevel('CRITICAL' if 'TEST' in os.environ and os.environ['TEST'] == 'True'
                         else 'ERROR')
        self.logger.addHandler(handler)


    def is_valid(self):
        return self.validate_playlist_config() and self.validate_log_config() and self.validate_account_config()


    def validate_account_config(self):
        required = [
            'CLIENT_ID',
            'CLIENT_SECRET',
            'REDIRECT_URI',
            'USERNAME'
        ]
        for field in required:
            if (field not in self.account.keys()
                or self.account[field] is None
                or self.account[field] == ''):
                self.logger.error('`ACCOUNT_CONFIG.%s` is not set in `data/config.yaml`!', field)
                return False
        return True


    def validate_log_config(self):
        required = [
            'FILE',
            'FORMAT',
            'FILE_LEVEL',
            'CONSOLE_LEVEL'
        ]
        for field in required:
            if (field not in self.log.keys()
                or self.log[field] is None
                or self.log[field] == ''):
                self.logger.error('`LOG_CONFIG.%s` is not set in `data/config.yaml`!', field)
                return False

        if self.log['FILE_LEVEL'] not in [ 'debug', 'info', 'warning', 'error', 'critical' ]:
            self.logger.error('`LOG_CONFIG.FILE_LEVEL` is invalid - it must be set to one of the following:')
            self.logger.error('Valid log levels: {\'debug\', \'info\', \'warning\', \'error\', \'critical\' }')
            return False
        elif self.log['CONSOLE_LEVEL'] not in [ 'debug', 'info', 'warning', 'error', 'critical' ]:
            self.logger.error('`LOG_CONFIG.CONSOLE_LEVEL` is invalid - it must be set to one of the following:')
            self.logger.error('Valid log levels: {\'debug\', \'info\', \'warning\', \'error\', \'critical\' }')
            return False

        return True

    def validate_playlist_config(self):
        required = [
            'DELAY_BETWEEN_SCANS',
            'PROTECT_ALL',
            'GLOBAL_MODE',
            'PROTECTED_PLAYLISTS',
            'BACKUP_PATH',
            'MAX_BACKUPS_PER_PLAYLIST'
        ]
        for field in required:
            if (field not in self.playlist.keys()
                or self.playlist[field] is None
                or self.playlist[field] == ''):
                self.logger.error('`PLAYLIST_CONFIG.%s` is not set in `data/config.yaml`!' % field)
                self.logger.error('Please appropriately update this option in `data/config.yaml`')
                return False

        if not isinstance(self.playlist['DELAY_BETWEEN_SCANS'], int) or self.playlist['DELAY_BETWEEN_SCANS'] < 1:
            self.logger.error('`PLAYLIST_CONFIG.DELAY_BETWEEN_SCANS` is invalid - it must be set to a positive integer')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if not isinstance(self.playlist['PROTECT_ALL'], bool):
            self.logger.error('`PLAYLIST_CONFIG.PROTECT_ALL` is invalid - it must be set to a Boolean value (either True or False)')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if not (self.playlist['GLOBAL_MODE'] == 'blacklist' or self.playlist['GLOBAL_MODE'] == 'whitelist'):
            self.logger.error('`PLAYLIST_CONFIG.GLOBAL_MODE` is invalid - it can be either \'blacklist\' or \'whitelist\'')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if ('GLOBAL_WHITELIST' in self.playlist.keys()
            and not isinstance(self.playlist['GLOBAL_WHITELIST'], list)):
            self.logger.error('`PLAYLIST_CONFIG.GLOBAL_WHITELIST` is invalid - it must be a list')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if ('GLOBAL_BLACKLIST' in self.playlist.keys()
            and not isinstance(self.playlist['GLOBAL_BLACKLIST'], list)):
            self.logger.error('`PLAYLIST_CONFIG.GLOBAL_BLACKLIST` is invalid - it must be a list')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if (self.playlist['GLOBAL_MODE'] == 'blacklist'
            and 'GLOBAL_BLACKLIST' not in self.playlist.keys()):
            self.logger.error('`PLAYLIST_CONFIG.GLOBAL_MODE` is `blacklist` but `PLAYLIST_CONFIG.GLOBAL_BLACKLIST` is not defined!')
            return False
        elif (self.playlist['GLOBAL_MODE'] == 'whitelist'
              and 'GLOBAL_WHITELIST' not in self.playlist.keys()):
            self.logger.error('`PLAYLIST_CONFIG.GLOBAL_MODE` is `whitelist` but `PLAYLIST_CONFIG.GLOBAL_WHITELIST` is not defined!')
            return False

        if not isinstance(self.playlist['PROTECTED_PLAYLISTS'], list):
            self.logger.error('`PLAYLIST_CONFIG.PROTECT_ALL` is invalid - it must be to a list (which may or may not be empty)')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if not isinstance(self.playlist['BACKUP_PATH'], str):
            self.logger.error('`PLAYLIST_CONFIG.BACKUP_PATH` is invalid - it must be set to a valid file system path')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        if (not isinstance(self.playlist['MAX_BACKUPS_PER_PLAYLIST'], int)
            or self.playlist['MAX_BACKUPS_PER_PLAYLIST'] < 1):
            self.logger.error('`PLAYLIST_CONFIG.MAX_BACKUPS_PER_PLAYLIST` is invalid - it must be a positive integer')
            self.logger.error('Please appropriately update this option in `data/config.yaml`')
            return False

        return self.validate_protected_playlists()


    def validate_protected_playlists(self):
        playlist_number = 1
        for playlist in self.playlist['PROTECTED_PLAYLISTS']:
            if len(playlist.keys()) != 1:
                self.logger.error('Playlist %d is not of a valid format', playlist_number)
                self.logger.error('Please update `PLAYLIST_CONFIG.PROTECTED_PLAYLISTS` in `data/config.yaml`')
                return False

            # Each playlist must have a valid Spotify URI to be monitored
            for key, val in playlist.items():
                if (not isinstance(val, dict)
                    or 'uri' not in val.keys()
                    or not isinstance(val['uri'], str)):
                    self.logger.error('Playlist %d does not have a valid Spotify URI', playlist_number)
                    self.logger.error('Please update `PLAYLIST_CONFIG.PROTECTED_PLAYLISTS` in `data/config.yaml`')
                    return False
                elif re.search('^spotify:playlist:[A-Za-z0-9]{22}$', val['uri']) is None:
                    self.logger.error('%s is not a valid Spotify URI for playlist %d',
                                      val['uri'], playlist_number)
                    return False

            playlist_number += 1

        return True


    def all_protected_playlists_exist(self, api_client):
        if ('PROTECTED_PLAYLISTS' not in self.playlist.keys()
            or not isinstance(self.playlist['PROTECTED_PLAYLISTS'], list)):
            self.logger.error('`PLAYLIST_CONFIG.PROTECTED_PLAYLISTS is invalid - it must be a list`')
            return False

        helper = SpotifyHelper(self.logger, api=api_client)
        collab_playlists = helper.get_all_collab_playlists()
        collab_pl_uris = [ pl['uri'] for pl in collab_playlists ]

        for playlist in self.playlist['PROTECTED_PLAYLISTS']:
            if len(playlist.keys()) != 1:
                return False

            for key, val in playlist.items():
                if val['uri'] not in collab_pl_uris:
                    return False
        return True

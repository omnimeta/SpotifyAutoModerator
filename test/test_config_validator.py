import unittest
import random
import string
import os
import spotipy
from unittest.mock import Mock, patch
from src.config_validator import ConfigValidator

class TestConfigValidator(unittest.TestCase):

    def setUp(self):
        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        os.environ['TEST'] = 'True'


    # ----- Tests for ConfigValidator.is_valid ----- #

    def test_is_valid_returns_true_if_all_config_types_are_valid(self):
        validator = ConfigValidator(playlist={}, log={}, account={})
        validator.validate_playlist_config = Mock(return_value=True)
        validator.validate_log_config = Mock(return_value=True)
        validator.validate_account_config = Mock(return_value=True)
        self.assertTrue(validator.is_valid())


    def test_is_valid_returns_false_if_log_config_is_invalid(self):
        validator = ConfigValidator(playlist={}, log={}, account={})
        validator.validate_playlist_config = Mock(return_value=True)
        validator.validate_log_config = Mock(return_value=False)
        validator.validate_account_config = Mock(return_value=True)
        self.assertFalse(validator.is_valid())


    def test_is_valid_returns_false_if_playlist_config_is_invalid(self):
        validator = ConfigValidator(playlist={}, log={}, account={})
        validator.validate_playlist_config = Mock(return_value=False)
        validator.validate_log_config = Mock(return_value=True)
        validator.validate_account_config = Mock(return_value=True)
        self.assertFalse(validator.is_valid())


    def test_is_valid_returns_false_if_account_config_is_invalid(self):
        validator = ConfigValidator(playlist={}, log={}, account={})
        validator.validate_playlist_config = Mock(return_value=True)
        validator.validate_log_config = Mock(return_value=True)
        validator.validate_account_config = Mock(return_value=False)
        self.assertFalse(validator.is_valid())


    # ----- Tests for ConfigValidator.validate_account_config ----- #

    def test_validate_account_config_returns_true_if_all_account_info_is_set(self):
        validator = ConfigValidator(account={
            'CLIENT_ID': 'id',
            'CLIENT_SECRET': 'secret',
            'REDIRECT_URI': 'uri',
            'USERNAME': 'username'
        })
        self.assertTrue(validator.validate_account_config())


    def test_validate_account_config_returns_false_if_any_account_info_is_missing(self):
        validator = ConfigValidator(account={
            'CLIENT_ID': 'id',
            'CLIENT_SECRET': 'secret',
            'REDIRECT_URI': 'uri'
        })
        self.assertFalse(validator.validate_account_config())

        validator = ConfigValidator(account={
            'CLIENT_ID': 'id',
            'CLIENT_SECRET': 'secret',
            'USERNAME': 'username'
        })
        self.assertFalse(validator.validate_account_config())

        validator = ConfigValidator(account={
            'CLIENT_ID': 'id',
            'USERNAME': 'username',
            'REDIRECT_URI': 'uri'
        })
        self.assertFalse(validator.validate_account_config())

        validator = ConfigValidator(account={
            'CLIENT_SECRET': 'secret',
            'USERNAME': 'username',
            'REDIRECT_URI': 'uri'
        })
        self.assertFalse(validator.validate_account_config())


    # ----- Tests for ConfigValidator.validate_log_config ----- #

    def test_validate_log_config_returns_false_if_any_required_field_is_missing(self):
        validator = ConfigValidator(log={
            'FILE': 'file',
            'FORMAT': 'format',
            'FILE_LEVEL': 'error'
        })
        self.assertFalse(validator.validate_log_config())

        validator = ConfigValidator(log={
            'FILE': 'file',
            'FORMAT': 'format',
            'CONSOLE_LEVEL': 'error'
        })
        self.assertFalse(validator.validate_log_config())

        validator = ConfigValidator(log={
            'FORMAT': 'format',
            'FILE_LEVEL': 'error',
            'CONSOLE_LEVEL': 'error'
        })
        self.assertFalse(validator.validate_log_config())


    def test_validate_log_config_returns_false_if_file_level_is_not_a_valid_log_level(self):
        validator = ConfigValidator(log={
            'FILE': 'file',
            'FORMAT': 'format',
            'FILE_LEVEL': 'not_a_real_log_level',
            'CONSOLE_LEVEL': 'error'
        })
        self.assertFalse(validator.validate_log_config())


    def test_validate_log_config_returns_false_if_console_level_is_not_a_valid_log_level(self):
        validator = ConfigValidator(log={
            'FILE': 'file',
            'FORMAT': 'format',
            'FILE_LEVEL': 'error',
            'CONSOLE_LEVEL': 'not_a_real_log_level'
        })
        self.assertFalse(validator.validate_log_config())


    def test_validate_log_config_returns_true_all_fields_provided_and_log_levels_are_valid(self):
        validator = ConfigValidator(log={
            'FILE': 'file',
            'FORMAT': 'format',
            'FILE_LEVEL': 'error',
            'CONSOLE_LEVEL': 'error'
        })
        self.assertTrue(validator.validate_log_config())


    # ----- Tests for ConfigValidator.validate_playlist_config ----- #

    def test_validate_playlist_config_returns_false_if_any_required_field_is_missing(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'PROTECTED_PLAYLISTS': [],
            'BACKUP_PATH': 'data/test/backup/some_path'
        })
        self.assertFalse(validator.validate_playlist_config())

        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'PROTECTED_PLAYLISTS': [],
            'MAX_BACKUPS_PER_PLAYLIST': 2
        })
        self.assertFalse(validator.validate_playlist_config())

        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2
        })
        self.assertFalse(validator.validate_playlist_config())

        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'PROTECT_ALL': False,
            'PROTECTED_PLAYLISTS': [],
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2
        })
        self.assertFalse(validator.validate_playlist_config())

        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_MODE': 'blacklist',
            'PROTECTED_PLAYLISTS': [],
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2
        })
        self.assertFalse(validator.validate_playlist_config())

        validator = ConfigValidator(playlist={
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'PROTECTED_PLAYLISTS': [],
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_delay_between_scans_is_not_an_integer(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 'not_an_int',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_delay_between_scans_is_less_than_1_minute(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 0,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_protect_all_is_not_a_boolean(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': 'not_a_bool',
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_GLOBAL_mode_is_not_blacklist_or_whitelist(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'not_a_valid_mode',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())

    def test_validate_playlist_config_returns_false_if_protected_playlists_are_not_a_list(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': 'not a list'
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_protected_playlists_are_not_valid(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        validator.validate_protected_playlists = Mock(return_value=False)
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_global_whitelist_is_set_but_is_not_a_list(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': 'not_a_list',
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_global_blacklist_is_set_but_is_not_a_list(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': 'not_a_list',
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_backup_path_is_not_a_string(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 900,
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_max_backups_per_playlist_is_not_a_positive_integer(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 'not_an_int',
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())

        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 0,
            'PROTECTED_PLAYLISTS': []
        })
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_global_mode_is_blacklist_and_global_blacklist_not_set(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        validator.validate_protected_playlists = Mock(return_value=True)
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_false_if_global_mode_is_whitelist_and_global_whitelist_not_set(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'whitelist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        validator.validate_protected_playlists = Mock(return_value=True)
        self.assertFalse(validator.validate_playlist_config())


    def test_validate_playlist_config_returns_true_if_all_fields_valid_and_protected_playlists_are_valid(self):
        validator = ConfigValidator(playlist={
            'DELAY_BETWEEN_SCANS': 90,
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECT_ALL': False,
            'GLOBAL_MODE': 'blacklist',
            'BACKUP_PATH': 'data/test/backup/some_path',
            'MAX_BACKUPS_PER_PLAYLIST': 2,
            'PROTECTED_PLAYLISTS': []
        })
        validator.validate_protected_playlists = Mock(return_value=True)
        self.assertTrue(validator.validate_playlist_config())


    # ----- Tests for ConfigValidator.validate_protected_playlists ----- #

    def test_validate_protected_playlist_returns_false_if_any_playlists_has_no_uri(self):
        validator = ConfigValidator(playlist={
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECTED_PLAYLISTS': [
                {
                    'pl1label': {
                        'uri': self.generate_playlist_uri(),
                        'blacklist': []
                    }
                },
                {
                    'pl2label': {
                        'blacklist': []
                    }
                }
            ]
        })
        self.assertFalse(validator.validate_protected_playlists())

    def test_validate_protected_playlist_returns_false_if_any_playlist_has_an_invalid_uri(self):
        validator = ConfigValidator(playlist={
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECTED_PLAYLISTS': [
                {
                    'pl1label': {
                        'uri': self.generate_playlist_uri(),
                        'blacklist': []
                    }
                },
                {
                    'pl2label': {
                        'uri': 'not_a_valid_uri',
                        'blacklist': []
                    }
                }
            ]
        })
        self.assertFalse(validator.validate_protected_playlists())


    def test_validate_protected_playlist_returns_true_if_all_playlists_have_a_valid_uri(self):
        # empty whitelist and no whitelist are considered the same thing
        validator = ConfigValidator(playlist={
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECTED_PLAYLISTS': [
                {
                    'playlist1label': { 'uri': self.generate_playlist_uri() }
                },
                {
                    'playlist2label': { 'uri': self.generate_playlist_uri() }
                }
            ]
        })
        self.assertTrue(validator.validate_protected_playlists())


    def test_validate_protected_playlist_returns_false_if_a_playlist_has_more_than_one_label(self):
        # empty whitelist and no whitelist are considered the same thing
        validator = ConfigValidator(playlist={
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': [],
            'PROTECTED_PLAYLISTS': [
                {
                    'playlist1label': { 'uri': self.generate_playlist_uri() },
                    'playlist1label2': { 'uri': self.generate_playlist_uri() }
                },
                {
                    'playlist2label': { 'uri': self.generate_playlist_uri() }
                }
            ]
        })
        self.assertFalse(validator.validate_protected_playlists())


    # ----- Tests for ConfigValidator.all_protected_playlists_exist() ----- #

    def test_all_protected_playlists_exist_returns_false_if_playlist_config_does_not_have_a_list_of_protected_playlists(self):
        validator = ConfigValidator({}, {}, {})
        self.assertFalse(validator.all_protected_playlists_exist(spotipy.client.Spotify()))


    @patch('src.config_validator.SpotifyHelper')
    def test_all_protected_playlists_exist_returns_true_if_all_playlist_uris_are_matched_in_the_users_collab_playlists(self, helper_stub):
        playlists = [
            {
                'playlist1label': { 'uri': self.generate_playlist_uri() }
            },
            {
                'playlist2label': { 'uri': self.generate_playlist_uri() }
            }
        ]
        helper_obj = Mock()
        helper_obj.get_all_collab_playlists.return_value = [
            playlists[0]['playlist1label'],
            playlists[1]['playlist2label']
        ]
        helper_stub.return_value = helper_obj
        validator = ConfigValidator({ 'PROTECTED_PLAYLISTS': playlists }, {}, {})
        self.assertTrue(validator.all_protected_playlists_exist(spotipy.client.Spotify()))


    @patch('src.config_validator.SpotifyHelper')
    def test_all_protected_playlists_exist_returns_false_if_all_any_protected_playlist_uri_is_not_matched_in_the_users_collab_playlists(self, helper_stub):
        protected_playlists = [
            {
                'pllabel1': { 'uri': self.generate_playlist_uri() }
            },
            {
                'pllabel2': { 'uri': self.generate_playlist_uri() }
            }
        ]
        helper_obj = Mock()
        helper_obj.get_all_collab_playlists.return_value = [ protected_playlists[0]['pllabel1'] ]
        helper_stub.return_value = helper_obj
        validator = ConfigValidator({ 'PROTECTED_PLAYLISTS': protected_playlists }, {}, {})
        self.assertFalse(validator.all_protected_playlists_exist(spotipy.client.Spotify()))


    @patch('src.config_validator.SpotifyHelper')
    def test_all_protected_playlists_exist_returns_false_if_a_playlist_has_more_than_one_label(self, helper_stub):
        protected_playlists = [
            {
                'pllabel1': { 'uri': self.generate_playlist_uri() },
                'anotherlabelforsame': { 'uri': self.generate_playlist_uri() }
            },
            {
                'pllabel2': { 'uri': self.generate_playlist_uri() }
            }
        ]
        helper_obj = Mock()
        helper_obj.get_all_collab_playlists.return_value = [ protected_playlists[0]['pllabel1'] ]
        helper_stub.return_value = helper_obj
        validator = ConfigValidator({ 'PROTECTED_PLAYLISTS': protected_playlists }, {}, {})
        self.assertFalse(validator.all_protected_playlists_exist(spotipy.client.Spotify()))


if __name__ == '__main__':
    unittest.main()

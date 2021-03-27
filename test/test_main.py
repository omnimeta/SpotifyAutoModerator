import unittest
from unittest.mock import Mock, patch
import logging
import sys
import random
import string
import yaml
import spotipy
import os
from inputimeout import inputimeout, TimeoutOccurred
import src.main as main

class TestMain(unittest.TestCase):

    def setUp(self):
        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())


    # ----- Tests for main ----- #

    @patch('src.main.input', return_value='') # exit w/o user input
    @patch('src.main.print_help_information', side_effect=main.print_help_information)
    def test_main_prints_help_info_and_exits_with_code_0_if_help_option_in_args(self, print_help_mock, exit_stub):
        with patch.object(sys, 'argv', [ '--help' ]) as stubbed_args:
            with self.assertRaises(SystemExit) as sys_exit:
                main.main()
        print_help_mock.assert_called_once()
        self.assertEqual(sys_exit.exception.code, 0)

        with patch.object(sys, 'argv', ['-h']) as stubbed_args:
            with self.assertRaises(SystemExit) as sys_exit:
                main.main()
        self.assertEqual(print_help_mock.call_count, 2)
        self.assertEqual(sys_exit.exception.code, 0)


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.restore_default_config_file')
    def test_main_returns_return_value_of_restore_config_if_rdc_option_in_args(self, restore_stub, exit_stub):
        with patch.object(sys, 'argv', ['--rdc']) as stubbed_args:
            restore_stub.return_value = 0
            with self.assertRaises(SystemExit) as sys_exit:
                main.main()
            self.assertEqual(sys_exit.exception.code, 0)

            restore_stub.return_value = 1
            with self.assertRaises(SystemExit) as sys_exit:
                main.main()
            self.assertEqual(sys_exit.exception.code, 1)


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.load_configurations', side_effect=Exception('something went wrong'))
    def test_main_exits_with_code_1_if_exception_raised_while_loading_configurations(self, load_config_mock,
                                                                                     exit_stub):
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        load_config_mock.assert_called_once()
        self.assertEqual(sys_exit.exception.code, 1)


    @patch('src.main.input', return_value='') # exits on error without user input
    @patch('src.main.load_configurations', return_value=({}, {}, {}))
    @patch('src.main.ConfigValidator')
    def test_main_validates_configurations_before_setting_up_a_logger(self, config_validator_mock,
                                                                      load_config_stub, exit_stub):
        # The stubbed return value of (False) is_valid() allows main() to quit early
        mock_validator = Mock()
        mock_validator.is_valid = Mock(return_value=False)
        config_validator_mock.return_value = mock_validator
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        mock_validator.is_valid.assert_called_once()


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.ConfigValidator')
    def test_main_exits_with_code_1_if_config_validation_fails(self, config_validator_mock, exit_stub):
        mock_validator = Mock()
        mock_validator.is_valid = Mock(return_value=False)
        config_validator_mock.return_value = mock_validator
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.load_configurations', return_value=({}, {}, {}))
    @patch('src.main.setup_logger', side_effect=Exception('something went wrong'))
    @patch('src.main.ConfigValidator')
    def test_main_exits_with_code_1_if_an_exception_is_raised_when_setting_up_a_loger(self, config_validator_mock,
                                                                                      setup_logger_mock, load_config_stub,
                                                                                      exit_stub):
        mock_validator = Mock()
        # stubbing is_valid to return True allows the function to continue running beyond validation
        mock_validator.is_valid = Mock(return_value=True)
        config_validator_mock.return_value = mock_validator
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations', return_value=({}, {}, {
        'CLIENT_ID': 'spotifyclientid',
        'CLIENT_SECRET': 'spotifyclientsecret',
        'REDIRECT_URI': 'http://localhost:8080'
    }))
    def test_main_exits_with_code_1_if_api_client_setup_fails(self, get_config_stub, config_validator_mock,
                                                             setup_logger_mock, helper_mock, exit_stub):
        mock_validator = Mock()
        # stubbing is_valid to return True allows the function to continue running beyond validation
        mock_validator.is_valid = Mock(return_value=True)
        config_validator_mock.return_value = mock_validator

        configure_api_stub = Mock()
        configure_api_stub.configure_api.side_effect = Exception('401 unauthorized')
        helper_mock.return_value = configure_api_stub
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)

        configure_api_stub.configure_api.side_effect = [ None ]
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations', return_value=({}, {}, {
        'CLIENT_ID': 'spotifyclientid',
        'CLIENT_SECRET': 'spotifyclientsecret',
        'REDIRECT_URI': 'http://localhost:8080'
    }))
    def test_main_exits_with_code_1_if_redirect_uri_is_in_use(self, get_config_stub, config_validator_mock,
                                                              setup_logger_mock, helper_mock, exit_stub):
        mock_validator = Mock()
        # stubbing is_valid to return True allows the function to continue running beyond validation
        mock_validator.is_valid = Mock(return_value=True)
        config_validator_mock.return_value = mock_validator

        configure_api_stub = Mock()
        # an OSError is raised when the redirect URI is already in use
        configure_api_stub.configure_api.side_effect = OSError('Address already in use')
        helper_mock.return_value = configure_api_stub
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)


    @patch('src.main.input', return_value='') # exit w/o user input
    @patch('src.main.PlaylistCleaner')
    @patch('src.main.IntegrityManager')
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations')
    def test_main_runs_one_playlist_moderation_loop_if_loop_mode_is_disabled(self, get_config_stub, config_validator_mock,
                                                                             setup_logger_mock, helper_mock, integrity_mgr_mock,
                                                                             cleaner_mock, exit_stub):
        # loop mode is only enabled if '--loop' in args so it is disabled by default

        only_playlist = { 'uri': self.generate_playlist_uri() }
        get_config_stub.return_value = ({
            'PROTECT_ALL': False,
            'PROTECTED_PLAYLISTS': [ { 'playlist_label': only_playlist } ]
        }, {}, {
            'CLIENT_ID': 'spotifyclientid',
            'CLIENT_SECRET': 'spotifyclientsecret',
            'REDIRECT_URI': 'http://localhost:8080',
            'USERNAME': 'spotifyusername'
        })

        mock_validator = Mock()
        mock_validator.is_valid.return_value = True
        mock_validator.all_protected_playlists_exist.return_value = True
        config_validator_mock.return_value = mock_validator

        configure_api_stub = Mock()
        configure_api_stub.configure_api.return_value = spotipy.client.Spotify()
        helper_mock.return_value = configure_api_stub

        integrity_mgr_obj = Mock()
        playlist_cleaner_obj = Mock()
        integrity_mgr_mock.return_value = integrity_mgr_obj
        cleaner_mock.return_value = playlist_cleaner_obj

        with self.assertRaises(SystemExit) as sys_exit:
            # run within SysExit context because main explicitly exits with code 0 after completion
            main.main()
        self.assertEqual(len(integrity_mgr_obj.run.call_args[0]), 1)
        integrity_mgr_obj.run.assert_called_once_with(only_playlist)
        self.assertEqual(len(playlist_cleaner_obj.run.call_args[0]), 1)
        playlist_cleaner_obj.run.assert_called_once_with(only_playlist)


    @patch('src.main.input', return_value='') # exit w/o user input
    @patch('src.main.PlaylistCleaner')
    @patch('src.main.IntegrityManager')
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations')
    def test_main_runs_protects_all_collab_playlist_if_protect_all_is_enabled(self, get_config_stub, config_validator_mock,
                                                                              setup_logger_mock, helper_mock, integrity_mgr_mock,
                                                                              cleaner_mock, exit_stub):

        get_config_stub.return_value = ({
            'PROTECT_ALL': True,
            'PROTECTED_PLAYLISTS': []
        }, {}, {
            'CLIENT_ID': 'spotifyclientid',
            'CLIENT_SECRET': 'spotifyclientsecret',
            'REDIRECT_URI': 'http://localhost:8080',
            'USERNAME': 'spotifyusername'
        })

        mock_validator = Mock()
        mock_validator.is_valid.return_value = True
        mock_validator.all_protected_playlists_exist.return_value = True
        config_validator_mock.return_value = mock_validator

        helper_obj = Mock()
        helper_obj.configure_api.return_value = spotipy.client.Spotify()
        only_collab_playlists = [ { 'uri': self.generate_playlist_uri() } ]
        helper_obj.get_all_collab_playlists.return_value = only_collab_playlists
        helper_mock.return_value = helper_obj

        integrity_mgr_obj = Mock()
        playlist_cleaner_obj = Mock()
        integrity_mgr_mock.return_value = integrity_mgr_obj
        cleaner_mock.return_value = playlist_cleaner_obj

        with self.assertRaises(SystemExit) as sys_exit:
            # run within SysExit context because main explicitly exits with code 0 after completion
            main.main()
        self.assertEqual(len(integrity_mgr_obj.run.call_args[0]), 1)
        integrity_mgr_obj.run.assert_called_once_with(only_collab_playlists[0])
        self.assertEqual(len(playlist_cleaner_obj.run.call_args[0]), 1)
        playlist_cleaner_obj.run.assert_called_once_with(only_collab_playlists[0])


    @patch('src.main.input', return_value='') # exit w/o user input
    @patch.object(sys, 'argv', [ '--loop' ])
    @patch('src.main.user_wants_to_exit', side_effect=[False, True])
    @patch('src.main.PlaylistCleaner')
    @patch('src.main.IntegrityManager')
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations')
    def test_main_runs_playlist_moderation_until_user_wants_to_exit_if_loop_mode_enabled(self, get_config_stub, config_validator_mock,
                                                                                         setup_logger_mock, helper_mock, integrity_mgr_mock,
                                                                                         cleaner_mock, user_exit_mock, exit_stub):

        only_playlist = { 'uri': self.generate_playlist_uri() }
        get_config_stub.return_value = ({
            'PROTECT_ALL': False,
            'PROTECTED_PLAYLISTS': [ { 'playlistlabel': only_playlist } ],
            'DELAY_BETWEEN_SCANS': 1
        }, {}, {
            'CLIENT_ID': 'spotifyclientid',
            'CLIENT_SECRET': 'spotifyclientsecret',
            'REDIRECT_URI': 'http://localhost:8080',
            'USERNAME': 'spotifyusername'
        })

        mock_validator = Mock()
        mock_validator.is_valid.return_value = True
        mock_validator.all_protected_playlists_exist.return_value = True
        config_validator_mock.return_value = mock_validator

        helper_obj = Mock()
        helper_obj.configure_api.return_value = spotipy.client.Spotify()
        helper_mock.return_value = helper_obj

        integrity_mgr_obj = Mock()
        playlist_cleaner_obj = Mock()
        integrity_mgr_mock.return_value = integrity_mgr_obj
        cleaner_mock.return_value = playlist_cleaner_obj

        with self.assertRaises(SystemExit) as sys_exit:
            # run within SysExit context because main explicitly exits with code 0 after completion
            main.main()

        self.assertEqual(integrity_mgr_obj.run.call_count, 2)
        self.assertEqual(len(integrity_mgr_obj.run.call_args_list[0][0]), 1)
        self.assertEqual(integrity_mgr_obj.run.call_args_list[0][0][0], only_playlist)

        self.assertEqual(len(integrity_mgr_obj.run.call_args_list[1][0]), 1)
        self.assertEqual(integrity_mgr_obj.run.call_args_list[1][0][0], only_playlist)

        self.assertEqual(playlist_cleaner_obj.run.call_count, 2)
        self.assertEqual(playlist_cleaner_obj.run.call_args_list[0][0][0], only_playlist)
        self.assertEqual(len(playlist_cleaner_obj.run.call_args_list[0][0]), 1)
        self.assertEqual(playlist_cleaner_obj.run.call_args_list[1][0][0], only_playlist)
        self.assertEqual(len(playlist_cleaner_obj.run.call_args_list[1][0]), 1)


    @patch('src.main.input', return_value='') # exit w/o user input
    @patch('src.main.PlaylistCleaner')
    @patch('src.main.IntegrityManager')
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations')
    def test_main_exits_with_code_0_after_running_successfully(self, get_config_stub, config_validator_mock,
                                                               setup_logger_mock, helper_mock, integrity_mgr_mock,
                                                               cleaner_mock, exit_stub):

        only_playlist = { 'uri': self.generate_playlist_uri() }
        get_config_stub.return_value = ({
            'PROTECT_ALL': False,
            'PROTECTED_PLAYLISTS': []
        }, {}, {
            'CLIENT_ID': 'spotifyclientid',
            'CLIENT_SECRET': 'spotifyclientsecret',
            'REDIRECT_URI': 'http://localhost:8080',
            'USERNAME': 'spotifyusername'
        })

        mock_validator = Mock()
        mock_validator.is_valid.return_value = True
        mock_validator.all_protected_playlists_exist.return_value = True
        config_validator_mock.return_value = mock_validator

        configure_api_stub = Mock()
        configure_api_stub.configure_api.return_value = spotipy.client.Spotify()
        helper_mock.return_value = configure_api_stub

        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 0)


    @patch('src.main.input', return_value='') # exits on error w/o user input
    @patch('src.main.moderate_playlists')
    @patch('src.main.PlaylistCleaner')
    @patch('src.main.IntegrityManager')
    @patch('src.main.SpotifyHelper')
    @patch('src.main.setup_logger')
    @patch('src.main.ConfigValidator')
    @patch('src.main.load_configurations')
    def test_main_exits_with_code_1_if_not_all_protected_playlists_exist(self, get_config_stub, config_validator_mock,
                                                                         setup_logger_mock, helper_mock, integrity_mgr_mock,
                                                                         cleaner_mock, moderate_playlists_mock, exit_stub):

        only_playlist = { 'uri': self.generate_playlist_uri() }
        get_config_stub.return_value = ({
            'PROTECT_ALL': False,
            'PROTECTED_PLAYLISTS': []
        }, {}, {
            'CLIENT_ID': 'spotifyclientid',
            'CLIENT_SECRET': 'spotifyclientsecret',
            'REDIRECT_URI': 'http://localhost:8080',
            'USERNAME': 'spotifyusername'
        })

        mock_validator = Mock()
        mock_validator.is_valid.return_value = True
        mock_validator.all_protected_playlists_exist.return_value = False
        config_validator_mock.return_value = mock_validator

        configure_api_stub = Mock()
        configure_api_stub.configure_api.return_value = spotipy.client.Spotify()
        helper_mock.return_value = configure_api_stub

        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)
        moderate_playlists_mock.assert_not_called()


    # ----- Tests for setup_logger ----- #

    def test_setup_logger_returns_a_logger(self):
        self.assertTrue(isinstance(main.setup_logger({
            'FILE_LEVEL': 'info',
            'CONSOLE_LEVEL': 'info',
            'FILE': 'data/test/log/log_file_path'
        }), logging.Logger))


    def test_setup_logger_raises_exception_if_the_given_config_is_not_a_dict(self):
        self.assertRaises(Exception, main.setup_logger, None)


    def test_setup_logger_raises_exception_if_the_given_config_is_does_not_include_a_valid_file_log_level(self):
        self.assertRaises(Exception, main.setup_logger, {
            'CONSOLE_LEVEL': 'info',
            'FILE': 'data/test/log/log_file_path'
        })

        self.assertRaises(Exception, main.setup_logger, {
            'FILE_LEVEL': '',
            'CONSOLE_LEVEL': 'info',
            'FILE': 'data/test/log/log_file_path'
        })


    def test_setup_logger_raises_exception_if_the_given_config_is_does_not_include_a_valid_console_log_level(self):
        self.assertRaises(Exception, main.setup_logger, {
            'FILE_LEVEL': 'info',
            'FILE': 'data/test/log/log_file_path'
        })

        self.assertRaises(Exception, main.setup_logger, {
            'FILE_LEVEL': 'info',
            'CONSOLE_LEVEL': '',
            'FILE': 'data/test/log/log_file_path'
        })


    def test_setup_logger_raises_exception_if_the_given_config_is_does_not_include_a_valid_log_file_name(self):
        self.assertRaises(Exception, main.setup_logger, {
            'FILE_LEVEL': 'info',
            'CONSOLE_LEVEL': 'info',
        })

        self.assertRaises(Exception, main.setup_logger, {
            'FILE_LEVEL': 'info',
            'CONSOLE_LEVEL': 'info',
            'FILE': ''
        })


    def test_setup_logger_returns_a_logger_with_a_stream_handler_with_the_given_console_log_level(self):
        # Log level numeric values:
        # CRITICAL: 50
        # ERROR: 40
        # WARNING: 30
        # INFO: 20
        # DEBUG: 10
        # NOTSET: 0

        logger = main.setup_logger({
            'FILE_LEVEL': 'info',
            'CONSOLE_LEVEL': 'debug',
            'FILE': 'data/test/log/log_file_path'
        })
        console_handler = None
        for handler in logger.handlers:
            if handler.get_name() == 'console_handler':
                console_handler = handler
        self.assertIsNotNone(console_handler)
        self.assertEqual(console_handler.level, 10)


    def test_setup_logger_returns_a_logger_with_a_file_handler_with_the_given_file_log_level(self):
        logger = main.setup_logger({
            'FILE_LEVEL': 'critical',
            'CONSOLE_LEVEL': 'info',
            'FILE': 'data/test/log/log_file_path'
        })
        file_handler = None
        for handler in logger.handlers:
            if handler.get_name() == 'file_handler':
                file_handler = handler
        self.assertIsNotNone(file_handler)
        self.assertEqual(file_handler.level, 50)


    # ----- Tests for user_wants_to_exit ----- #

    @patch('src.main.inputimeout', side_effect=TimeoutOccurred())
    def test_user_wants_to_exit_returns_false_if_a_timeout_occurs(self, input_func_stub):
        self.assertFalse(main.user_wants_to_exit(10))


    @patch('src.main.inputimeout')
    def test_user_wants_it_exit_returns_true_if_user_input_is_some_variation_of_yes(self, input_func_stub):
        variants_of_yes = ['Y', 'y', 'YES', 'Yes', 'yes']
        for yes in variants_of_yes:
            input_func_stub.return_value = yes
            self.assertTrue(main.user_wants_to_exit(10))


    @patch('src.main.inputimeout', return_value='')
    def test_user_wants_to_exit_returns_false_if_user_input_is_empty(self, input_func_stub):
        self.assertFalse(main.user_wants_to_exit(10))


    @patch('src.main.inputimeout', return_value='notyes')
    def test_user_wants_to_exit_returns_false_if_user_input_is_nonempty_but_not_a_variant_of_yes(self, input_func_stub):
        self.assertFalse(main.user_wants_to_exit(10))


    # ----- Tests for restore_default_config_file ----- #

    @patch('src.main.get_config_filepath', return_value='data/test/fake_config.yaml')
    @patch('src.main.inputimeout', return_value='Y')
    def test_restore_default_config_file_copies_the_default_config_if_user_confirms(self, user_input_stub,
                                                                                    get_config_stub):
        default_config_file = open('data/.default_config.yaml', 'r')
        default_config_info = default_config_file.read()
        default_config_file.close()
        main.restore_default_config_file()
        config_file = open('data/test/fake_config.yaml', 'r')
        config_info = config_file.read()
        config_file.close()

        self.assertEqual(config_info, default_config_info)
        os.remove('data/test/fake_config.yaml')


    @patch('src.main.open')
    @patch('src.main.inputimeout', return_value='Y')
    def test_restore_default_config_file_returns_0_if_restored_successfully(self, user_input_stub,
                                                                                   open_func_stub):
        file_mock = Mock()
        open_func_stub.return_value = file_mock
        self.assertEqual(main.restore_default_config_file(), 0)


    @patch('src.main.open')
    @patch('src.main.inputimeout', return_value='n')
    def test_restore_default_config_file_aborts_and_returns_0_if_the_user_does_not_config(self, user_input_stub,
                                                                                                 open_func_stub):
        file_mock = Mock()
        open_func_stub.return_value = file_mock
        file_mock.write.assert_not_called()
        self.assertEqual(main.restore_default_config_file(), 0)


    @patch('src.main.open')
    @patch('src.main.inputimeout', side_effect=TimeoutOccurred())
    def test_restore_default_config_file_aborts_and_returns_1_if_the_user_input_times_out(self, user_input_stub,
                                                                                                 open_func_stub):
        file_mock = Mock()
        open_func_stub.return_value = file_mock
        file_mock.write.assert_not_called()
        self.assertEqual(main.restore_default_config_file(), 1)


    @patch('src.main.open')
    @patch('src.main.inputimeout', side_effect=TimeoutOccurred())
    def test_restore_default_config_file_returns_1_if_the_user_input_times_out(self, user_input_stub,
                                                                                      open_func_stub):
        self.assertEqual(main.restore_default_config_file(), 1)


    @patch('src.main.open', side_effect=Exception('something went wrong'))
    @patch('src.main.inputimeout', return_value='Y')
    def test_restore_default_config_file_returns_1_if_exception_raised_during_restoration(self, user_input_stub,
                                                                                                 open_func_stub):
        file_mock = Mock()
        open_func_stub.return_value = file_mock
        file_mock.write.assert_not_called()
        self.assertEqual(main.restore_default_config_file(), 1)


    # ----- Tests for load_configurations ----- #

    def test_load_configurations_loads_playlist_log_and_account_configurations_from_yaml_at_the_given_path(self):
        test_config = """
---
PLAYLIST_CONFIG:
  PROTECTED_PLAYLISTS:
    - PlaylistLabel1:
        uri: playlist1_uri
        whitelist:
          - spotifyusername1
LOG_CONFIG:
  FILE: data/test/log/log_file_path
ACCOUNT_CONFIG:
  USERNAME: spotifyusername
"""
        test_config_file = open('data/test/config/config.yaml', 'w')
        test_config_file.write(test_config)
        test_config_file.close()
        loaded_configs = main.load_configurations(path='data/test/config/config.yaml')
        self.assertEqual(loaded_configs, ({
            'PROTECTED_PLAYLISTS': [
                {
                    'PlaylistLabel1': {
                        'uri': 'playlist1_uri',
                        'whitelist': [ 'spotifyusername1' ]
                    }
                }
            ]
        }, {
            'FILE': 'data/test/log/log_file_path'
        }, {
            'USERNAME': 'spotifyusername'
        }))


    @patch('src.main.open')
    @patch('src.main.yaml.load', side_effect=yaml.YAMLError())
    def test_load_configurations_propagates_exception_and_closes_file_if_config_yaml_invalid(self, yaml_mock, open_stub):
        fake_file = Mock()
        open_stub.return_value = fake_file
        self.assertRaises(yaml.YAMLError, main.load_configurations)
        fake_file.close.assert_called_once()


    @patch('src.main.open')
    @patch('src.main.yaml.load', side_effect=Exception('something went wrong'))
    def test_load_configurations_propagates_exception_and_closes_file_if_one_is_raised(self, yaml_mock, open_stub):
        fake_file = Mock()
        open_stub.return_value = fake_file
        self.assertRaises(Exception, main.load_configurations)
        fake_file.close.assert_called_once()



if __name__ == '__main__':
    unittest.main()

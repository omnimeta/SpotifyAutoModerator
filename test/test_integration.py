import unittest
from unittest.mock import Mock, patch
import sys
import os
import re
import spotipy
import random
import string
from inputimeout import inputimeout, TimeoutOccurred
import src.main as main

# These tests serve the purpose of end-to-end tests.
# Only responses from external entities (such as the Spotify API and the user) are stubbed.
# Correctness of behaviour is tested by checking attempted calls to the Spotify API and
# any triggered system exit codes.

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.test_config_path = 'data/test/config'

        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())

    def tearDown(self):
        for filename in os.listdir(self.test_config_path):
            if re.search(filename, '^\.gitignore$') is None:
                os.remove('%s/%s' % (self.test_config_path, filename))


    @patch.object(sys, 'argv', [ '-h' ]) # stubbed user input
    @patch('src.main.spotipy.client.Spotify') # used to test behaviour
    def test_program_run_with_help_function(self, api_client_mock):
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 0)
        api_client_mock.assert_not_called()


    @patch.object(sys, 'argv', [ '--rdc' ]) # stubbed user input
    @patch('src.main.inputimeout', return_value='Y') # stubbed user input
    @patch('src.main.get_config_filepath') # allows different config file to be used
    @patch('src.main.spotipy.client.Spotify') # used to test behaviour
    def test_program_run_with_restore_default_config_function(self, api_client_mock, config_path_stub,
                                                              user_input_stub):
        test_config_file = self.test_config_path + '/config.yaml'
        config_path_stub.return_value = test_config_file
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        default_config_file = open('data/.default_config.yaml', 'r')
        default_config = default_config_file.read()
        default_config_file.close()
        config_file = open(test_config_file, 'r')
        config = config_file.read()
        config_file.close()

        self.assertEqual(sys_exit.exception.code, 0)
        self.assertEqual(default_config, config)
        api_client_mock.assert_not_called()


    @patch('src.main.get_config_filepath') # allows different config file to be used
    @patch('src.main.spotipy.client.Spotify') # used to test behaviour
    def test_program_run_with_invalid_config_file(self, api_client_mock, config_path_stub):
        test_config_file = self.test_config_path + '/config.yaml'
        config_path_stub.return_value = test_config_file

        # config data with missing URI for a playlist which should trigger an error
        config_data = """
---
PLAYLIST_CONFIG:
  DELAY_BETWEEN_SCANS: 1
  GLOBAL_WHITELIST: []
  GLOBAL_BLACKLIST: []
  PROTECTED_PLAYLISTS:
    - PlaylistLabel:
        blacklist:
          - blacklistedusername
ACCOUNT_CONFIG:
  USERNAME: spotifyusername
  CLIENT_ID: spotifyclientid
  CLIENT_SECRET: spotifyclientsecret
  REDIRECT_URI: spotifyredirecturi
LOG_CONFIG:
  FILE: data/test/log/log_file_path
  FORMAT: '%(levelname)s - %(message)s'
  CONSOLE_LEVEL: critical
  FILE_LEVEL: critical
"""

        test_config = open(test_config_file, 'w')
        test_config.write(config_data)
        test_config.close()

        with self.assertRaises(SystemExit) as sys_exit:
            main.main()

        self.assertEqual(sys_exit.exception.code, 1)
        api_client_mock.assert_not_called()


    @patch('src.main.get_config_filepath') # allows different config file to be used
    @patch('src.main.spotipy.client.Spotify') # used to test behaviour
    def test_program_run_with_invalid_config_yaml(self, api_client_mock, config_path_stub):
        test_config_file = self.test_config_path + '/config.yaml'
        config_path_stub.return_value = test_config_file
        test_config = open(test_config_file, 'w')
        test_config.write('not valid yaml')
        test_config.close()

        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 1)
        api_client_mock.assert_not_called()

if __name__ == '__main__':
    unittest.main()

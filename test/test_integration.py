import unittest
from unittest.mock import Mock, patch
import sys
import os
import re
import spotipy
import random
import string
import json
from time import time
from inputimeout import inputimeout, TimeoutOccurred
import src.main as main

# These tests serve the purpose of end-to-end tests.
# Only responses from external entities (such as the Spotify API and the user) are stubbed.
# Correctness of behaviour is tested by checking corretness of external interactions such as
# attempted API calls, saved backups, and exit codes.

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.test_config_path = 'data/test/config'
        self.test_backup_path = 'data/test/backups'
        self.test_log_path = 'data/test/log'

        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())

        # also clear any files before starting for consistency (e.g., if other tests don't cleanup)
        for dir_path in [ self.test_config_path, self.test_backup_path, self.test_log_path ]:
            for filename in os.listdir(dir_path):
                if re.search(filename, '^\.gitignore$') is None:
                    os.remove('%s/%s' % (dir_path, filename))

    def tearDown(self):
        for dir_path in [ self.test_config_path, self.test_backup_path, self.test_log_path ]:
            for filename in os.listdir(dir_path):
                if re.search(filename, '^\.gitignore$') is None:
                    os.remove('%s/%s' % (dir_path, filename))


    @patch.object(sys, 'argv', [ '-h' ]) # stubbed user input
    @patch('src.main.spotipy.client.Spotify') # used to monitor behaviour
    def test_program_run_with_help_function(self, api_client_mock):
        with self.assertRaises(SystemExit) as sys_exit:
            main.main()
        self.assertEqual(sys_exit.exception.code, 0)
        api_client_mock.assert_not_called()


    @patch.object(sys, 'argv', [ '--rdc' ]) # stubbed user input
    @patch('src.main.inputimeout', return_value='Y') # stubbed user input
    @patch('src.main.get_config_filepath') # allows different config file to be used
    @patch('src.main.spotipy.client.Spotify') # used to monitor behaviour
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
    @patch('src.main.spotipy.Spotify', return_value=spotipy.client.Spotify()) # used to monitor behaviour
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
  BACKUP_PATH: %s
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
  FILE: %s/info.log
  CONSOLE_LEVEL: critical
  FILE_LEVEL: critical
"""     % (self.test_backup_path, self.test_log_path)

        test_config = open(test_config_file, 'w')
        test_config.write(config_data)
        test_config.close()

        with self.assertRaises(SystemExit) as sys_exit:
            main.main()

        self.assertEqual(sys_exit.exception.code, 1)
        api_client_mock.assert_not_called()


    @patch('src.main.get_config_filepath') # allows different config file to be used
    @patch('src.main.spotipy.Spotify', return_value=spotipy.client.Spotify()) # used to monitor behaviour
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


    @patch.object(os, 'environ', {})
    @patch('src.integrity_manager.inputimeout', side_effect=[ 'no', 'yes', 'no' ]) # stubbed user input
    @patch('src.main.get_config_filepath') # allows different config file to be used
    @patch('src.main.spotipy.Spotify', return_value=spotipy.client.Spotify()) # used to monitor behaviour
    def test_program_run_simple_with_simple_playlist_config_no_protect_all_no_loop_mode(self, api_mock,
                                                                                        config_path_stub,
                                                                                        user_input_stub):
        # prepare config file
        test_config_file = self.test_config_path + '/config.yaml'
        config_path_stub.return_value = test_config_file
        test_config = open(test_config_file, 'w')
        config_data = """
PLAYLIST_CONFIG:
  DELAY_BETWEEN_SCANS: 120
  PROTECT_ALL: false
  GLOBAL_MODE: whitelist
  MAX_BACKUPS_PER_PLAYLIST: 1
  BACKUP_PATH: %s
  GLOBAL_WHITELIST:
    - friendaccount1
    - friendaccount2
    - friendaccount3
  PROTECTED_PLAYLISTS:
    - ProgressiveJazzFusion:
        uri: spotify:playlist:xxxxxxxxxxxxxxxxxxxxx1
    - ProkofievConcertoMix:
        uri: spotify:playlist:xxxxxxxxxxxxxxxxxxxxx2
    - Instrudjental:
        uri: spotify:playlist:xxxxxxxxxxxxxxxxxxxxx3
    - ModernAlternativeRnB:
        uri: spotify:playlist:xxxxxxxxxxxxxxxxxxxxx4
        blacklist:
          - spotifyuser1
ACCOUNT_CONFIG:
  USERNAME: testuser
  CLIENT_ID: testuserclientid
  CLIENT_SECRET: testuserclientsecret
  REDIRECT_URI: http://localhost:8080/
LOG_CONFIG:
  FILE: %s/info.log
  CONSOLE_LEVEL: critical
  FILE_LEVEL: critical
"""     % (self.test_backup_path, self.test_log_path)
        test_config.write(config_data)
        test_config.close()

        # prepare backups for playlist 1 and 3
        
        def save_backup(pl_id, pl_data):
            backup_file_path = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, str(time()))
            backup_file = open(backup_file_path, 'w')
            backup_file.write(json.dumps(pl_data))
            backup_file.close()
            return backup_file_path

        pl_ids = [ 'xxxxxxxxxxxxxxxxxxxxx%d' % (pl_num + 1) for pl_num in range(0, 6) ]
        pl_names = [ 'playlist%d' % (pl_num + 1) for pl_num in range(0, 6) ]

        backed_up_items = ([
            self.generate_track_uri() for i in range(0, 2) # items for playlist 1
        ], [
            self.generate_track_uri() for i in range(0, 2) # items for playlist 2
        ])
        backup_filepaths = []
        backup_filepaths.append(save_backup(pl_ids[0], {
            'name': 'playlist1',
            'items': [
                {
                    'name': 'pl1track%d' % (item_num + 1),
                    'uri': backed_up_items[0][item_num]
                } for item_num in range(0, len(backed_up_items[0]))
            ]
        }))
        backup_filepaths.append(save_backup(pl_ids[2], {
            'name': 'playlist3',
            'items': [
                {
                    'name': 'pl3track%d' % (item_num + 1),
                    'uri': backed_up_items[1][item_num]
                } for item_num in range(0, len(backed_up_items[1]))
            ]
        }))

        added_to_1_id = self.generate_spotify_id()
        added_to_4_id = self.generate_spotify_id()

        # prepare mock API functions

        def current_user_playlists(limit=50, offset=0):
            playlists = {
                'items': [
                    {
                        'collaborative': True,
                        'uri': 'spotify:playlist:' + pl_ids[pl_num],
                        'id': pl_ids[pl_num],
                        'name': pl_names[pl_num]
                    } for pl_num in range(0, len(pl_ids))
                ],
                'limit': limit,
                'offset': offset,
                'total': 6
            }
            playlists['items'][-1]['collaborative'] = False
            return playlists
        api_mock.return_value.current_user_playlists = Mock(side_effect=current_user_playlists)

        def playlist(pl_id, fields=None):
            for i in range(0, len(pl_ids)):
                if pl_id == pl_ids[i]:
                    return { 'name': pl_names[i]  }
            return None
        api_mock.return_value.playlist = Mock(side_effect=playlist)


        # for playlist 1 and 3 (because they have a backup),
        # there are 3 calls to api.playlist_items for the same playlist in a row
        # - one during cleaning
        # - one for removal restore
        # - one for backup
        # for playlists with no backup there are only two calls
        playlist_items_responses = [
            { # playlist 1
                'items': [
                    { # this item was in the playlist before (and should be authorized)
                        'track': {
                            'name': 'pl1track1',
                            'uri': backed_up_items[0][0],
                        },
                        'added_at': time() - 40000, # arbitrary
                        'added_by': {
                            'id': 'friendaccount1'
                        },
                        'position': 0
                    },
                    { # this item was recently added (should be unauthorized)
                        'track': {
                            'name': 'pl1newtrack1',
                            'uri': 'spotify:track:' + added_to_1_id
                        },
                        'added_at': time() - 2000, # arbitrary
                        'added_by': {
                            'id': 'unknownspotifyuser'
                        },
                        'position': 1
                    }
                    # the other item that was in the playlist before was removed without approval
                ],
                'limit': 100,
                'offset': 0,
                'total': 2
            },
            { # playlist 1
                'items': [
                    {
                        'track': {
                            'name': 'pl1track1',
                            'uri': backed_up_items[0][0],
                        },
                        'added_at': time() - 40000, # arbitrary
                        'added_by': {
                            'id': 'friendaccount1'
                        },
                        'position': 0
                    }
                ],
                'limit': 100,
                'offset': 0,
                'total': 1
            },
            { # playlist 1
                'items': [
                    { # this item was in the playlist before (and should be authorized)
                        'track': {
                            'name': 'pl1track1',
                            'uri': backed_up_items[0][0],
                        },
                        'added_at': time() - 40000, # arbitrary
                        'added_by': {
                            'id': 'friendaccount1'
                        },
                        'position': 0
                    },
                    { # this item was restored
                        'track': {
                            'name': 'pl1track2',
                            'uri': backed_up_items[0][1],
                        },
                        'added_at': time(), # arbitrary
                        'added_by': {
                            'id': 'testuser'
                        },
                        'position': 1
                    }
                ],
                'limit': 100,
                'offset': 0,
                'total': 2
            },
            { # playlist 2
                'items': [],
                'limit': 100,
                'offset': 0,
                'total': 0
            },
            { # playlist 2 - unchanged after checking for unauthorized additions
                'items': [],
                'limit': 100,
                'offset': 0,
                'total': 0
            },
            { # playlist 3
                'items': [], # both items were removed (1st approved, 2nd unapproved)
                'limit': 100,
                'offset': 0,
                'total': 0
            },
            { # playlist 3 - unchanged after checking for unauthorized additions
                'items': [],
                'limit': 100,
                'offset': 0,
                'total': 0
            },
            { # playlist 3 - one removal restored
                'items': [
                    { # this item was restored
                        'track': {
                            'name': 'pl3track2',
                            'uri': backed_up_items[1][1],
                        },
                        'added_at': time(), # arbitrary
                        'added_by': {
                            'id': 'testuser'
                        },
                        'position': 0
                    }
                ],
                'limit': 100,
                'offset': 0,
                'total': 1
            },
            { # playlist 4
                'items': [
                    { # added by blacklist user (should be unauthorized)
                        'track': {
                            'name': 'pl4newtrack',
                            'uri': 'spotify:track:' + added_to_4_id,
                        },
                        'added_at': time() - 50000, # arbitrary
                        'added_by': {
                            'id': 'spotifyuser1'
                        },
                        'position': 0
                    }
                ],
                'limit': 100,
                'offset': 0,
                'total': 1
            },
            { # playlist 4 - one addition was removed
                'items': [],
                'limit': 100,
                'offset': 0,
                'total': 0
            }
        ]

        api_mock.return_value.playlist_items = Mock(side_effect=playlist_items_responses)
        api_mock.return_value.playlist_add_items = Mock()
        api_mock.return_value.playlist_remove_specific_occurrences_of_items = Mock()

        with self.assertRaises(SystemExit) as sys_exit:
            main.main()

        # use API mocks to test for correct interaction with external API

        api_mock.assert_called_once()
        self.assertEqual(os.environ['SPOTIPY_CLIENT_ID'], 'testuserclientid')
        self.assertEqual(os.environ['SPOTIPY_CLIENT_SECRET'], 'testuserclientsecret')
        self.assertEqual(os.environ['SPOTIPY_REDIRECT_URI'], 'http://localhost:8080/')

        # since PROTECT_ALL=false, the only time all playlists are retrieved is for validation of
        # the protected playlist list
        self.assertEqual(api_mock.return_value.current_user_playlists.call_count, 1)

        self.assertEqual(api_mock.return_value.playlist_items.call_count, 10)
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[0][0][0], pl_ids[0])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[1][0][0], pl_ids[0])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[2][0][0], pl_ids[0])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[3][0][0], pl_ids[1])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[4][0][0], pl_ids[1])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[5][0][0], pl_ids[2])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[6][0][0], pl_ids[2])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[7][0][0], pl_ids[2])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[8][0][0], pl_ids[3])
        self.assertEqual(api_mock.return_value.playlist_items.call_args_list[9][0][0], pl_ids[3])

        # two tracks should have been removed: one from playlist 1 and one from playlist 4
        self.assertEqual(api_mock.return_value.playlist_remove_specific_occurrences_of_items.call_count, 2)
        self.assertEqual(api_mock.return_value.playlist_remove_specific_occurrences_of_items.call_args_list[0][0][0], pl_ids[0])
        self.assertEqual(
            api_mock.return_value.playlist_remove_specific_occurrences_of_items.call_args_list[0][0][1], [
                {
                    'uri': 'spotify:track:' + added_to_1_id,
                    'positions': [ 1 ]
                }
            ])
        self.assertEqual(api_mock.return_value.playlist_remove_specific_occurrences_of_items.call_args_list[1][0][0], pl_ids[3])
        self.assertEqual(
            api_mock.return_value.playlist_remove_specific_occurrences_of_items.call_args_list[1][0][1], [
                {
                    'uri': 'spotify:track:' + added_to_4_id,
                    'positions': [ 0 ]
                }
            ])

        # two tracks should have been restored: one from playlist 1 and one from playlist 3
        self.assertEqual(api_mock.return_value.playlist_add_items.call_count, 2)
        self.assertEqual(api_mock.return_value.playlist_add_items.call_args_list[0][0][0], pl_ids[0])
        self.assertEqual(api_mock.return_value.playlist_add_items.call_args_list[0][0][1], [ backed_up_items[0][1] ])
        self.assertEqual(api_mock.return_value.playlist_add_items.call_args_list[1][0][0], pl_ids[2])
        self.assertEqual(api_mock.return_value.playlist_add_items.call_args_list[1][0][1], [ backed_up_items[1][1] ])


        # use backups to test for correct end-state

        def get_backups(pl_id):
            pl_backups = []
            new_backup_files = os.listdir(self.test_backup_path)
            for filename in new_backup_files:
                if re.search('^%s_[0-9]{10}\.[0-9]+\.backup\.json$' % pl_id, filename) is not None:
                    pl_backups.append(filename)
            return pl_backups

        all_pl_backups = [ get_backups(pl_id) for pl_id in pl_ids ]
        for backups in all_pl_backups[:-2]:
            self.assertEqual(len(backups), 1)
        for backups in all_pl_backups[-2:]:
            self.assertEqual(len(backups), 0)

        def get_backup_data(filename):
            try:
                backup_file = open('%s/%s' % (self.test_backup_path, filename))
                backup_info = json.loads(backup_file.read())
                return backup_info
            except Exception as err:
                print(err)
            finally:
                if backup_file is not None:
                    backup_file.close()

        self.assertEqual(get_backup_data(all_pl_backups[0][0]), {
            'name': pl_names[0],
            'items': [
                {
                    'name': 'pl1track1',
                    'uri': backed_up_items[0][0],
                    'position': 0
                },
                {
                    'name': 'pl1track2',
                    'uri': backed_up_items[0][1],
                    'position': 1
                }
            ]
        })
        self.assertEqual(get_backup_data(all_pl_backups[1][0]), {
            'name': pl_names[1],
            'items': []
        })
        self.assertEqual(get_backup_data(all_pl_backups[2][0]), {
            'name': pl_names[2],
            'items': [
                {
                    'name': 'pl3track2',
                    'uri': backed_up_items[1][1],
                    'position': 0
                },
            ]
        })
        self.assertEqual(get_backup_data(all_pl_backups[3][0]), {
            'name': pl_names[3],
            'items': [
            ]
        })

        # check program exited correctly

        self.assertEqual(sys_exit.exception.code, 0)



if __name__ == '__main__':
    unittest.main()

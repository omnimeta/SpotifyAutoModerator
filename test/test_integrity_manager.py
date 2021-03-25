import unittest
import logging
import random
import string
import json
import os
import re
from time import time, sleep
from unittest.mock import Mock, patch
import spotipy
import inputimeout
from src.integrity_manager import IntegrityManager

class TestIntegrityManager(unittest.TestCase):

    def setUp(self):
        self.test_logger = logging.getLogger('TestIntegrityManager')
        log_handler = logging.StreamHandler()
        log_handler.setLevel('CRITICAL')
        self.test_logger.addHandler(log_handler)

        self.test_backup_path = 'data/test/backups' # no trailing forward slash /
        self.manager = IntegrityManager(self.test_logger, spotipy.client.Spotify(), {
            'BACKUP_PATH': self.test_backup_path,
            'PROTECTED_PLAYLISTS': [],
            'MAX_BACKUPS_PER_PLAYLIST': 2
        })

        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())

        # also clear any files before starting for consistency (e.g., if other tests don't cleanup)
        for filename in os.listdir(self.test_backup_path):
            if re.search(filename, '^\.gitignore$') is None:
                os.remove('%s/%s' % (self.test_backup_path, filename))


    def tearDown(self):
        for filename in os.listdir(self.test_backup_path):
            if re.search(filename, '^\.gitignore$') is None:
                os.remove('%s/%s' % (self.test_backup_path, filename))


    def test_integrity_manager_ignores_trailing_slashes_on_the_backup_path(self):
        self.assertEqual(IntegrityManager(self.test_logger, spotipy.client.Spotify(), {
            'BACKUP_PATH': 'test_backup_path//',
            'PROTECTED_PLAYLISTS': [],
            'MAX_BACKUPS_PER_PLAYLIST': 2
        }).config['BACKUP_PATH'][-1], 'h')


    @patch('src.integrity_manager.SpotifyHelper', return_value=Mock())
    def test_integrity_manager_passes_its_logger_and_api_client_to_spotify_helper(self, helper_mock):
        particular_client = spotipy.client.Spotify()
        IntegrityManager(self.test_logger, particular_client, {
            'BACKUP_PATH': 'test_backup_path',
            'PROTECTED_PLAYLISTS': [],
            'MAX_BACKUPS_PER_PLAYLIST': 1
        })
        self.assertEqual(len(helper_mock.call_args[0]), 1)
        self.assertEqual(len(helper_mock.call_args[1].keys()), 1)
        helper_mock.assert_called_once_with(self.test_logger.getChild('IntegrityManager'), api=particular_client)



    # ----- Tests for IntegrityManager.run ----- #

    def test_run_takes_a_backup_and_does_not_check_integrity_of_a_playlist_with_no_existing_backup(self):
        pl_id = self.generate_spotify_id()
        self.manager.find_latest_backup = Mock(return_value=None)
        self.manager.backup_playlist = Mock()
        self.manager.get_removals = Mock()
        self.manager.run({ 'uri': 'spotify:playlist:' + pl_id })
        self.assertEqual(len(self.manager.backup_playlist.call_args[0]), 1)
        self.manager.backup_playlist.assert_called_once_with(pl_id)
        self.manager.get_removals.assert_not_called


    def test_run_restores_only_unapproved_removals_based_on_the_latest_backup(self):
        latest_backup = {
            'name': 'playlistname',
            'items': []
        }
        self.manager.find_latest_backup = Mock(return_value=latest_backup)

        # backup_playlists and manage_redundant_backups need to be stubbed to avoid them
        # trying to backup a fake/test playlist
        self.manager.backup_playlist = Mock()
        self.manager.manage_redundant_backups = Mock()

        pl_id = self.generate_spotify_id()
        removals = [
            {
                'name': 'removed track %d' % num,
                'uri': self.generate_track_uri()
            } for num in range(0, 3)
        ]
        unapproved = [ removals[0], removals[-1] ]
        self.manager.get_removals = Mock(return_value=removals)
        self.manager.get_unapproved_removals = Mock(return_value=unapproved)
        self.manager.spotify_helper.add_items_to_playlist = Mock()

        self.manager.run({ 'uri': 'spotify:playlist:' + pl_id })
        self.assertEqual(len(self.manager.get_removals.call_args[0]), 2)
        self.manager.get_removals.assert_called_once_with(pl_id, latest_backup)
        self.assertEqual(len(self.manager.spotify_helper.add_items_to_playlist.call_args[0]), 2)
        self.manager.spotify_helper.add_items_to_playlist.assert_called_once_with(pl_id, unapproved)


    def test_run_backs_up_playlist_and_manages_redundant_backups_if_removal_of_unapproved_additions_is_successful(self):
        pl_id = self.generate_spotify_id()
        removals = [
            {
                'name': 'removed track %d' % num,
                'uri': self.generate_track_uri()
            } for num in range(0, 3)
        ]
        unapproved = [ removals[0], removals[-1] ]
        self.manager.backup_playlist = Mock()
        self.manager.manage_redundant_backups = Mock()

        # the following mocks ensure that execution proceeds beyond restoration of unapproved removals
        self.manager.find_latest_backup = Mock(return_value={
            'name': 'playlistname',
            'items': []
        })
        self.manager.get_removals = Mock(return_value=removals)
        self.manager.get_unapproved_removals = Mock(return_value=unapproved)
        self.manager.spotify_helper.add_items_to_playlist = Mock()

        self.manager.run({ 'uri': 'spotify:playlist:' + pl_id })
        self.assertEqual(len(self.manager.backup_playlist.call_args[0]), 1)
        self.manager.backup_playlist.assert_called_once_with(pl_id)
        self.manager.manage_redundant_backups.assert_called_once_with(pl_id)


    def test_run_does_not_backup_a_playlist_if_an_exception_is_raised_during_attempting_restoration_of_removals(self):
        pl_id = self.generate_spotify_id()
        removals = [
            {
                'name': 'removed track %d' % num,
                'uri': self.generate_track_uri()
            } for num in range(0, 3)
        ]
        unapproved = [ removals[0], removals[-1] ]
        self.manager.backup_playlist = Mock()
        self.manager.manage_redundant_backups = Mock()

        self.manager.find_latest_backup = Mock(return_value={
            'name': 'playlistname',
            'items': []
        })
        self.manager.get_removals = Mock(return_value=removals)
        self.manager.get_unapproved_removals = Mock(return_value=unapproved)
        self.manager._restore_removals = Mock(side_effect=Exception('unexpected error'))

        self.manager.run({ 'uri': 'spotify:playlist:' + pl_id })
        self.manager.backup_playlist.assert_not_called()
        self.manager.manage_redundant_backups.assert_not_called()


    def test_run_does_not_backup_a_playlist_if_a_timeout_exception_is_raised_while_asking_for_approval(self):
        pl_id = self.generate_spotify_id()
        removals = [
            {
                'name': 'removed track %d' % num,
                'uri': self.generate_track_uri()
            } for num in range(0, 3)
        ]
        self.manager.backup_playlist = Mock()
        self.manager.manage_redundant_backups = Mock()

        self.manager.find_latest_backup = Mock(return_value={
            'name': 'playlistname',
            'items': []
        })
        self.manager.get_removals = Mock(return_value=removals)
        self.manager.get_unapproved_removals = Mock(side_effect=inputimeout.TimeoutOccurred())
        self.manager._restore_removals = Mock()

        self.manager.run({ 'uri': 'spotify:playlist:' + pl_id })
        self.manager.backup_playlist.assert_not_called()
        self.manager.manage_redundant_backups.assert_not_called()


    # ----- Tests for IntegrityManager.find_latest_backup ----- #
    
    def test_find_latest_backup_returns_backup_imported_from_file_with_latest_timestamp(self):
        def create_blank_backup_file(pl_id):
            ts = str(time())
            filename = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, ts)
            bu_file = open(filename, 'w')
            bu_file.write('playlist_backup')
            bu_file.close()
            return {
                'filename': filename,
                'timestamp': ts
            }

        pl_id = self.generate_spotify_id()
        backups = []
        for i in range(0, 3):
            backups.append(create_blank_backup_file(pl_id))
            sleep(0.1)

        self.manager._load_backup_from_file = Mock(return_value='correct_return_val')
        self.assertEqual(self.manager.find_latest_backup(pl_id), 'correct_return_val')
        self.assertEqual(self.manager._load_backup_from_file.call_args[0][0], backups[-1]['filename'])
        self.assertEqual(self.manager._load_backup_from_file.call_args[0][0], backups[-1]['filename'])

    def test_find_latest_backup_returns_none_if_the_playlist_has_no_backups(self):
        def create_blank_backup_file(pl_id):
            ts = str(time())
            filename = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, ts)
            bu_file = open(filename, 'w')
            bu_file.write('playlist_backup')
            bu_file.close()
            return {
                'filename': filename,
                'timestamp': ts
            }

        pl_id = self.generate_spotify_id()
        create_blank_backup_file(self.generate_spotify_id())
        self.assertIsNone(self.manager.find_latest_backup(pl_id))


    # ----- Tests for IntegrityManager.get_removals ----- #

    def test_get_removals_returns_only_items_in_backup_that_are_not_currently_in_the_playlist(self):
        backup = {
            'name': 'playlist_name',
            'items': [ { 'name': 'track%d' % num, 'uri': self.generate_track_uri() } for num in range(0, 5) ]
        }
        self.manager.spotify_helper.get_all_items_in_playlist = Mock(return_value=[
            {
                'track': {
                    'name': track['name'],
                    'uri': track['uri']
                }
            } for track in backup['items'][:3]
        ])
        self.assertEqual(self.manager.get_removals(self.generate_spotify_id(), backup), backup['items'][3:])


    # ----- Tests for IntegrityManager.get_unapproved_removals ------ #

    def test_get_unapproved_removals_returns_only_unapproved_removals(self):
        removals = [ { 'uri': self.generate_track_uri } for i in range(0, 5) ]
        self.manager._user_approves_removal = Mock(side_effect=[
            True, True, False, True, False
        ])
        expected_removals = [ removals[2], removals[-1] ]
        self.assertEqual(self.manager.get_unapproved_removals(removals, 'pl_name'), expected_removals)


    def test_get_unapproved_removals_propagates_timeout_exception_outwards(self):
        removals = [ { 'uri': self.generate_track_uri } for i in range(0, 5) ]
        self.manager._user_approves_removal = Mock(side_effect=inputimeout.TimeoutOccurred())

        self.assertRaises(inputimeout.TimeoutOccurred, self.manager.get_unapproved_removals, removals, 'pl_name')


    # ----- Tests for IntegrityManager.backup_playlist ---- #

    def test_backup_playlist_saves_playlist_backup_to_correct_filepath(self):
        pl_id = self.generate_spotify_id()
        self.manager.api.playlist = Mock(return_value={
            'name': 'playlist name'
        })
        self.manager.spotify_helper.get_all_items_in_playlist = Mock(return_value=[])
        self.manager.backup_playlist(pl_id)
        relevant_files = []
        for fl in os.listdir(self.test_backup_path):
            if re.search('^[A-Za-z0-9]{22}_[0-9]{10}\.[0-9]+\.backup\.json$', fl) is not None:
                relevant_files.append(fl)
        self.assertEqual(len(relevant_files), 1)
        self.assertIsNotNone(re.search('^%s_[0-9]{10}\.[0-9]+\.backup\.json$' % pl_id, relevant_files[0]))


    def test_backup_playlist_saves_playlist_backup_in_correct_format(self):
        pl_id = self.generate_spotify_id()
        self.manager.api.playlist = Mock(return_value={
            'name': 'playlist name'
        })
        items = [
            {
                'track': {
                    'name': 'track1',
                    'uri': self.generate_track_uri(),
                    'artists': [
                    ]
                },
                'position': 0
            },
            {
                'track': {
                    'name': 'track2',
                    'uri': self.generate_track_uri(),
                    'artists': [
                        {
                            'name': 'artist1'
                        },
                        {
                            'name': 'artist2'
                        }
                    ]
                },
                'position': 1
            }
        ]
        self.manager.spotify_helper.get_all_items_in_playlist = Mock(return_value=items)
        self.manager.backup_playlist(pl_id)
        relevant_backups = []
        for backup in os.listdir(self.test_backup_path):
            if re.search('^[A-Za-z0-9]{22}_[0-9]{10}\.[0-9]+\.backup\.json$', backup) is not None:
                relevant_backups.append(backup)
        backup_file = open('%s/%s' % (self.test_backup_path, relevant_backups[0]), 'r')
        backup_content = json.loads(backup_file.read())
        backup_file.close()
        self.assertEqual({
            'name': 'playlist name',
            'items': [
                {
                    'name': items[0]['track']['name'],
                    'artists': '',
                    'uri': items[0]['track']['uri'],
                    'position': 0
                },
                {
                    'name': items[1]['track']['name'],
                    'artists': 'artist1, artist2',
                    'uri': items[1]['track']['uri'],
                    'position': 1
                }
            ]
        }, backup_content)


    # ----- Tests for IntegrityManager._backup_info_is_valid ----- #

    def test_backup_info_is_valid_returns_false_if_it_does_not_incude_a_nonempty_string_name(self):
        self.assertFalse(self.manager._backup_info_is_valid({
            'items': []
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 10,
            'items': []
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': '',
            'items': []
        }, 'filename'))


    def test_backup_info_is_valid_returns_false_if_it_does_not_include_a_list_of_items(self):
        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name'
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': 'not_a_list'
        }, 'filename'))


    def test_backup_info_is_valid_returns_false_if_any_item_is_not_a_dict(self):
        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                'not a dict',
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))


    def test_backup_info_is_valid_returns_false_if_any_item_has_no_valid_uri(self):
        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'name': 'track name'
                },
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'name': 'track name',
                    'uri': 10
                },
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'name': 'track name',
                    'uri': 'not_a_valid_url'
                },
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))


    def test_backup_info_is_valid_returns_false_if_any_item_has_no_valid_name(self):
        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'uri': self.generate_track_uri()
                },
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'name': '',
                    'uri': self.generate_track_uri()
                },
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))

        self.assertFalse(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'name': 10,
                    'uri': self.generate_track_uri()
                },
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))


    def test_backup_info_is_valid_returns_true_if_it_has_a_name_and_no_items_or_a_list_of_valid_items(self):
        self.assertTrue(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': []
        }, 'filename'))

        self.assertTrue(self.manager._backup_info_is_valid({
            'name': 'playlist name',
            'items': [
                {
                    'name': 'valid track',
                    'uri': self.generate_track_uri()
                }
            ]
        }, 'filename'))


    # ----- Tests for IntegrityManager._load_backup_from_file ----- \

    def test_load_backup_from_file_returns_none_if_the_file_does_not_exist(self):
        self.assertIsNone(self.manager._load_backup_from_file('not_a_real_file'))


    def test_load_backup_from_file_returns_the_data_in_the_correct_format_if_it_is_valid(self):
        def create_backup_file(pl_id, name, items):
            ts = str(time())
            filename = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, ts)
            bu_file = open(filename, 'w')
            bu_file.write(json.dumps({
                'name': name,
                'items': items
            }))
            bu_file.close()
            return filename

        items = [
            {
                'name': 'track name 1',
                'uri': self.generate_track_uri()
            },
            {
                'name': 'track name 1',
                'uri': self.generate_track_uri()
            }
        ]
        backup_info = {
            'name': 'playlist name',
            'items': items
        }
        filename = create_backup_file(self.generate_spotify_id(), 'playlist name', items)
        self.manager._backup_info_is_valid = Mock(return_value=True)
        self.assertEqual(self.manager._load_backup_from_file(filename), backup_info)
        self.manager._backup_info_is_valid.assert_called_once_with(backup_info, filename)
        self.assertEqual(len(self.manager._backup_info_is_valid.call_args[0]), 2)


    def test_load_backup_from_file_returns_none_if_the_imported_backup_is_not_valid(self):
        def create_backup_file(pl_id, name, items):
            ts = str(time())
            filename = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, ts)
            bu_file = open(filename, 'w')
            bu_file.write(json.dumps({
                'name': name,
                'items': items
            }))
            bu_file.close()
            return filename

        filename = create_backup_file(self.generate_spotify_id(), 'playlist name', [])
        self.manager._backup_info_is_valid = Mock(return_value=False)
        self.assertIsNone(self.manager._load_backup_from_file(filename))


    def test_load_backup_from_file_returns_none_if_the_json_data_is_invalid_and_cannot_be_decoded(self):
        def create_invalid_backup_file(pl_id, name, items):
            # reading the file created by this function will cause a JSONDecodeError to be raised
            ts = str(time())
            filename = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, ts)
            bu_file = open(filename, 'w')
            bu_file.write('this is not valid json')
            bu_file.close()
            return filename

        filename = create_invalid_backup_file(self.generate_spotify_id(), 'playlist name', [])
        self.manager._backup_info_is_valid = Mock(return_value=True)
        self.assertIsNone(self.manager._load_backup_from_file(filename))



    @patch('src.integrity_manager.json.loads', side_effect=Exception('something went wrong'))
    def test_load_backup_from_file_returns_none_if_reading_the_file_raises_an_unexpected_exception(self, jsonLoadsMock):
        def create_backup_file(pl_id, name, items):
            # the backup itself should be valid so a normal JSONDecodeError is not raised first
            ts = str(time())
            filename = '%s/%s_%s.backup.json' % (self.test_backup_path, pl_id, ts)
            bu_file = open(filename, 'w')
            bu_file.write(json.dumps({
                'name': name,
                'items': items
            }))
            bu_file.close()
            return filename

        filename = create_backup_file(self.generate_spotify_id(), 'playlist name', [])
        self.manager._backup_info_is_valid = Mock(return_value=True)
        self.assertIsNone(self.manager._load_backup_from_file(filename))


    # ----- Tests for IntegrityManager.manage_redundant_backups ----- #

    def test_manage_redundant_backups_deletes_nothing_if_a_playlist_has_less_than_the_maximum_backups(self):
        def create_backup_file(pl_id, name, items):
            ts = str(time())
            filename = '%s_%s.backup.json' % (pl_id, ts)
            bu_file = open('%s/%s' % (self.test_backup_path, filename), 'w')
            bu_file.write(json.dumps({
                'name': name,
                'items': items
            }))
            bu_file.close()
            return filename

        pl_id = self.generate_spotify_id()
        backups = []
        for i in range(0, 2):
            backups.append(create_backup_file(pl_id, 'playlist name', []))
        self.manager.manage_redundant_backups(pl_id)

        relevant_backups = []
        for backup in os.listdir(self.test_backup_path):
            if re.search('^[A-Za-z0-9]{22}_[0-9]{10}\.[0-9]+\.backup\.json$', backup) is not None:
                relevant_backups.append(backup)
        for backup in backups:
            self.assertTrue(backup in relevant_backups)


    def test_manage_redundant_backups_deletes_oldest_backups_until_the_number_remaining_is_equal_to_the_maximum(self):
        def create_backup_file(pl_id, name, items):
            ts = str(time())
            filename = '%s_%s.backup.json' % (pl_id, ts)
            bu_file = open('%s/%s' % (self.test_backup_path, filename), 'w')
            bu_file.write(json.dumps({
                'name': name,
                'items': items
            }))
            bu_file.close()
            return filename

        pl_id = self.generate_spotify_id()
        backups = []
        for i in range(0, 4):
            backups.append(create_backup_file(pl_id, 'playlist name', []))
        self.manager.manage_redundant_backups(pl_id)

        relevant_backups = []
        for backup in os.listdir(self.test_backup_path):
            if re.search('^[A-Za-z0-9]{22}_[0-9]{10}\.[0-9]+\.backup\.json$', backup) is not None:
                relevant_backups.append(backup)
        for backup in backups[0:2]:
            self.assertFalse(backup in relevant_backups)
        for backup in backups[2:]:
            self.assertTrue(backup in relevant_backups)


    # ----- Tests for IntegrityManager._user_approves_removal ----- #

    @patch('src.integrity_manager.inputimeout', side_effect=inputimeout.TimeoutOccurred())
    def test_user_approves_removal_propagates_timeout_exception_outwards_if_a_timeout_occurs(self, inputFuncMock):
        self.assertRaises(inputimeout.TimeoutOccurred, self.manager._user_approves_removal, {
            'name': 'track to be removed',
            'uri': self.generate_track_uri(),
                'artists': [
                    {
                        'name': 'artist1',
                    }
                ]
        }, 'playlist name', 5)


    @patch('src.integrity_manager.inputimeout', return_value='')
    def test_user_approves_removal_returns_false_if_user_input_is_empty(self, inputFuncMock):
        self.assertFalse(self.manager._user_approves_removal({
            'name': 'track to be removed',
            'uri': self.generate_track_uri(),
                'artists': [
                    {
                        'name': 'artist1',
                    },
                    {
                        'name': 'artist2',
                    }
                ]
        }, 'playlist name', 5))


    @patch('src.integrity_manager.inputimeout', return_value='notyes')
    def test_user_approves_removal_returns_false_if_user_input_is_nonempty_but_is_not_some_variant_of_yes(self, inputFuncMock):
        self.assertFalse(self.manager._user_approves_removal({
            'name': 'track to be removed',
            'uri': self.generate_track_uri(),
            'artists': []
        }, 'playlist name', 5))


    @patch('src.integrity_manager.inputimeout')
    def test_user_approves_removal_returns_true_if_user_input_is_some_variant_of_yes(self, inputFuncMock):
        variants_of_yes = ['Y', 'y', 'YES', 'Yes', 'yes']
        for yes in variants_of_yes:
            inputFuncMock.return_value = yes
            self.assertTrue(self.manager._user_approves_removal({
                'name': 'track to be removed',
                'uri': self.generate_track_uri(),
                'artists': [
                    {
                        'name': 'artist1',
                    },
                    {
                        'name': 'artist2',
                    }
                ]
            }, 'playlist name', 5))



if __name__ == '__main__':
    unittest.main()

import unittest
import logging
import random
import string
from unittest.mock import Mock, patch
import spotipy
from src.playlist_cleaner import PlaylistCleaner
from src.spotify_helper import SpotifyHelper

class TestPlaylistCleaner(unittest.TestCase):

    def setUp(self):
        self.test_logger = logging.getLogger('TestPlaylistCleaner')
        log_handler = logging.StreamHandler()
        log_handler.setLevel('CRITICAL')
        self.test_logger.addHandler(log_handler)
        self.test_api =  spotipy.client.Spotify()
        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())

    # ----- Tests for PlaylistCleaner.run ----- #

    def test_run_removes_only_unauthorized_items(self):
        mock_api = spotipy.client.Spotify()
        pl_id = self.generate_spotify_id()
        config = {
            'PROTECT_ALL': False,
            'PROTECTED_PLAYLISTS': [
                { 'uri': 'spotify:playlist:' + pl_id }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, mock_api, 'playlist_owner', config)
        unauth_items = [
            {
                'name': 'unauth_item_1',
                'uri': self.generate_track_uri()
            },
            {
                'name': 'unauth_item_2',
                'uri': self.generate_track_uri()
            }
        ]
        cleaner.find_unauthorized_additions = Mock(return_value=unauth_items)
        cleaner.remove_playlist_items = Mock()
        cleaner.run({ 'uri': 'spotify:playlist:' + pl_id})
        self.assertEqual(len(cleaner.find_unauthorized_additions.call_args[0]), 1)
        cleaner.find_unauthorized_additions.called_once_with(pl_id)


    # ----- Tests for PlaylistCleaner.find_unauthorized_additions ----- #

    def test_find_unauthorized_additions_returns_only_unauthorized_additions(self):
        pl_id = self.generate_spotify_id()
        items = [
            {
                'track': {
                    'uri': self.generate_track_uri(),
                    'name': 'track_name'
                },
                'added_at': 'added_at_timestamp',
                'added_by': { 'id': self.generate_spotify_id() },
                'position': index
            } for index in range(0, 200)
        ]
        mock_api = spotipy.client.Spotify()
        mock_api.playlist = Mock(return_value={ 'name': 'playlist_name' })

        cleaner = PlaylistCleaner(self.test_logger, mock_api, 'playlist_owner', {})
        cleaner.spotify_helper.get_all_items_in_playlist = Mock(return_value=items)
        cleaner.playlist_addition_is_authorized = Mock(side_effect=[
            i not in [22, 60, 129] for i in range(0, len(items))
        ])
        result = cleaner.find_unauthorized_additions(pl_id)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['uri'], items[22]['track']['uri'])
        self.assertEqual(result[1]['uri'], items[60]['track']['uri'])
        self.assertEqual(result[2]['uri'], items[129]['track']['uri'])


    # ----- Tests for PlaylistCleaner.playlist_addition_is_authorized ----- #

    def test_playlist_addition_is_authorized_returns_true_if_adder_is_playlist_owner(self):
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', {})
        self.assertTrue(cleaner.playlist_addition_is_authorized('owner_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_false_playlist_has_no_local_or_global_restrictions(self):
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {   'myplaylist': {
                        'uri': 'spotify:playlist' + pl_id
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_true_if_playlist_has_only_local_blacklist_and_adder_not_blacklisted(self):
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'blacklist': []
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_false_if_playlist_has_only_local_blacklist_and_adder_is_blacklisted(self):
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'blacklist': [ 'adder_id' ]
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_true_if_playlist_has_only_local_whitelist_and_adder_is_whitelisted(self):
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'whitelist': [ 'adder_id' ]
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_false_if_playlist_has_only_local_whitelist_and_adder_not_whitelisted(self):
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'whitelist': []
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_true_if_adder_locally_whitelisted_but_explicitly_not_blacklisted(self):
        # this spec/fixture means blacklist overrides whitelist if a playlist configuration has both!
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'blacklist': [],
                        'whitelist': [ 'adder_id' ]
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_false_if_adder_both_locally_whitelisted_and_blacklisted(self):
        # this spec/fixture means blacklist overrides whitelist if a playlist configuration has both!
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'blacklist': [ 'adder_id' ],
                        'whitelist': [ 'adder_id' ]
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_true_if_adder_both_locally_explicitly_not_whitelisted_and_not_blacklisted(self):
        # this spec/fixture means blacklist overrides whitelist if a playlist configuration has both!
        pl_id = self.generate_spotify_id()
        pl_config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'blacklist': [],
                        'whitelist': []
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', pl_id))


    def test_playlist_addition_is_authorized_returns_true_if_global_mode_is_blacklist_and_adder_not_globally_blacklisted(self):
        pl_config = {
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_BLACKLIST': []
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_false_if_global_mode_is_blacklist_and_adder_globally_blacklisted(self):
        pl_config = {
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_BLACKLIST': [ 'adder_id' ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_false_if_global_mode_is_whitelist_and_adder_not_globally_whitelisted(self):
        pl_config = {
            'GLOBAL_MODE': 'whitelist',
            'GLOBAL_WHITELIST': []
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_true_if_global_mode_is_whitelist_and_adder_globally_whitelisted(self):
        pl_config = {
            'GLOBAL_MODE': 'whitelist',
            'GLOBAL_WHITELIST': [ 'adder_id' ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_true_adder_is_locally_authorized_but_globally_unauthorized(self):
        # this spec/fixture means local authorization overrides global authorization!
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', {})
        cleaner._local_authorization = Mock(return_value='authorized')
        cleaner._global_authorization = Mock(return_value='unauthorized')
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_false_adder_is_locally_unauthorized_but_globally_authorized(self):
        # this spec/fixture means local authorization overrides global authorization!
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', {})
        cleaner._local_authorization = Mock(return_value='unauthorized')
        cleaner._global_authorization = Mock(return_value='authorized')
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_true_if_adder_is_playlist_owner_regardless_of_local_and_global_restrictions(self):
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', {})
        cleaner._local_authorization = Mock(return_value='unauthorized')
        cleaner._global_authorization = Mock(return_value='unauthorized')
        self.assertTrue(cleaner.playlist_addition_is_authorized('owner_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_ignores_global_whitelist_if_global_mode_is_blacklist(self):
        pl_config = {
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_WHITELIST': [ 'adder_id' ],
            'GLOBAL_BLACKLIST': [ 'adder_id' ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))

        pl_config = {
            'GLOBAL_MODE': 'blacklist',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': []
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_ignores_global_blacklist_if_global_mode_is_whitelist(self):
        pl_config = {
            'GLOBAL_MODE': 'whitelist',
            'GLOBAL_WHITELIST': [ 'adder_id' ],
            'GLOBAL_BLACKLIST': [ 'adder_id' ]
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertTrue(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))

        pl_config = {
            'GLOBAL_MODE': 'whitelist',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': []
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    def test_playlist_addition_is_authorized_returns_false_if_adder_not_locally_authorized_and_global_mode_is_unknown(self):
        pl_config = {
            'GLOBAL_MODE': 'not a valid mode',
            'GLOBAL_WHITELIST': [],
            'GLOBAL_BLACKLIST': []
        }
        cleaner = PlaylistCleaner(self.test_logger, Mock(), 'owner_id', pl_config)
        cleaner._local_authorization = Mock(return_value='neutral')
        self.assertFalse(cleaner.playlist_addition_is_authorized('adder_id', self.generate_spotify_id()))


    # ----- Tests for PlaylistCleaner.remove_playlist_items ---- #

    def test_remove_playlist_items_processes_removes_items_in_blocks_of_100_items(self):
        mock_api = spotipy.client.Spotify()
        mock_api.playlist = Mock(return_value={ 'name': 'Playlist Name' })
        mock_api.playlist_remove_specific_occurrences_of_items = Mock()
        pl_id = self.generate_spotify_id()
        cleaner = PlaylistCleaner(self.test_logger, mock_api, 'owner_id', {})
        item_ids = [ self.generate_spotify_id() for i in range(0, 230) ]
        items = [
            {
                'uri': 'spotify:track:' + item_ids[index],
                'name': item_ids[index],
                'added_by': 'adder',
                'added_at': 'date added',
                'position': index

            } for index in range(0, len(item_ids))
        ]
        expected_removed = [
            {
                'uri': item['uri'],
                'positions': [ item['position'] ]
            } for item in items
        ]
        cleaner.remove_playlist_items(pl_id, items)

        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_count, 3)

        self.assertEqual(len(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[0][0]), 2)
        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[0][0][0], pl_id)
        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[0][0][1], expected_removed[0:100])

        self.assertEqual(len(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[1][0]), 2)
        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[1][0][0], pl_id)
        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[1][0][1], expected_removed[100:200])

        self.assertEqual(len(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[2][0]), 2)
        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[2][0][0], pl_id)
        self.assertEqual(mock_api.playlist_remove_specific_occurrences_of_items.call_args_list[2][0][1], expected_removed[200:230])


    # ----- Tests for PlaylistCleaner._get_playlist_config ----- #
    
    def test_get_playlist_config_returns_none_if_playlist_has_no_config(self):
        config = { 'PROTECTED_PLAYLISTS': [ { 'myplaylist': { 'uri': self.generate_playlist_uri() } } ] }
        cleaner = PlaylistCleaner(self.test_logger, self.test_api, 'owner_id', config)
        different_playlist = self.generate_spotify_id()
        self.assertIsNone(cleaner._get_playlist_config(different_playlist))


    def test_get_playlist_config_returns_none_if_playlist_has_two_labels(self):
        config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist':{
                        'uri': self.generate_playlist_uri()
                    },
                    'somehowthesameplaylist': {}
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, self.test_api, 'owner_id', config)
        different_playlist = self.generate_spotify_id()
        self.assertIsNone(cleaner._get_playlist_config(different_playlist))


    def test_get_playlist_config_returns_config_of_playlist_with_matching_url(self):
        pl_id = self.generate_spotify_id()
        other_pl_uri = self.generate_playlist_uri()
        config = {
            'PROTECTED_PLAYLISTS': [
                {
                    'myplaylist1': {
                        'uri': other_pl_uri,
                        'other_config': '...'
                    }
                },
                {
                    'myplaylist2': {
                        'uri': 'spotify:playlist:' + pl_id,
                        'other_config': 'other relevant config data'
                    }
                }
            ]
        }
        cleaner = PlaylistCleaner(self.test_logger, self.test_api, 'owner_id', config)
        self.assertEqual(cleaner._get_playlist_config(pl_id), config['PROTECTED_PLAYLISTS'][1]['myplaylist2'])



if __name__ == '__main__':
    unittest.main()

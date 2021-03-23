import unittest
import logging
import os
import random
import string
from unittest.mock import Mock, patch
import spotipy
from src.spotify_helper import SpotifyHelper

class TestSpotifyHelper(unittest.TestCase):

    def setUp(self):
        self.test_logger = logging.getLogger('TestSpotifyHelper')
        log_handler = logging.StreamHandler()
        log_handler.setLevel('CRITICAL')
        self.test_logger.addHandler(log_handler)

        self.helper = SpotifyHelper(self.test_logger)

        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())

        os.environ = {} # reset environment


    # ----- Tests for SpotifyHelper.configure_api ----- #

    @patch('src.spotify_helper.spotipy.Spotify')
    @patch('src.spotify_helper.SpotifyOAuth')
    def test_configure_api_authenticates_with_all_required_scopes(self, oauth_mock, spotify_mock):
        oauth_mock.return_value  = Mock()
        spotify_mock.return_value = None

        required_scopes = [
            'playlist-read-private',
            'playlist-read-collaborative',
            'playlist-modify-public',
            'playlist-modify-private'
        ]
        self.helper.configure_api('test_client_id', 'test_client_secret', 'test_redirect')

        # Ensure Spotify (client) has been configured with the correct auth manager
        oauth_mock.assert_called_once()
        spotify_mock.asset_called_once_with(auth_manager=oauth_mock.return_value)

        # Ensure the used auth manager received all of the required scopes
        self.assertTrue(isinstance(oauth_mock.call_args[1], dict) and 'scope' in oauth_mock.call_args[1].keys(),
                        "SpotifyOAuth did not receive any list/string of scopes.")
        requested_scopes = oauth_mock.call_args[1]['scope']
        for scope in required_scopes:
            # Scopes must be delimiteed by a space which can be either prefixed or suffixed
            self.assertTrue(scope + ' ' in requested_scopes or ' ' + scope in requested_scopes)


    @patch.dict(os.environ, {})
    def test_configure_api_passes_client_auth_details_via_environment_variables(self):
        auth_keys = ('SPOTIPY_CLIENT_ID', 'SPOTIPY_CLIENT_SECRET', 'SPOTIPY_REDIRECT_URI')
        for key in auth_keys:
            self.assertTrue(key not in os.environ)

        auth_values = ('test_client_id', 'test_client_secret', 'test_redirect_uri')
        self.helper.configure_api(auth_values[0], auth_values[1], auth_values[2])
        for index in range(0, len(auth_keys)):
           self.assertEqual(os.environ[auth_keys[index]], auth_values[index])


    @patch('src.spotify_helper.spotipy.Spotify')
    @patch('src.spotify_helper.SpotifyOAuth')
    def test_configure_api_returns_none_if_spotipy_raises_exception(self, oauth_mock, spotify_mock):
        spotify_mock.side_effect = Exception('TestException')
        api = self.helper.configure_api('test_client_id', 'test_client_secret', 'test_redirect')
        self.assertIsNone(api)


    @patch('src.spotify_helper.spotipy.Spotify')
    @patch('src.spotify_helper.SpotifyOAuth')
    def test_configure_api_returns_client_object_if_spotipy_returns_the_correct_type(self, oauth_mock, spotify_mock):
        spotify_mock.return_value = spotipy.client.Spotify()
        api = self.helper.configure_api('test_client_id', 'test_client_secret', 'test_redirect')
        self.assertEqual(api, spotify_mock.return_value)


    # Tests for SpotifyHelper.get_all_collab_playlists ----- #

    def test_get_all_collab_playlists_returns_none_if_no_api_clients_are_given_or_configured(self):
        self.helper.api = None
        self.assertEqual(self.helper.get_all_collab_playlists(api=None), None)


    def test_get_all_collab_playlists_uses_api_client_received_as_argument_instead_of_preconfigured_client(self):
        stubbed_response = { 'items': [], 'total': 0 }
        preconfigured_api = spotipy.client.Spotify()
        preconfigured_api.current_user_playlists = Mock(return_value=stubbed_response)
        given_api = spotipy.client.Spotify()
        given_api.current_user_playlists = Mock(return_value=stubbed_response)

        self.helper.api = preconfigured_api
        self.helper.get_all_collab_playlists(api=given_api)
        preconfigured_api.current_user_playlists.assert_not_called()
        given_api.current_user_playlists.assert_called()


    def test_get_all_collab_playlists_uses_preconfigured_api_client_if_no_client_is_given_as_an_argument(self):
        preconfigured_api = spotipy.client.Spotify()
        preconfigured_api.current_user_playlists = Mock(return_value={ 'items': [], 'total': 0 })
        self.helper.api = preconfigured_api
        self.helper.get_all_collab_playlists(api=None)
        preconfigured_api.current_user_playlists.assert_called()

    def test_get_all_collab_playlists_returns_only_collaborative_playlists_and_in_correct_format(self):
        response = {
            'items': [
                {
                    'uri': self.generate_track_uri(),
                    'collaborative': False
                } for i in range(0, 130)
            ],
            'total': 132
        }
        for item in range(130, 132):
            response['items'].append({
                'uri': self.generate_track_uri(),
                'collaborative': True
            })
   
        mock_api = spotipy.client.Spotify()
        mock_api.current_user_playlists = Mock()
        mock_api.current_user_playlists.side_effect = [
            {
                'items': response['items'][0:50],
                'total': 130
            },
            {
                'items': response['items'][50:100],
                'total': 130
            },
            {
                'items': response['items'][100:],
                'total': 130
            }
        ]
        expected_result = [ { 'uri': item['uri'] } for item in response['items'][130:] ]
        result = self.helper.get_all_collab_playlists(api=mock_api)
        self.assertEqual(result, expected_result)


    def test_get_all_collab_playlists_fetches_playlists_in_blocks_of_50_playlists(self):
        response = {
            'items': [ { 'uri': 'playlist_uri%d' % item, 'collaborative': False } for item in range(0, 130) ],
            'total': 130
        }
        mock_api = spotipy.client.Spotify()
        mock_api.current_user_playlists = Mock()
        mock_api.current_user_playlists.side_effect = [
            {
                'items': response['items'][0:50],
                'total': 130
            },
            {
                'items': response['items'][50:100],
                'total': 130
            },
            {
                'items': response['items'][100:],
                'total': 130
            }
        ]
        self.helper.get_all_collab_playlists(api=mock_api)
        self.assertEqual(mock_api.current_user_playlists.call_count, 3)

        self.assertEqual(mock_api.current_user_playlists.call_args_list[0][1]['limit'], 50)
        self.assertEqual(mock_api.current_user_playlists.call_args_list[0][1]['offset'], 0)

        self.assertEqual(mock_api.current_user_playlists.call_args_list[1][1]['limit'], 50)
        self.assertEqual(mock_api.current_user_playlists.call_args_list[1][1]['offset'], 50)

        self.assertEqual(mock_api.current_user_playlists.call_args_list[2][1]['limit'], 50)
        self.assertEqual(mock_api.current_user_playlists.call_args_list[2][1]['offset'], 100)



    # ----- Tests for SpotifyHelper.add_items_to_playlist ----- \

    def test_add_items_to_playlist_uses_api_client_received_as_argument_instead_of_preconfigured_client(self):
        self.helper.api = spotipy.client.Spotify()
        self.helper.api.playlist_add_items = Mock()
        received_api = spotipy.client.Spotify()
        received_api.playlist_add_items = Mock()
        self.helper.add_items_to_playlist(self.generate_spotify_id(), [
            { 'uri': self.generate_track_uri() } for i in range (0, 2)
        ], api=received_api)
        received_api.playlist_add_items.assert_called_once()
        self.helper.api.playlist_add_items.assert_not_called()


    def test_add_items_to_playlist_uses_preconfigure_api_client_one_is_available_and_no_api_is_given(self):
        self.helper.api = spotipy.client.Spotify()
        self.helper.api.playlist_add_items = Mock()
        self.helper.add_items_to_playlist(self.generate_spotify_id(), [
            { 'uri': self.generate_track_uri() } for i in range (0, 2)
        ])
        self.helper.api.playlist_add_items.assert_called_once()


    def test_add_items_to_playlist_does_not_attempt_to_add_items_if_no_preconfigured_or_provided_api_is_available(self):
        # the API mock should be ignored because it is not of the correct type but if execution
        # unexpectedly continued then its playlist_add_items method would be called.
        # Therefore this mock and its method can be used to test that execution stops before
        # an attempt is made to add the items to the playlist
        self.helper.api = Mock()
        self.helper.add_items_to_playlist(self.generate_spotify_id(), [
            { 'uri': self.generate_track_uri() } for i in range (0, 2)
        ])
        self.helper.api.playlist_add_items.assert_not_called()


    def test_add_items_to_playlist_add_items_in_blocks_of_100(self):
        mock_api = spotipy.client.Spotify()
        mock_api.playlist_add_items = Mock()
        pl_id = self.generate_spotify_id()
        items = [ { 'uri': self.generate_track_uri() } for i in range(0, 230) ]
        item_uris = [ item['uri'] for item in items ]
        self.helper.add_items_to_playlist(pl_id, items, api=mock_api)

        self.assertEqual(mock_api.playlist_add_items.call_count, 3)
        self.assertEqual(len(mock_api.playlist_add_items.call_args_list[0][0]), 2)
        self.assertEqual(mock_api.playlist_add_items.call_args_list[0][0][0], pl_id)
        self.assertEqual(mock_api.playlist_add_items.call_args_list[0][0][1], item_uris[0:100])

        self.assertEqual(len(mock_api.playlist_add_items.call_args_list[1][0]), 2)
        self.assertEqual(mock_api.playlist_add_items.call_args_list[1][0][0], pl_id)
        self.assertEqual(mock_api.playlist_add_items.call_args_list[1][0][1], item_uris[100:200])

        self.assertEqual(len(mock_api.playlist_add_items.call_args_list[2][0]), 2)
        self.assertEqual(mock_api.playlist_add_items.call_args_list[2][0][0], pl_id)
        self.assertEqual(mock_api.playlist_add_items.call_args_list[2][0][1], item_uris[200:])


    # ----- Tests for SpotifyHelper.get_track_id ----- #

    def test_get_track_id_returns_correct_id_when_input_is_uri(self):
        track_id = self.generate_spotify_id()
        track_uri = 'spotify:track:' + track_id
        self.assertEqual(self.helper.get_track_id(track_uri), track_id)


    def test_get_track_id_returns_correct_id_when_input_is_dict_with_uri(self):
        track_id = self.generate_spotify_id()
        track_uri = 'spotify:track:' + track_id
        self.assertEqual(self.helper.get_track_id({ 'uri': track_uri }), track_id)


    def test_get_track_id_returns_none_if_input_is_string_with_no_uri(self):
        self.assertIsNone(self.helper.get_track_id('somestringwithnouri'))


    def test_get_track_id_returns_none_if_input_is_dict_with_no_uri_field(self):
        self.assertIsNone(self.helper.get_track_id({ 'otherfield': self.generate_spotify_id() }))


    # ----- Tests for SpotifyHelper.get_playlist_id ----- #

    def test_get_playlist_id_returns_correct_id_when_input_is_uri(self):
        pl_id = self.generate_spotify_id()
        pl_uri = 'spotify:playlist:' + pl_id
        self.assertEqual(self.helper.get_playlist_id(pl_uri), pl_id)


    def test_get_playlist_id_returns_correct_id_when_input_is_dict_with_uri(self):
        pl_id = self.generate_spotify_id()
        pl_uri = 'spotify:playlist:' + pl_id
        self.assertEqual(self.helper.get_playlist_id({ 'uri': pl_uri }), pl_id)


    def test_get_playlist_id_returns_none_if_input_is_string_with_no_uri(self):
        self.assertIsNone(self.helper.get_playlist_id('somestringwithnouri'))


    def test_get_playlist_id_returns_none_if_input_is_dict_with_no_uri_field(self):
        self.assertIsNone(self.helper.get_track_id({ 'otherfield': self.generate_spotify_id() }))


    # ----- Tests for SpotifyHelper.get_all_items_in_playlist ----- #

    def test_get_all_items_in_playlist_uses_api_client_received_as_argument_instead_of_preconfigured_client(self):
        self.helper.api = spotipy.client.Spotify()
        self.helper.api.playlist_items = Mock(return_value={ 'items': [] })
        received_api = spotipy.client.Spotify()
        received_api.playlist_items = Mock(return_value={ 'items': [] })
        self.helper.get_all_items_in_playlist(self.generate_spotify_id(), fields=None, api=received_api)
        received_api.playlist_items.assert_called_once()
        self.helper.api.playlist_items.assert_not_called()


    def test_get_all_items_in_playlist_uses_preconfigure_api_client_one_is_available_and_no_api_is_given(self):
        self.helper.api = spotipy.client.Spotify()
        self.helper.api.playlist_items = Mock(return_value={ 'items': [] })
        self.helper.get_all_items_in_playlist(self.generate_spotify_id(), fields=None)
        self.helper.api.playlist_items.assert_called_once()


    def test_get_all_items_playlist_returns_none_if_there_is_no_preconfigured_or_received_api_available(self):
        self.helper.api = None
        self.assertIsNone(self.helper.get_all_items_in_playlist(self.generate_spotify_id(), fields=None))


    def test_get_all_items_in_playlist_returns_all_constituent_items(self):
        items = [
            {
                'track': {
                    'uri': self.generate_track_uri(),
                    'name': 'track_name'
                },
                'added_at': 'added_at_timestamp',
                'added_by': { 'id': self.generate_spotify_id() },
                'position': index
            } for index in range(0, 230)
        ]
        mock_api = spotipy.client.Spotify()
        mock_api.playlist_items = Mock(side_effect=[
            {
                'items': items[0:100]
            },
            {
                'items': items[100:200]
            },
            {
                'items': items[200:]
            }
        ])
        result = self.helper.get_all_items_in_playlist(
            self.generate_spotify_id(), api=mock_api, fields='items(added_at,added_by,track(uri.name))')
        self.assertEqual(result, items)


if __name__ == '__main__':
    unittest.main()

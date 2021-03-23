import re
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

class SpotifyHelper:

    def __init__(self, logger, api=None):
        self.api = api
        self.logger = logger.getChild('SpotifyHelper')


    def configure_api(self, client_id, client_secret, redirect):
        os.environ['SPOTIPY_CLIENT_ID'] = client_id
        os.environ['SPOTIPY_CLIENT_SECRET'] = client_secret
        os.environ['SPOTIPY_REDIRECT_URI'] = redirect
        scope = 'playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private'

        self.logger.debug('Attempting to authenticate with Spotify. Requested scope: \'%s\'', scope)
        api_client = None
        try:
            api_client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        except Exception as err:
            self.logger.error('Failed to authenticate with Spotify. Error: \'%s\'', err)
            return None

        if isinstance(api_client, spotipy.client.Spotify):
            self.api = api_client
            return self.api

        self.logger.error('Failed to authenticate with Spotify.')
        return None


    def get_all_collab_playlists(self, creator_id, api=None):
        if not isinstance(api, spotipy.client.Spotify):
            api = self.api
        if not isinstance(api, spotipy.client.Spotify):
            self.logger.error('Cannot get all collaborative playlists: no API is available')
            return None

        item_limit = 50
        last_checked = 0
        more_to_process = True
        collaborative_playlists = []

        while more_to_process:
            response = api.current_user_playlists(limit=item_limit, offset=last_checked)
            for playlist in response['items']:
                if playlist['collaborative'] and playlist['owner']['id'] == creator_id:
                    collaborative_playlists.append({ 'uri': playlist['uri'] })

            more_to_process = len(response['items']) == item_limit
            last_checked += item_limit
        return collaborative_playlists


    def get_all_items_in_playlist(self, playlist_id, fields=None, api=None):
        if not isinstance(api, spotipy.client.Spotify):
            api = self.api
        if not isinstance(api, spotipy.client.Spotify):
            self.logger.error('Cannot get all items in a playlist: no API is available')
            return None

        item_limit = 100
        offset = 0
        more_to_process = True
        items = []

        while more_to_process:
            response = api.playlist_items(playlist_id, limit=item_limit, offset=offset, fields=fields)
            for index in range(0, len(response['items'])):
                item = response['items'][index]
                item['position'] = offset + index
                items.append(item)
            more_to_process = len(response['items']) == item_limit
            offset += item_limit

        return items


    def add_items_to_playlist(self, playlist_id, items, api=None):
        if not isinstance(api, spotipy.client.Spotify):
            api = self.api
        if not isinstance(api, spotipy.client.Spotify):
            self.logger.error('Cannot add items to playlist: no API is available')
            return

        item_uris = [ item['uri'] for item in items ]
        max_additions = 100
        lbound = 0
        while lbound < len(item_uris):
            ubound = lbound + max_additions if lbound + max_additions <= len(item_uris) else len(item_uris)
            api.playlist_add_items(playlist_id, item_uris[lbound:ubound])
            lbound = ubound


    @staticmethod
    def get_playlist_id(playlist):
        if (isinstance(playlist, str)
            and re.search('^spotify:playlist:[A-Za-z0-9]{22}$', playlist) is not None):
            return playlist[17:]
        elif isinstance(playlist, dict) and 'uri' in playlist.keys():
            return playlist['uri'][17:]
        return None


    @staticmethod
    def get_track_id(track):
        if (isinstance(track, str)
            and re.search('^spotify:track:[A-Za-z0-9]{22}$', track) is not None):
            return track[14:]
        elif isinstance(track, dict) and 'uri' in track.keys():
            return track['uri'][14:]
        return None

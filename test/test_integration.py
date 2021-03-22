import unittest
from unittest.mock import Mock, patch
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
        self.generate_spotify_id = (
            lambda: ''.join(random.choice(string.ascii_letters + string.digits) for i in range(0, 22)))
        self.generate_playlist_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:playlist:' + gen_id())
        self.generate_track_uri = (
            lambda gen_id=self.generate_spotify_id: 'spotify:track:' + gen_id())


    def test_program_run_with_help_function(self):
        pass



if __name__ == '__main__':
    unittest.main()

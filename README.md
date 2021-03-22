# SpotifyAutoModerator
![Code Coverage Badge](https://raw.githubusercontent.com/omnimeta/SpotifyAutoModerator/main/coverage/badge.svg)

Automated moderator for collaborative playlists on Spotify.

## The Problem

Spotify's collaborative playlists can be an awesome tool for constructing and sharing unique mixes of music with friends (and more).
However, there are two crucial issues with Spotify's collaborative playlist system that can be a great annoyance for those use the feature frequently

* any user can add any track to a public collaborative playlist; and
* any user can remove any track from a public collaborative playlist.

Imagine spending years constructing and managing the perfect <insert your overly specific sub-genre of preference> with your close friends. Now imagine a random Spotify artist to use their burner account to empty your playlist and replace it with their own (extremely underwhelming) music of a completely unrelated sub-genre. A lot of Spotify users don't need to imagine this at all, as it happens regularly. Record label accounts on Spotify have also been seen promoting their artists' music by adding it to irrelevant collaborative playlists. Additionally, general trolls exist on every online platform and Spotify is certainly no exception.

It is obvious that collaborative playlists require protection against such annoyances.

## The Solution

SpotifyAutoModerator monitors all (or a chosen subset of) your collaborative playlists and provides the following services in an attempt to mitigate the aforementioned problem:

* **enforcement of a whitelist of authorized users** - automatic removal of any track additions by users which are not explicitly authorized;
* **enforcement of a blacklist of unauthorized users** - automatic removal of any track additions by users which are explicitly banned from contributing to a particular playlist (or all playlists); and
* **track restoration after unapproved removal** - SpotifyAutoModerator will automatically ask you to approve the removals of tracks from your protected playlists and will restore any tracks that were removed without your approval.

## Installation

### Download the Project Source

To install SpotifyAutoModerator, run the following commands:

``` shell
$> git clone https://github.com/omnimeta/SpotifyAutoModerator.git
$> cd SpotifyAutoModerator
$> ./setup.sh
```

## Register the Application on Your Spotify Dashboard

Register the application at: https://developer.spotify.com/dashboard/login
<div style="text-align:center"><img src="data/images/register_app.png" /></div>

Once the application is registered, note the generated client ID and client secret, then click the `EDIT SETTINGS` button and add `http://localhost:8080` as a redirect URI to the application (in the Spotify dashboard). If the port `8080` is in use by some service (e.g., a local web server) on your system then replace `8080` with an unused port number.
<div style="text-align:center"><img src="data/images/add_redirect_uri.png" /></div>


## Project Roadmap

The following are the current goals of the project:
* addition of a set of integration tests;
* configuration and usage documentation;
* vulnerability scanning of sourced libraries/packages;
* provision of a Dockerfile.

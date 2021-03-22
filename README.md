# SpotifyAutoModerator

[Code Coverage Badge](https://raw.githubusercontent.com/omnimeta/SpotifyAutoModerator/main/coverage/badge.svg)

## The Problem

Spotify's collaborative playlists can be an awesome tool for constructing and sharing unique mixes of music with friends (and more).
However, there are two crucial issues with Spotify's collaborative playlist system that can be a great annoyance for those use the feature frequently

* any user can add any track to a public collaborative playlist; and
* any user can remove any track from a public collaborative playlist.

Imagine spending years constructing and managing the perfect <insert your overly specific sub-genre of preference> with your close friends. Now imagine a random Spotify artist to use their burner account to empty your playlist and replace it with their own (extremely underwhelming) music of a completely unrelated sub-genre. A lot of Spotify users don't need to imagine this at all, as it happens regularly. Record label accounts on Spotify have also been seen promoting their artists' music by adding it to irrelevant collaborative playlists. Additionally, general trolls exist on every online platform and Spotify is certainly no exception.
It is obvious that collaborative playlists required protection against such annoyances.

## The Solution

SpotifyAutoModerator monitors all (or a chosen subset of) your collaborative playlists and provides the following services in an attempt to mitigate the aforementioned problem:

* **enforcement of a whitelist of authorized users** - automatic removal of any track additions by users which are not explicitly authorized;
* **enforcement of a blacklist* of unauthorized users** - automatic removal of any track additions by users which are explicitly banned from contributing to a particular playlist (or all playlists); and
* **track restoration after unapproved removal** - SpotifyAutoModerator will automatically ask you to approve the removals of tracks from your protected playlists and will restore any tracks that were removed without your approval.

## Project Roadmap

The following are the current goals of the project:
* addition of a set of integration tests;
* installation, configuration, and usage documentation;
* vulnerability scanning of sourced libraries/packages;
* provision of a Dockerfile.

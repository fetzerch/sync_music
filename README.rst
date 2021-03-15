.. image:: https://travis-ci.com/fetzerch/sync_music.svg?branch=master
    :target: https://travis-ci.com/fetzerch/sync_music
    :alt: Travis CI Status

.. image:: https://coveralls.io/repos/github/fetzerch/sync_music/badge.svg?branch=master
    :target: https://coveralls.io/github/fetzerch/sync_music?branch=master
    :alt: Coveralls Status

.. image:: https://img.shields.io/pypi/v/sync_music.svg
    :target: https://pypi.org/project/sync_music
    :alt: PyPI Version

sync_music - Sync music library to external devices
===================================================

This program allows you to synchronize your music library for the usage
on primitive music players that don't support the diversity of your
collection.

In normal operation mode, *sync_music* performs its synchronization tasks
depending on the input file format. Music files in FLAC and Ogg Vorbis
format are transcoded to MP3. MP3 audio files and other files are
transferred unchanged. Filenames are adapted where necessary to comply
with the FAT32 format. If preferred, *sync_music* can also forcefully
transcode all files in order to save disk space. Another operation mode
applies volume normalization based on ReplayGain_ tags.

Transcoding is a time consuming operation, therefore the first run of
*sync_music* can take several minutes. In subsequent runs however, it will
only process files that changed in the source. To optimize the detection of
file changes, the script stores and compares a hash build on a fixed size
block at the beginning of each file.

Besides audio files, *sync_music* is also able to export M3U playlists to
the destination folder. Absolute paths are hereby replaced with relative
paths in addition to the FAT32 filename adaptations.

Dependencies
------------

- Python 3.5
- `Python Audio Tools`_ >= 3.0 (for transcoding to MP3)
- Mutagen_ >= 1.29 (for tag manipulation)

Installation
------------

The first step is to install `Python Audio Tools`_ which depends on a couple of
native libraries and doesn't offer a PyPI package. On Ubuntu 16.04 or later
there's an official package that can simply be installed using::

    # apt install audiotools

As an alternative `Python Audio Tools`_ can be installed from source after the
necessary native libraries are installed::

    # apt install python3-dev lame libmp3lame-dev libmpg123-dev libvorbis-dev
    # pip3 install https://github.com/tuffy/python-audio-tools/archive/master.zip

Then *sync_music* can be installed from PyPI with::

    # pip3 install sync_music

The following command installs the current development version::

    # pip3 install https://github.com/fetzerch/sync_music/archive/master.zip

Usage
-----

Quick start
^^^^^^^^^^^

The following basic command synchronizes all audio files from the source to the
destination directory::

    sync_music --audio-src=<FOLDER> --audio-dest=<FOLDER>

Additionally M3U playlist syncing can be enabled by specifying the path to the
playlists::

    sync_music --audio-src=<FOLDER> --audio-dest=<FOLDER> --playlist-src=<FOLDER>

Besides that *sync_music* supports a number of advanced options. A full list of
supported options is available in the built in help message::

    sync_music --help

Transcoding
^^^^^^^^^^^

The operation mode can be changed with the `--mode` parameter.

In *transcode* mode MP3 files are transcoded as well (instead of just copied to
the destination)::

    sync_music --audio-src=<FOLDER> --audio-dest=<FOLDER> --mode=transcode

Transcoding MP3 files can lead to significantly smaller files if the source
contains many 320kbps CBR MP3s as the target rate is 190kbps VBR. The drawback
is that transcoding is slower and needs more CPU power.

The *replaygain* and *replaygain-album* modes apply (track or album) based
volume normalization from ReplayGain_ tags when transcoding::

    sync_music --audio-src=<FOLDER> --audio-dest=<FOLDER> --mode=replaygain

Transcoding modes require that the MP3 files can be decoded by `Python
Audio Tools`_ without issues. Problematic input files can be analyzed and fixed
for example with `MP3 Diags`_.

Hacks
^^^^^

Some media players don't properly support album artist tags. This restriction
can be bypassed by writing the album artist information into the artist field.
This can be enabled by adding the `--albumartist-artist-hack` parameter.

Some media players don't properly support album artist tags, but they do
support the composer field. This restriction can be bypassed by writing
the album artist information into the composer field. This can be
enabled by adding the `--albumartist-composer-hack` parameter.

Some media players don't properly support disc number tags with tracks numbered
starting with 1 for every disc. The user typically wants to group them by disc
and not by track position. This can be solved by creating a different album for
each disc. With the `--discnumber-hack` option, the disc number is appended
to the album field.

Some media players don't properly support track number tags containing the
total number of tracks on the disk. With the `--tracknumber-hack` option, the
track total is removed from the track number field.

License
-------

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
`GNU General Public License <http://www.gnu.org/licenses/gpl-2.0.html>`_
for more details.

.. _`Python Audio Tools`: http://audiotools.sourceforge.net
.. _`MP3 Diags`: http://mp3diags.sourceforge.net
.. _Mutagen: https://mutagen.readthedocs.io
.. _ReplayGain: https://en.wikipedia.org/wiki/ReplayGain

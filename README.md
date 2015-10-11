sync_music - Sync music library to external devices
===================================================

This program allows you to synchronize your music library for the usage
on primitive music players that don't support the diversity of your
collection.

In normal operation mode, sync_music performs its synchronization tasks
depending on the input file format. Music files in FLAC and Ogg Vorbis
format are transcoded to MP3. MP3 audio files and other files are
transferred unchanged. Filenames are adapted where necessary to comply
with the FAT32 format.

Transcoding is a time consuming operation, therefore the first run of
sync_music can take several minutes. In subsequent runs however, it will
only process files that changed in the source. To optimize the detection of
file changes, the script stores and compares a hash build on a fixed size
block at the beginning of each file.

Besides audio files, sync_music is also able to export M3U playlists to
the destination folder. Absolute paths are hereby replaced with relative
paths in addition to the FAT32 filename adaptations.

Dependencies
------------

- Python 3.4
- Python Audio Tools >= 3.0 (for transcoding to MP3)
- Mutagen >= 1.29 (for tag manipulation)

Installation
------------

    pip3 install --process-dependency-links sync_music.zip

Usage
-----

    sync_music --audio-src=<FOLDER> --audio-dest=<FOLDER>

M3U Playlist syncing can be enabled by specifying the path to the
playlist with the `--playlist-src=<FOLDER>` parameter.

Some media players don't properly support album artist tags, but they do
support the composer field. This restriction can be bypassed by writing
the album artist information into the composer field. This can be
enabled by the `--albumartist-hack`

Some media players don't properly support disc number tags with tracks numbered
starting with 1 for every disc. The user typically wants to group them by disc
and not by track position. This can be solved by creating a different album for
each disc. With the `--discnumber-hack` option, the disc number is appended
to the album field.

Some media players don't properly support track number tags containing the
total number of tracks on the disk. With the `--tracknumber-hack` option, the
track total is removed from the track number field.

Call sync_music with `--help` to get a full list of supported command
line parameters.

License
-------

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
[GNU General Public License](http://www.gnu.org/licenses/gpl-2.0.html)
for more details.

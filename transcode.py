# sync_music - Sync music library to external device
# Copyright (C) 2013 Christian Fetzer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

""" Transcode action """

import os
import shutil
import util

import audiotools

# Mutagen 1.22 supports id3v2.3
if util.module_exists('mutagen', '1.22', 'version_string'):
    import mutagen


class Transcode(object):
    """ Transcodes audio files """

    def __init__(self, transcode=True, copy_tags=True, composer_hack=False):
        self.name = "Processing"
        self._format = audiotools.MP3Audio
        self._compression = audiotools.MP3Audio.COMPRESSION_MODES[2]

        print("Transcoding settings:")
        print(" - Audiotools " + audiotools.VERSION)
        print(" - Mutagen " + mutagen.version_string)
        self._transcode = transcode
        if transcode:
            print(" - Converting to %s in quality %s "
                  "(LAME quality parameter; 0 best, 9 fastest)" %
                  (self._format.NAME, self._compression))
        else:
            print(" - Skipping transcoding")

        self._copy_tags = copy_tags
        if copy_tags:
            print(" - Copying tags")
        else:
            print(" - Skipping copying tags")

        self._composer_hack = composer_hack
        if composer_hack:
            print(" - Writing albumartist into composer field")
        print("")

    def get_out_filename(self, path):
        """ Determine output file path """
        return os.path.splitext(path)[0] + '.' + self._format.SUFFIX

    def execute(self, in_filepath, out_filepath):
        """ Executes action """
        if self._transcode:
            if os.path.splitext(in_filepath)[1] != '.' + self._format.SUFFIX:
                self.transcode(in_filepath, out_filepath)
            else:
                self.copy(in_filepath, out_filepath)
        if self._copy_tags:
            if os.path.splitext(in_filepath)[1] in ['.flac', '.ogg']:
                self.copy_vorbiscomments_to_mp3(in_filepath, out_filepath)
            elif os.path.splitext(in_filepath)[1] == '.mp3':
                self.copy_id3_to_mp3(in_filepath, out_filepath)

    @classmethod
    def copy(cls, in_filepath, out_filepath):
        """ Copying audio file """
        print("Copying from %s to %s" % (in_filepath.decode('utf-8'),
                                         out_filepath.decode('utf-8')))
        shutil.copy(in_filepath, out_filepath)

    def transcode(self, in_filepath, out_filepath):
        """ Transcode audio file """
        print("Transcoding from %s to %s" % (in_filepath.decode('utf-8'),
                                             out_filepath.decode('utf-8')))
        try:
            audiotools.open(in_filepath).convert(out_filepath, self._format,
                                                 compression=self._compression)
        except audiotools.EncodingError as err:
            raise IOError("Error: Failed to transcode: %s" % err)

    def copy_vorbiscomments_to_mp3(self, in_filename, mp3_filename):
        """ Copy vorbis comments to ID3 tags in MP3 files """
        print("Copying metadata from %s to %s" % (in_filename.decode('utf-8'),
                                                  mp3_filename.decode(
                                                      'utf-8')))
        in_file = mutagen.File(in_filename)
        mp3_file = mutagen.mp3.MP3(mp3_filename)
        if not mp3_file.tags:
            mp3_file.tags = mutagen.id3.ID3()

        # Copy tags
        tagtable = {
            'album': mutagen.id3.TALB,
            'artist': mutagen.id3.TPE1,
            'albumartist': mutagen.id3.TPE2,
            'title': mutagen.id3.TIT2,
            'genre': mutagen.id3.TCON,
            'date': mutagen.id3.TDRC,
            'tracknumber': mutagen.id3.TRCK,
            'discnumber': mutagen.id3.TPOS,
        }
        for tag in tagtable.keys():
            if tag in in_file.tags:
                id3tag = tagtable[tag]
                if tag == 'tracknumber':
                    track = in_file.tags['tracknumber'][0]
                    if 'tracktotal' in in_file.tags:
                        track = "%s/%s" % (track,
                                           in_file.tags['tracktotal'][0])
                    mp3_file.tags.add(id3tag(encoding=3, text="%s" % track))
                else:  # All other tags
                    mp3_file.tags.add(id3tag(encoding=3,
                                      text=in_file.tags[tag]))

                if self._composer_hack and tag == 'albumartist':
                    mp3_file.tags.add(mutagen.id3.TCOM(encoding=3,
                                      text=in_file.tags['albumartist']))

        # Copy cover art
        try:
            for picture in in_file.pictures:
                mp3_file.tags.add(mutagen.id3.APIC(encoding=3,
                                                   desc=picture.desc,
                                                   data=picture.data,
                                                   type=picture.type,
                                                   mime=picture.mime))
        except AttributeError:
            # Ogg files have their image in METADATA_BLOCK_PICTURE
            image = os.path.join(os.path.dirname(in_filename), 'folder.jpg')
            if os.path.exists(image):
                image_file = open(image, 'rb')
                img = image_file.read()
                image_file.close()
                mp3_file.tags.add(mutagen.id3.APIC(3, 'image/jpg', 3, '', img))

        # Save as id3v1 and id3v2.3
        mp3_file.tags.update_to_v23()
        mp3_file.tags.save(mp3_filename, v1=2, v2_version=3)

    def copy_id3_to_mp3(self, in_filename, mp3_filename):
        """ Copy ID3 tags to ID3 tags in MP3 files """
        print("Copying ID3 from %s to %s" % (in_filename.decode('utf-8'),
                                             mp3_filename.decode('utf-8')))
        try:
            in_file = mutagen.File(in_filename)
        except mutagen.mp3.HeaderNotFoundError as err:
            raise IOError("Failed to read tags from input file %s" % err)

        if not in_file.tags:
            in_file.tags = mutagen.id3.ID3()

        mp3_file = mutagen.mp3.MP3(mp3_filename)
        mp3_file.tags = mutagen.id3.ID3()

        # Copy tags
        taglist = [
            'TALB',
            'TPE1',
            'TPE2',
            'TIT2',
            'TCON',
            'TDRC',
            'TRCK',
            'TPOS',
            'APIC:'
        ]
        for tag in taglist:
            if tag in in_file.tags:
                # All other tags
                mp3_file.tags.add(in_file.tags[tag])

                if self._composer_hack and tag == 'TPE2':
                    mp3_file.tags.add(mutagen.id3.TCOM(encoding=3,
                                      text=in_file.tags['TPE2'].text))

        # Save as id3v1 and id3v2.3
        mp3_file.tags.update_to_v23()
        mp3_file.tags.save(mp3_filename, v1=2, v2_version=3)

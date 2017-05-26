# sync_music - Sync music library to external device
# Copyright (C) 2013-2015 Christian Fetzer
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

import base64
import collections
import os
import shutil

import audiotools
import audiotools.replaygain
import mutagen


class Transcode(object):  # pylint: disable=R0902
    """ Transcodes audio files """

    def __init__(self,  # pylint: disable=R0913
                 file_mode='auto', tag_mode='auto',
                 composer_hack=False, discnumber_hack=False,
                 tracknumber_hack=False):
        self.name = "Processing"
        self._format = audiotools.MP3Audio
        self._compression = 'standard'

        print("Transcoding settings:")
        print(" - Audiotools " + audiotools.VERSION)
        print(" - Mutagen " + mutagen.version_string)
        self._file_mode = file_mode
        self._tag_mode = tag_mode
        if file_mode in ['auto', 'transcode', 'replaygain']:
            print(" - Converting to {} in quality {}".format(
                self._format.NAME, self._compression))
        else:
            print(" - Skipping transcoding")

        if tag_mode in ['auto']:
            print(" - Copying tags")
        else:
            print(" - Skipping copying tags")

        self._composer_hack = composer_hack
        if composer_hack:
            print(" - Writing albumartist into composer field")
        self._discnumber_hack = discnumber_hack
        if discnumber_hack:
            print(" - Extending album field by disc number")
        self._tracknumber_hack = tracknumber_hack
        if tracknumber_hack:
            print(" - Remove track total from track number")
        print("")

    def get_out_filename(self, path):
        """ Determine output file path """
        return os.path.splitext(path)[0] + '.' + self._format.SUFFIX

    def execute(self, in_filepath, out_filepath):
        """ Executes action """
        if self._file_mode == 'auto':
            if os.path.splitext(in_filepath)[1] != '.' + self._format.SUFFIX:
                self.transcode(in_filepath, out_filepath)
            else:
                self.copy(in_filepath, out_filepath)
        elif self._file_mode in ['transcode', 'replaygain']:
            self.transcode(in_filepath, out_filepath)

        if self._tag_mode == 'auto':
            self.copy_tags(in_filepath, out_filepath)

    @classmethod
    def copy(cls, in_filepath, out_filepath):
        """ Copying audio file """
        print("Copying from {} to {}".format(in_filepath, out_filepath))
        shutil.copy(in_filepath, out_filepath)

    @classmethod
    def get_replaygain(cls, in_filepath):
        """ Read ReplayGain info from tags """
        tags = [
            'replaygain_album_gain',
            'replaygain_album_peak',
            'replaygain_track_gain',
            'replaygain_track_peak'
        ]
        rp_info = collections.namedtuple('ReplayGainInfo', tags)
        in_file = mutagen.File(in_filepath)
        tag_prefix = 'TXXX:' if isinstance(in_file, mutagen.mp3.MP3) else ''
        result = []
        try:
            for tag in tags:
                value = in_file.tags['{}{}'.format(tag_prefix, tag)][0]
                result.append(float(value.replace('dB', '')))
            return rp_info(*result)
        except (TypeError, KeyError):
            return None

    def transcode(self, in_filepath, out_filepath):
        """ Transcode audio file """
        print("Transcoding from {} to {}".format(in_filepath, out_filepath))
        try:
            if self._file_mode != 'replaygain':
                audiotools.open(in_filepath).convert(
                    out_filepath, self._format, compression=self._compression)
            else:
                in_file = audiotools.open(in_filepath)
                rp_info = self.get_replaygain(in_filepath)
                if rp_info:
                    pcmreader = audiotools.replaygain.ReplayGainReader(
                        in_file.to_pcm(),
                        rp_info.replaygain_album_gain,
                        rp_info.replaygain_album_peak)
                    self._format.from_pcm(out_filepath, pcmreader,
                                          compression=self._compression)
                else:
                    print("No ReplayGain info found {}".format(in_filepath))
                    audiotools.open(in_filepath).convert(
                        out_filepath, self._format,
                        compression=self._compression)
        except (audiotools.EncodingError, audiotools.UnsupportedFile) as err:
            raise IOError("Failed to transcode file {}: {}"
                          .format(in_filepath, err))

    def copy_tags(self, in_filepath, out_filepath):
        """ Copy tags """
        in_file = mutagen.File(in_filepath)

        # Tags are converted to ID3 format. If the output format is changed
        # in the functions above, this function has to be adapted too.
        try:
            mp3_file = mutagen.mp3.MP3(out_filepath)
        except mutagen.mp3.HeaderNotFoundError:
            raise IOError("Output file is not in MP3 format")

        if not mp3_file.tags:
            mp3_file.tags = mutagen.id3.ID3()

        # Tags are processed depending on their input format.
        if isinstance(in_file, mutagen.mp3.MP3):
            self.copy_id3_to_id3(in_file.tags, mp3_file.tags)
        elif (isinstance(in_file, (mutagen.flac.FLAC,
                                   mutagen.oggvorbis.OggVorbis))):
            self.copy_vorbis_to_id3(in_file.tags, mp3_file.tags)
            self.copy_vorbis_picture_to_id3(in_file, mp3_file.tags)
        else:
            raise IOError("Input file tag conversion not implemented")

        # Load the image from folder.jpg
        self.copy_folder_image_to_id3(in_filepath, mp3_file.tags)

        # Apply hacks
        if self._composer_hack:
            self.apply_composer_hack(mp3_file.tags)
        if self._discnumber_hack:
            self.apply_disknumber_hack(mp3_file.tags)
        if self._tracknumber_hack:
            self.apply_tracknumber_hack(mp3_file.tags)

        # Remove ReplayGain tags if the volume has already been changed
        if self._file_mode == 'replaygain':
            mp3_file.tags.delall('TXXX:replaygain_album_gain')
            mp3_file.tags.delall('TXXX:replaygain_album_peak')
            mp3_file.tags.delall('TXXX:replaygain_track_gain')
            mp3_file.tags.delall('TXXX:replaygain_track_peak')

        # Save as id3v1 and id3v2.3
        mp3_file.tags.update_to_v23()
        mp3_file.tags.save(out_filepath, v1=2, v2_version=3)

    @classmethod
    def copy_vorbis_to_id3(cls, src_tags, dest_tags):
        """ Copy tags in vorbis comments (ogg, flac) to ID3 format """
        tagtable = {
            'album': mutagen.id3.TALB,
            'artist': mutagen.id3.TPE1,
            'albumartist': mutagen.id3.TPE2,
            'title': mutagen.id3.TIT2,
            'genre': mutagen.id3.TCON,
            'date': mutagen.id3.TDRC,
            'tracknumber': mutagen.id3.TRCK,
            'discnumber': mutagen.id3.TPOS,
            'MUSICBRAINZ_TRACKID': 'http://musicbrainz.org',
            'MUSICBRAINZ_ARTISTID': 'MusicBrainz Artist Id',
            'MUSICBRAINZ_ALBUMARTISTID': 'MusicBrainz Album Artist Id',
            'MUSICBRAINZ_RELEASEGROUPID': 'MusicBrainz Release Group Id',
            'MUSICBRAINZ_ALBUMID': 'MusicBrainz Album Id',
            'MUSICBRAINZ_RELEASETRACKID': 'MusicBrainz Release Track Id',
            'replaygain_album_gain': 'replaygain_album_gain',
            'replaygain_album_peak': 'replaygain_album_peak',
            'replaygain_track_gain': 'replaygain_track_gain',
            'replaygain_track_peak': 'replaygain_track_peak'
        }
        for tag in tagtable:
            if tag in src_tags:
                id3tag = tagtable[tag]
                if tag == 'tracknumber':
                    track = src_tags['tracknumber'][0]
                    if 'tracktotal' in src_tags:
                        track = '{}/{}'.format(track,
                                               src_tags['tracktotal'][0])
                    dest_tags.add(id3tag(encoding=3, text=track))
                elif tag == 'discnumber':
                    disc = src_tags['discnumber'][0]
                    if 'disctotal' in src_tags:
                        disc = '{}/{}'.format(disc, src_tags['disctotal'][0])
                    dest_tags.add(id3tag(encoding=3, text=disc))
                elif tag == 'MUSICBRAINZ_TRACKID':
                    dest_tags.add(mutagen.id3.UFID(
                        owner=id3tag, data=src_tags[tag][0].encode()))
                elif isinstance(id3tag, str):  # TXXX tags
                    dest_tags.add(mutagen.id3.TXXX(encoding=3, desc=id3tag,
                                                   text=src_tags[tag]))
                else:  # All other tags
                    dest_tags.add(id3tag(encoding=3, text=src_tags[tag]))

    @classmethod
    def copy_vorbis_picture_to_id3(cls, in_file, dest_tags):
        """ Copy pictures from vorbis comments to ID3 format """
        pictures = []
        try:  # Flac
            pictures.extend(in_file.pictures)
        except AttributeError:
            pass

        if 'METADATA_BLOCK_PICTURE' in in_file.tags:  # OggVorbis
            for data in in_file.tags['METADATA_BLOCK_PICTURE']:
                pictures.append(mutagen.flac.Picture(
                    base64.b64decode(data)))
        for picture in pictures:
            dest_tags.add(mutagen.id3.APIC(encoding=3,
                                           desc=picture.desc,
                                           data=picture.data,
                                           type=picture.type,
                                           mime=picture.mime))

    @classmethod
    def copy_id3_to_id3(cls, src_tags, dest_tags):
        """ Copy tags from ID3 to ID3 """
        taglist = [
            'TALB',
            'TPE1',
            'TPE2',
            'TIT2',
            'TCON',
            'TDRC',
            'TRCK',
            'TPOS',
            'APIC:',
            'UFID:http://musicbrainz.org',
            'TXXX:MusicBrainz Artist Id',
            'TXXX:MusicBrainz Album Artist Id'
            'TXXX:MusicBrainz Release Group Id',
            'TXXX:MusicBrainz Album Id',
            'TXXX:MusicBrainz Release Track Id',
            'TXXX:replaygain_album_gain',
            'TXXX:replaygain_album_peak',
            'TXXX:replaygain_track_gain',
            'TXXX:replaygain_track_peak'
        ]
        if src_tags is None:
            return
        for tag in taglist:
            if tag in src_tags:
                dest_tags.add(src_tags[tag])

    @classmethod
    def copy_folder_image_to_id3(cls, in_filename, dest_tags):
        """ Copy folder.jpg to ID3 tag """
        if 'APIC:' not in dest_tags:
            image = os.path.join(os.path.dirname(in_filename), 'folder.jpg')
            if os.path.exists(image):
                image_file = open(image, 'rb')
                img = image_file.read()
                image_file.close()
                dest_tags.add(mutagen.id3.APIC(3, 'image/jpg', 3, '', img))

    @classmethod
    def apply_composer_hack(cls, tags):
        """ Copy the albumartist (TPE2) into the composer field (TCOM) """
        if 'TPE2' in tags:
            tags.add(mutagen.id3.TCOM(encoding=3, text=tags['TPE2'].text))

    @classmethod
    def apply_disknumber_hack(cls, tags):
        """ Extend album field by disc number """
        if 'TALB' in tags and 'TPOS' in tags and not tags['TPOS'] == '1':
            tags.add(mutagen.id3.TALB(
                encoding=tags['TALB'].encoding,
                text=tags['TALB'].text[0] + ' - ' + tags['TPOS'].text[0]))

    @classmethod
    def apply_tracknumber_hack(cls, tags):
        """ Remove track total from track number """
        if 'TRCK' in tags:
            track_string = tags['TRCK'].text[0].split('/')[0]
            try:
                track_string = str(int(track_string))
            except ValueError:
                pass
            tags.add(mutagen.id3.TRCK(encoding=0, text=track_string))

# sync_music - Sync music library to external device
# Copyright (C) 2013-2018 Christian Fetzer
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

"""Process Metadata action."""

import base64
import logging

import mutagen

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ProcessMetadata:
    """Copy audio file metadata."""

    name = "Processing Metadata"

    def __init__(  # pylint: disable=too-many-arguments
        self,
        copy_replaygain=True,
        albumartist_artist_hack=False,
        albumartist_composer_hack=False,
        artist_albumartist_hack=False,
        discnumber_hack=False,
        tracknumber_hack=False,
    ):
        self._copy_replaygain = copy_replaygain
        self._albumartist_artist_hack = albumartist_artist_hack
        self._albumartist_composer_hack = albumartist_composer_hack
        self._artist_albumartist_hack = artist_albumartist_hack
        self._discnumber_hack = discnumber_hack
        self._tracknumber_hack = tracknumber_hack

        logger.info("Processing metadata with Mutagen (%s):", mutagen.version_string)
        if self._copy_replaygain:
            logger.info(" - Copying ReplayGain tags")
        else:
            logger.info(" - Discarding ReplayGain tags")
        if albumartist_artist_hack:
            logger.info(" - Hack: Writing albumartist into artist field")
        if albumartist_composer_hack:
            logger.info(" - Hack: Writing albumartist into composer field")
        if artist_albumartist_hack:
            logger.info(" - Hack: Writing artist into albumartist field")
        if discnumber_hack:
            logger.info(" - Hack: Extending album field by disc number")
        if tracknumber_hack:
            logger.info(" - Hack: Remove track total from track number")
        logger.info("")

    def execute(self, in_filepath, out_filepath):
        """Processing metadata."""
        in_file = mutagen.File(in_filepath)

        # Tags are converted to ID3 format. If the output format is changed
        # in the functions above, this function has to be adapted too.
        try:
            mp3_file = mutagen.mp3.MP3(out_filepath)
        except mutagen.mp3.HeaderNotFoundError as err:
            raise IOError("Output file is not in MP3 format") from err

        if not mp3_file.tags:
            mp3_file.tags = mutagen.id3.ID3()

        # Tags are processed depending on their input format.
        if isinstance(in_file, mutagen.mp3.MP3):
            self.copy_id3_to_id3(in_file.tags, mp3_file.tags)
        elif isinstance(in_file, (mutagen.flac.FLAC, mutagen.oggvorbis.OggVorbis)):
            self.copy_vorbis_to_id3(in_file.tags, mp3_file.tags)
            self.copy_vorbis_picture_to_id3(in_file, mp3_file.tags)
        elif isinstance(in_file, mutagen.mp4.MP4):
            self.copy_mp4_to_id3(in_file.tags, mp3_file.tags)
            self.copy_mp4_picture_to_id3(in_file, mp3_file.tags)
        else:
            raise IOError("Input file tag conversion not implemented")

        # Load the image from folder.jpg
        self.copy_folder_image_to_id3(in_filepath, mp3_file.tags)

        # Apply hacks
        if self._albumartist_artist_hack:
            self.apply_albumartist_artist_hack(mp3_file.tags)
        if self._albumartist_composer_hack:
            self.apply_albumartist_composer_hack(mp3_file.tags)
        if self._artist_albumartist_hack:
            self.apply_artist_albumartist_hack(mp3_file.tags)
        if self._discnumber_hack:
            self.apply_disknumber_hack(mp3_file.tags)
        if self._tracknumber_hack:
            self.apply_tracknumber_hack(mp3_file.tags)

        # Remove ReplayGain tags if the volume has already been changed
        if not self._copy_replaygain:
            mp3_file.tags.delall("TXXX:replaygain_album_gain")
            mp3_file.tags.delall("TXXX:replaygain_album_peak")
            mp3_file.tags.delall("TXXX:replaygain_track_gain")
            mp3_file.tags.delall("TXXX:replaygain_track_peak")

        # Save as id3v1 and id3v2.3
        mp3_file.tags.update_to_v23()
        mp3_file.tags.save(out_filepath, v1=2, v2_version=3)

    @classmethod
    def copy_vorbis_to_id3(cls, src_tags, dest_tags):
        """Copy tags in vorbis comments (ogg, flac) to ID3 format."""
        tagtable = {
            "album": mutagen.id3.TALB,
            "artist": mutagen.id3.TPE1,
            "albumartist": mutagen.id3.TPE2,
            "title": mutagen.id3.TIT2,
            "genre": mutagen.id3.TCON,
            "date": mutagen.id3.TDRC,
            "tracknumber": mutagen.id3.TRCK,
            "discnumber": mutagen.id3.TPOS,
            "MUSICBRAINZ_TRACKID": "http://musicbrainz.org",
            "MUSICBRAINZ_ARTISTID": "MusicBrainz Artist Id",
            "MUSICBRAINZ_ALBUMARTISTID": "MusicBrainz Album Artist Id",
            "MUSICBRAINZ_RELEASEGROUPID": "MusicBrainz Release Group Id",
            "MUSICBRAINZ_ALBUMID": "MusicBrainz Album Id",
            "MUSICBRAINZ_RELEASETRACKID": "MusicBrainz Release Track Id",
            "replaygain_album_gain": "replaygain_album_gain",
            "replaygain_album_peak": "replaygain_album_peak",
            "replaygain_track_gain": "replaygain_track_gain",
            "replaygain_track_peak": "replaygain_track_peak",
        }
        for tag, id3tag in tagtable.items():
            if tag in src_tags:
                if tag == "tracknumber":
                    track = src_tags["tracknumber"][0]
                    if "tracktotal" in src_tags:
                        track = f"{track}/{src_tags['tracktotal'][0]}"
                    dest_tags.add(id3tag(encoding=3, text=track))
                elif tag == "discnumber":
                    disc = src_tags["discnumber"][0]
                    if "disctotal" in src_tags:
                        disc = f"{disc}/{src_tags['disctotal'][0]}"
                    dest_tags.add(id3tag(encoding=3, text=disc))
                elif tag == "MUSICBRAINZ_TRACKID":
                    dest_tags.add(
                        mutagen.id3.UFID(owner=id3tag, data=src_tags[tag][0].encode())
                    )
                elif isinstance(id3tag, str):  # TXXX tags
                    dest_tags.add(
                        mutagen.id3.TXXX(encoding=3, desc=id3tag, text=src_tags[tag])
                    )
                else:  # All other tags
                    dest_tags.add(id3tag(encoding=3, text=src_tags[tag]))

    @classmethod
    def copy_vorbis_picture_to_id3(cls, in_file, dest_tags):
        """Copy pictures from vorbis comments to ID3 format."""
        pictures = []
        try:  # Flac
            pictures.extend(in_file.pictures)
        except AttributeError:
            pass

        if "METADATA_BLOCK_PICTURE" in in_file.tags:  # OggVorbis
            for data in in_file.tags["METADATA_BLOCK_PICTURE"]:
                pictures.append(mutagen.flac.Picture(base64.b64decode(data)))
        for picture in pictures:
            dest_tags.add(
                mutagen.id3.APIC(
                    encoding=3,
                    desc=picture.desc,
                    data=picture.data,
                    type=picture.type,
                    mime=picture.mime,
                )
            )

    @classmethod
    def copy_mp4_to_id3(cls, src_tags, dest_tags):
        """Copy tags in MP4 format (m4a, ...) to ID3 format."""
        tagtable = {
            "\xa9alb": mutagen.id3.TALB,
            "\xa9ART": mutagen.id3.TPE1,
            "aART": mutagen.id3.TPE2,
            "\xa9nam": mutagen.id3.TIT2,
            "\xa9gen": mutagen.id3.TCON,
            "\xa9day": mutagen.id3.TDRC,
            "trkn": mutagen.id3.TRCK,
            "disk": mutagen.id3.TPOS,
            "----:com.apple.iTunes:MusicBrainz Track Id": "http://musicbrainz.org",
            "----:com.apple.iTunes:MusicBrainz Artist Id": "MusicBrainz Artist Id",
            "----:com.apple.iTunes:MusicBrainz Album Artist Id": "MusicBrainz Album Artist Id",
            "----:com.apple.iTunes:MusicBrainz Release Group Id": "MusicBrainz Release Group Id",
            "----:com.apple.iTunes:MusicBrainz Album Id": "MusicBrainz Album Id",
            "----:com.apple.iTunes:MusicBrainz Release Track Id": "MusicBrainz Release Track Id",
            "----:com.apple.iTunes:replaygain_album_gain": "replaygain_album_gain",
            "----:com.apple.iTunes:replaygain_album_peak": "replaygain_album_peak",
            "----:com.apple.iTunes:replaygain_track_gain": "replaygain_track_gain",
            "----:com.apple.iTunes:replaygain_track_peak": "replaygain_track_peak",
        }
        for tag, id3tag in tagtable.items():
            if tag in src_tags:
                if tag == "trkn":
                    track = str(src_tags["trkn"][0][0])
                    if src_tags["trkn"][0][1] != 0:
                        track = f"{track}/{src_tags['trkn'][0][1]}"
                    dest_tags.add(id3tag(encoding=3, text=track))
                elif tag == "disk":
                    disk = str(src_tags["disk"][0][0])
                    if src_tags["disk"][0][1] != 0:
                        disk = f"{disk}/{src_tags['disk'][0][1]}"
                    dest_tags.add(id3tag(encoding=3, text=disk))
                elif tag == "----:com.apple.iTunes:MusicBrainz Track Id":
                    dest_tags.add(mutagen.id3.UFID(owner=id3tag, data=src_tags[tag][0]))
                elif isinstance(id3tag, str):  # TXXX tags
                    dest_tags.add(
                        mutagen.id3.TXXX(
                            encoding=3,
                            desc=id3tag,
                            text=src_tags[tag][0].decode("utf-8", "ignore"),
                        )
                    )
                else:  # All other tags
                    dest_tags.add(id3tag(encoding=3, text=src_tags[tag][0]))

    @classmethod
    def copy_mp4_picture_to_id3(cls, in_file, dest_tags):
        """Copy pictures from mp4 format to ID3 format."""
        if "covr" in in_file.tags:
            picture = in_file["covr"][0]

            # MP4 & Mutagen supports only PNG or JPEG, default being JPEG.
            mime = "jpeg"
            if picture.imageformat == mutagen.mp4.AtomDataType.PNG:
                mime = "png"

            dest_tags.add(
                mutagen.id3.APIC(
                    encoding=3,
                    desc="",
                    data=picture,
                    type=mutagen.id3.PictureType.COVER_FRONT,
                    mime=f"mime/{mime}",
                )
            )

    ID3_TAGS = [
        "TALB",
        "TPE1",
        "TPE2",
        "TIT2",
        "TCON",
        "TDRC",
        "TRCK",
        "TPOS",
        "APIC:",
        "UFID:http://musicbrainz.org",
        "TXXX:MusicBrainz Artist Id",
        "TXXX:MusicBrainz Album Artist Id",
        "TXXX:MusicBrainz Release Group Id",
        "TXXX:MusicBrainz Album Id",
        "TXXX:MusicBrainz Release Track Id",
        "TXXX:replaygain_album_gain",
        "TXXX:replaygain_album_peak",
        "TXXX:replaygain_track_gain",
        "TXXX:replaygain_track_peak",
    ]

    @classmethod
    def copy_id3_to_id3(cls, src_tags, dest_tags):
        """Copy tags from ID3 to ID3."""
        if src_tags is None:
            return
        for tag in cls.ID3_TAGS:
            if tag in src_tags:
                dest_tags.add(src_tags[tag])

    @classmethod
    def copy_folder_image_to_id3(cls, in_filename, dest_tags):
        """Copy folder.jpg to ID3 tag."""
        if "APIC:" not in dest_tags:
            image = in_filename.parent / "folder.jpg"
            if image.exists():
                with image.open("rb") as image_file:
                    img = image_file.read()
                dest_tags.add(mutagen.id3.APIC(3, "image/jpg", 3, "", img))

    @classmethod
    def apply_albumartist_artist_hack(cls, tags):
        """Copy the albumartist (TPE2) into the artist field (TPE1)."""
        artist = tags["TPE2"].text if "TPE2" in tags else "Various Artists"
        tags.add(mutagen.id3.TPE1(encoding=3, text=artist))

    @classmethod
    def apply_albumartist_composer_hack(cls, tags):
        """Copy the albumartist (TPE2) into the composer field (TCOM)."""
        if "TPE2" in tags:
            tags.add(mutagen.id3.TCOM(encoding=3, text=tags["TPE2"].text))

    @classmethod
    def apply_artist_albumartist_hack(cls, tags):
        """Copy the artist (TPE1) into the albumartist field (TPE2)."""
        albumartist = tags["TPE1"].text if "TPE1" in tags else "Various Artists"
        tags.add(mutagen.id3.TPE2(encoding=3, text=albumartist))

    @classmethod
    def apply_disknumber_hack(cls, tags):
        """Extend album field by disc number."""
        if "TALB" in tags and "TPOS" in tags and not tags["TPOS"] == "1":
            tags.add(
                mutagen.id3.TALB(
                    encoding=tags["TALB"].encoding,
                    text=tags["TALB"].text[0] + " - " + tags["TPOS"].text[0],
                )
            )

    @classmethod
    def apply_tracknumber_hack(cls, tags):
        """Remove track total from track number."""
        if "TRCK" in tags:
            track_string = tags["TRCK"].text[0].split("/")[0]
            try:
                track_string = str(int(track_string))
            except ValueError:
                pass
            tags.add(mutagen.id3.TRCK(encoding=0, text=track_string))

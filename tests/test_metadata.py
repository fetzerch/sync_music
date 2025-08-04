# music_sync - Sync music library to external device
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

"""Tests the metadata processing implementation."""

import shutil

import mutagen
import pytest

from sync_music.sync_music import ProcessMetadata

from tests import (
    ReferenceFiles,
    mutagen_filter_tags,
    run_withreferencefiles_alltags,
    run_withreferencefiles_notags,
)


class TestMetadata:
    """Tests the metadata processing implementation."""

    @staticmethod
    @pytest.fixture
    def out_path(tmp_path):
        """Setup temporary output directory. Prepare empty mp3 file."""
        output_path = tmp_path / "withtags.mp3"
        shutil.copy(ReferenceFiles.MP3_EMPTY, output_path)
        return output_path

    @staticmethod
    @run_withreferencefiles_alltags
    def test_processmetadata(in_path, out_path):
        """Test transcoding with default options."""
        ProcessMetadata().execute(in_path, out_path)
        reference_tags = mutagen.File(ReferenceFiles.MP3_ALL).tags
        tags = mutagen.File(out_path).tags

        for tag in [tag for tag in ProcessMetadata.ID3_TAGS if "replaygain" not in tag]:
            assert tags[tag] == reference_tags[tag]

        for tag in [tag for tag in ProcessMetadata.ID3_TAGS if "replaygain" in tag]:
            assert tags[tag]

    @staticmethod
    @run_withreferencefiles_notags
    def test_processmetadata_empty(in_path, out_path):
        """Test transcoding files that have no tags."""
        assert not mutagen.File(in_path).tags
        ProcessMetadata().execute(in_path, out_path)
        # The folder image is the only tag added to the output file.
        assert list(mutagen.File(out_path).tags.keys()) == ["APIC:"]

    @staticmethod
    def test_processmetadata_noreplaygain(out_path):
        """Tests transcoding without copying ReplayGain."""
        assert mutagen_filter_tags(mutagen.File(ReferenceFiles.MP3_ALL), "replaygain")
        ProcessMetadata(copy_replaygain=False).execute(ReferenceFiles.MP3_ALL, out_path)
        assert not mutagen_filter_tags(mutagen.File(out_path), "replaygain")

    @staticmethod
    def test_processmetadata_folderimage_missing(out_path):
        """Tests transcoding without folder image."""
        assert "APIC:" not in mutagen.File(ReferenceFiles.MP3).tags
        # Copy input file to a folder without folder.jpg (output folder)
        in_filepath = out_path.parent / ReferenceFiles.MP3.name
        shutil.copy(ReferenceFiles.MP3, in_filepath)
        ProcessMetadata().execute(in_filepath, out_path)
        assert "APIC:" not in mutagen.File(out_path).tags

    @staticmethod
    def test_processmetadata_error(out_path):
        """Tests copying tag failure."""
        # Copy tags expects the output file to be an MP3 file.
        # Don't transcode as this would rewrite the output file.
        shutil.copy(ReferenceFiles.FOLDER_IMAGE, out_path)
        with pytest.raises(IOError):
            ProcessMetadata().execute(ReferenceFiles.FOLDER_IMAGE, out_path)

    @staticmethod
    def test_processmetadata_formaterror(out_path):
        """Tests transcoding a non supported format."""
        with pytest.raises(IOError):
            ProcessMetadata().execute(ReferenceFiles.FOLDER_IMAGE, out_path)

    @staticmethod
    def test_processmetadata_m4a_pngimage(out_path):
        """Tests transcoding an M4A file with PNG image."""
        ProcessMetadata().execute(ReferenceFiles.M4A_PNGIMAGE, out_path)
        tags = mutagen.File(out_path).tags
        assert tags["APIC:"].mime == "mime/png"

    @staticmethod
    def test_processmetadata_artist_hack(out_path):
        """Tests transcoding with albumartist to artist hack enabled."""
        in_file = mutagen.File(ReferenceFiles.FLAC)
        assert in_file.tags["albumartist"] != in_file.tags["artist"]
        ProcessMetadata(albumartist_artist_hack=True).execute(
            ReferenceFiles.FLAC, out_path
        )
        assert mutagen.File(out_path).tags["TPE1"] == in_file.tags["albumartist"]

    @staticmethod
    def test_processmetadata_artist_hackempty(out_path):
        """Tests transcoding with albumartist to artist hack enabled."""
        ProcessMetadata(albumartist_artist_hack=True).execute(
            ReferenceFiles.FLAC_EMPTY, out_path
        )
        assert mutagen.File(out_path).tags["TPE1"] == "Various Artists"

    @staticmethod
    def test_processmetadata_composer_hack(out_path):
        """Tests transcoding with albumartist to composer hack enabled."""
        in_file = mutagen.File(ReferenceFiles.FLAC)
        assert "composer" not in in_file.tags.keys()
        ProcessMetadata(albumartist_composer_hack=True).execute(
            ReferenceFiles.FLAC, out_path
        )
        assert mutagen.File(out_path).tags["TCOM"] == in_file.tags["albumartist"]

    @staticmethod
    def test_processmetadata_composer_hackempty(out_path):
        """Tests transcoding with albumartist to composer hack enabled."""
        ProcessMetadata(albumartist_composer_hack=True).execute(
            ReferenceFiles.FLAC_EMPTY, out_path
        )
        assert "TCOM" not in mutagen.File(out_path).tags.keys()

    @staticmethod
    def test_processmetadata_artist_albumartist_hack(out_path):
        """Tests transcoding with artist to albumartist hack enabled."""
        in_file = mutagen.File(ReferenceFiles.FLAC)
        assert in_file.tags["albumartist"] != in_file.tags["artist"]
        ProcessMetadata(artist_albumartist_hack=True).execute(
            ReferenceFiles.FLAC, out_path
        )
        assert mutagen.File(out_path).tags["TPE2"] == in_file.tags["artist"]

    @staticmethod
    def test_processmetadata_artist_albumartist_hackempty(out_path):
        """Tests transcoding with artist to albumartist hack enabled."""
        ProcessMetadata(artist_albumartist_hack=True).execute(
            ReferenceFiles.FLAC_EMPTY, out_path
        )
        assert mutagen.File(out_path).tags["TPE2"] == "Various Artists"

    @staticmethod
    def test_processmetadata_discnumber_hack(out_path):
        """Tests transcoding with disc number hack enabled."""
        in_file = mutagen.File(ReferenceFiles.FLAC)
        ProcessMetadata(discnumber_hack=True).execute(ReferenceFiles.FLAC, out_path)
        out_file = mutagen.File(out_path)
        assert (
            out_file.tags["TALB"]
            == f"{in_file.tags['album'][0]} - {in_file.tags['discnumber'][0]}"
        )

    @staticmethod
    def test_processmetadata_discnumber_hackempty(out_path):
        """Tests transcoding with disc number hack enabled."""
        ProcessMetadata(discnumber_hack=True).execute(
            ReferenceFiles.FLAC_EMPTY, out_path
        )
        assert "TALB" not in mutagen.File(out_path).tags.keys()

    @staticmethod
    def test_processmetadata_tracknumber_hack(out_path):
        """Tests transcoding with track number hack enabled."""
        ProcessMetadata(tracknumber_hack=True).execute(ReferenceFiles.FLAC, out_path)
        assert "/" not in mutagen.File(out_path).tags["TRCK"].text[0]

    @staticmethod
    def test_processmetadata_tracknumber_hackempty(out_path):
        """Tests transcoding with track number hack enabled."""
        ProcessMetadata(tracknumber_hack=True).execute(
            ReferenceFiles.FLAC_EMPTY, out_path
        )
        assert "TRCK" not in mutagen.File(out_path).tags.keys()

    @staticmethod
    def test_processmetadata_tracknumber_hackbroken(out_path):
        """Tests transcoding with track number hack enabled."""
        in_file = mutagen.File(ReferenceFiles.MP3_BROKENTRACKNUMBER)
        ProcessMetadata(tracknumber_hack=True).execute(
            ReferenceFiles.MP3_BROKENTRACKNUMBER, out_path
        )
        assert mutagen.File(out_path).tags["TRCK"] == in_file.tags["TRCK"]

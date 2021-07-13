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

import pytest

from sync_music.sync_music import ProcessMetadata

from tests import REFERENCE_FILES


class TestMetadata:
    """Tests the metadata processing implementation."""

    @staticmethod
    @pytest.fixture
    def out_path(tmp_path):
        """Setup temporary output directory. Prepare empty mp3 file."""
        output_path = tmp_path / "withtags.mp3"
        shutil.copy(REFERENCE_FILES.MP3_EMPTY, output_path)
        return output_path

    @staticmethod
    def test_processmetadata_default(out_path):
        """Test transcoding with default options."""
        ProcessMetadata().execute(REFERENCE_FILES.MP3, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.MP3_ALL, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.MP3_EMPTY, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.FLAC, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.FLAC_ALL, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.FLAC_EMPTY, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.OGG, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.OGG_ALL, out_path)
        ProcessMetadata().execute(REFERENCE_FILES.OGG_EMPTY, out_path)

    @staticmethod
    def test_processmetadata_noreplaygain(out_path):
        """Tests transcoding without ReplayGain."""
        ProcessMetadata(copy_replaygain=False).execute(REFERENCE_FILES.FLAC, out_path)

    @staticmethod
    def test_processmetadata_folderimage(out_path):
        """Tests transcoding without folder image."""
        # Copy input file to a folder without folder.jpg (output folder)
        in_filepath = out_path.parent / REFERENCE_FILES.FLAC.name
        shutil.copy(REFERENCE_FILES.FLAC, in_filepath)
        ProcessMetadata().execute(in_filepath, out_path)

    @staticmethod
    def test_processmetadata_artist_hack(out_path):
        """Tests transcoding with albumartist to artist hack enabled."""
        ProcessMetadata(albumartist_artist_hack=True).execute(
            REFERENCE_FILES.FLAC, out_path
        )
        ProcessMetadata(albumartist_artist_hack=True).execute(
            REFERENCE_FILES.FLAC_EMPTY, out_path
        )

    @staticmethod
    def test_processmetadata_composer_hack(out_path):
        """Tests transcoding with albumartist to composer hack enabled."""
        ProcessMetadata(albumartist_composer_hack=True).execute(
            REFERENCE_FILES.FLAC, out_path
        )
        ProcessMetadata(albumartist_composer_hack=True).execute(
            REFERENCE_FILES.FLAC_EMPTY, out_path
        )

    @staticmethod
    def test_processmetadata_artist_albumartist_hack(out_path):
        """Tests transcoding with albumartist to artist hack enabled."""
        ProcessMetadata(artist_albumartist_hack=True).execute(
            REFERENCE_FILES.FLAC, out_path
        )
        ProcessMetadata(artist_albumartist_hack=True).execute(
            REFERENCE_FILES.FLAC_EMPTY, out_path
        )

    @staticmethod
    def test_processmetadata_discnumber_hack(out_path):
        """Tests transcoding with disc number hack enabled."""
        ProcessMetadata(discnumber_hack=True).execute(REFERENCE_FILES.FLAC, out_path)
        ProcessMetadata(discnumber_hack=True).execute(
            REFERENCE_FILES.FLAC_ALL, out_path
        )

    @staticmethod
    def test_processmetadata_tracknumber_hack(out_path):
        """Tests transcoding with track number hack enabled."""
        ProcessMetadata(tracknumber_hack=True).execute(REFERENCE_FILES.FLAC, out_path)
        ProcessMetadata(tracknumber_hack=True).execute(
            REFERENCE_FILES.FLAC_EMPTY, out_path
        )
        ProcessMetadata(tracknumber_hack=True).execute(
            REFERENCE_FILES.MP3_BROKENTRACKNUMBER, out_path
        )

    @staticmethod
    def test_processmetadata_error(out_path):
        """Tests copying tag failure."""
        # Copy tags expects the output file to be an MP3 file.
        # Don't transcode as this would rewrite the output file.
        shutil.copy(REFERENCE_FILES.FOLDER_IMAGE, out_path)
        with pytest.raises(IOError):
            ProcessMetadata().execute(REFERENCE_FILES.FOLDER_IMAGE, out_path)

    @staticmethod
    def test_processmetadata_formaterror(out_path):
        """Tests transcoding a non supported format."""
        with pytest.raises(IOError):
            ProcessMetadata().execute(REFERENCE_FILES.FOLDER_IMAGE, out_path)

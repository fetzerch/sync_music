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

"""Tests the transcoding implementation."""

import pathlib

import pytest

from sync_music.transcode import Transcode

from tests import REFERENCE_FILES


class TestTranscode:
    """Tests the transcoding implementation."""

    @staticmethod
    @pytest.fixture
    def out_path(tmp_path):
        """Setup temporary output directory."""
        return tmp_path / "withtags.mp3"

    @staticmethod
    def test_filename():
        """Tests retrieving the output file name."""
        transcode = Transcode()
        out_filename = transcode.get_out_filename(REFERENCE_FILES.FLAC)
        assert out_filename == REFERENCE_FILES.FLAC.with_suffix(".mp3")

    @staticmethod
    def test_transcode_default(out_path):
        """Test transcoding with default options."""
        Transcode().execute(REFERENCE_FILES.MP3, out_path)
        Transcode().execute(REFERENCE_FILES.FLAC, out_path)
        Transcode().execute(REFERENCE_FILES.OGG, out_path)

    @staticmethod
    def test_transcode_replaygain(out_path):
        """Tests transcoding with ReplayGain (track based)."""
        Transcode(mode="replaygain").execute(REFERENCE_FILES.MP3_ALL, out_path)
        Transcode(mode="replaygain").execute(REFERENCE_FILES.MP3, out_path)

    @staticmethod
    def test_transcode_replaygainalbum(out_path):
        """Tests transcoding with ReplayGain (album based)."""
        Transcode(mode="replaygain-album", replaygain_preamp_gain=10.0).execute(
            REFERENCE_FILES.MP3_ALL, out_path
        )

    @staticmethod
    def test_transcode_transcodeerror():
        """Tests transcoding failure."""
        # IOError is raised on audiotools.EncodingError. The easiest way that
        # leads into this exception is writing to a non writable path.
        with pytest.raises(IOError):
            Transcode().execute(REFERENCE_FILES.FLAC, pathlib.Path("/"))

    @staticmethod
    def test_transcode_formaterror(out_path):
        """Tests transcoding a non supported format."""
        with pytest.raises(IOError):
            Transcode().execute(REFERENCE_FILES.FOLDER_IMAGE, out_path)

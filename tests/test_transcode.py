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

import mutagen
import pytest

from sync_music.transcode import Transcode
from sync_music.replaygain import ReplayGain

from tests import (
    ReferenceFiles,
    mutagen_filter_tags,
    run_withreferencefiles_alltags,
    run_withreferencefiles_tags,
)


def assert_approx_replaygain(rp1, rp2):
    """Assert that two ReplayGain objects are approximately the same"""
    assert rp1.gain == pytest.approx(rp2.gain, abs=0.5)
    assert rp1.peak == pytest.approx(rp2.peak, abs=0.1)


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
        out_filename = transcode.get_out_filename(ReferenceFiles.FLAC)
        assert out_filename == ReferenceFiles.FLAC.with_suffix(".mp3")

    @staticmethod
    @run_withreferencefiles_tags
    def test_transcode_default(in_path, out_path):
        """Test transcoding with default options."""
        Transcode().execute(in_path, out_path)
        out_file = mutagen.File(out_path)
        assert isinstance(out_file, mutagen.mp3.MP3)
        assert out_file.info.bitrate_mode == mutagen.mp3.BitrateMode.VBR

    @staticmethod
    @run_withreferencefiles_alltags
    def test_transcode_replaygain(in_path, out_path):
        """Tests transcoding with ReplayGain (track based)."""
        Transcode(mode="replaygain").execute(in_path, out_path)
        rp_info = ReplayGain.from_audiotrack(out_path)
        assert_approx_replaygain(rp_info, ReplayGain(0.0, 0.25))
        assert not mutagen_filter_tags(mutagen.File(out_path), "replaygain")

    @staticmethod
    def test_transcode_replaygain_preamp(out_path):
        """Tests transcoding with ReplayGain (track based) with preamp."""
        Transcode(mode="replaygain", replaygain_preamp_gain=10.0).execute(
            ReferenceFiles.MP3_ALL, out_path
        )
        rp_info = ReplayGain.from_audiotrack(out_path)
        assert_approx_replaygain(rp_info, ReplayGain(-10.0, 0.81))
        assert not mutagen_filter_tags(mutagen.File(out_path), "replaygain")

    @staticmethod
    def test_transcode_replaygain_empty(out_path):
        """Tests transcoding with ReplayGain (track based) without ReplayGain data."""
        Transcode(mode="replaygain").execute(ReferenceFiles.MP3, out_path)
        assert_approx_replaygain(
            ReplayGain.from_audiotrack(out_path),
            ReplayGain.from_audiotrack(ReferenceFiles.MP3),
        )

    @staticmethod
    def test_transcode_replaygain_album(out_path):
        """Tests transcoding with ReplayGain (album based)."""
        Transcode(mode="replaygain-album").execute(ReferenceFiles.MP3_ALL, out_path)
        rp_info = ReplayGain.from_audiotrack(out_path)
        assert_approx_replaygain(rp_info, ReplayGain(0.2, 0.25))
        assert not mutagen_filter_tags(mutagen.File(out_path), "replaygain")

    @staticmethod
    def test_transcode_transcodeerror():
        """Tests transcoding failure."""
        with pytest.raises(IOError):
            Transcode().execute(ReferenceFiles.FLAC, pathlib.Path("/"))

    @staticmethod
    def test_transcode_formaterror(out_path):
        """Tests transcoding a non supported format."""
        with pytest.raises(IOError):
            Transcode().execute(ReferenceFiles.FOLDER_IMAGE, out_path)

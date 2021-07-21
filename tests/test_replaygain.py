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

"""Tests the ReplayGain utils."""

import pytest

from sync_music.replaygain import ReplayGain

from tests import ReferenceFiles


def assert_approx_replaygain(rp1, rp2):
    """Assert that two ReplayGain objects are approximately the same"""
    assert rp1.gain == pytest.approx(rp2.gain, abs=0.2)
    assert rp1.peak == pytest.approx(rp2.peak, abs=0.1)


def assert_approx_multiplicator(multiplicator1, multiplicator2):
    """Assert that two ReplayGain volume multiplicators are approximately the same"""
    assert multiplicator1 == pytest.approx(multiplicator2, abs=0.01)


class TestReplayGain:
    """Tests the ReplayGain utils."""

    @staticmethod
    def test_replaygain_multiplier():
        """Tests calculating the ReplayGain volume multiplicator."""
        assert_approx_multiplicator(ReplayGain(0.0, 0.1).get_volume_multiplier(), 1.0)
        assert_approx_multiplicator(ReplayGain(3.0, 0.1).get_volume_multiplier(), 1.41)
        assert_approx_multiplicator(ReplayGain(-3.0, 0.1).get_volume_multiplier(), 0.70)

        # Peak of 0 disables clipping protection
        assert_approx_multiplicator(ReplayGain(3.0, 0.0).get_volume_multiplier(), 1.41)

        # Peak limits the multiplier
        assert_approx_multiplicator(ReplayGain(4.0, 1.0).get_volume_multiplier(), 1.0)

    REPLAYGAIN_TEST_FILES = [
        (ReferenceFiles.MP3_ALL, ReplayGain(1.91, 0.18)),
        (ReferenceFiles.FLAC_ALL, ReplayGain(0.65, 0.10)),
        (ReferenceFiles.OGG_ALL, ReplayGain(1.01, 0.21)),
    ]

    @staticmethod
    @pytest.mark.parametrize(
        "in_path,expected_rp_info",
        REPLAYGAIN_TEST_FILES,
        ids=[path[0].name for path in REPLAYGAIN_TEST_FILES],
    )
    def test_replaygain_tags(in_path, expected_rp_info):
        """Tests reading ReplayGain information from tags."""
        rp_info = ReplayGain.from_tags(in_path)
        assert_approx_replaygain(rp_info, expected_rp_info)

    @staticmethod
    def test_replaygain_tags_empty():
        """Tests reading ReplayGain information from a file with empty tags."""
        assert not ReplayGain.from_tags(ReferenceFiles.FLAC_EMPTY)

    @staticmethod
    def test_replaygain_tags_formaterror():
        """Tests reading ReplayGain information from a non supported format."""
        assert not ReplayGain.from_tags(ReferenceFiles.FOLDER_IMAGE)

    @staticmethod
    @pytest.mark.parametrize(
        "in_path,expected_rp_info",
        REPLAYGAIN_TEST_FILES,
        ids=[path[0].name for path in REPLAYGAIN_TEST_FILES],
    )
    def test_replaygain_audiotrack(in_path, expected_rp_info):
        """Tests reading ReplayGain information from audio track."""
        rp_info = ReplayGain.from_audiotrack(in_path)
        assert_approx_replaygain(rp_info, expected_rp_info)

    @staticmethod
    def test_replaygain_audiotrack_formaterror():
        """Tests reading ReplayGain information from a non supported format."""
        assert not ReplayGain.from_audiotrack(ReferenceFiles.FOLDER_IMAGE)

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

"""Tests."""

import pathlib

REFERENCE_PATH = pathlib.Path("tests/reference_data/audiofiles")


class REFERENCE_FILES:  # pylint: disable=invalid-name, too-few-public-methods
    """Test reference files."""

    FLAC = REFERENCE_PATH / "withtags.flac"
    FLAC_ALL = REFERENCE_PATH / "withalltags.flac"
    FLAC_EMPTY = REFERENCE_PATH / "stripped.flac"
    OGG = REFERENCE_PATH / "withtags.ogg"
    OGG_ALL = REFERENCE_PATH / "withalltags.ogg"
    OGG_EMPTY = REFERENCE_PATH / "stripped.ogg"
    MP3 = REFERENCE_PATH / "withtags.mp3"
    MP3_ALL = REFERENCE_PATH / "withalltags.mp3"
    MP3_EMPTY = REFERENCE_PATH / "stripped.mp3"
    MP3_BROKENTRACKNUMBER = REFERENCE_PATH / "brokentag_tracknumber.mp3"
    FOLDER_IMAGE = REFERENCE_PATH / "folder.jpg"

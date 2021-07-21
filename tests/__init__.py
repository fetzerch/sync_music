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

import pytest

REFERENCE_PATH = pathlib.Path("tests/reference_data/audiofiles")


class ReferenceFiles:  # pylint: disable=too-few-public-methods
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
    M4A = REFERENCE_PATH / "withtags.m4a"
    M4A_ALL = REFERENCE_PATH / "withalltags.m4a"
    M4A_PNGIMAGE = REFERENCE_PATH / "png_image.m4a"
    M4A_EMPTY = REFERENCE_PATH / "stripped.m4a"
    FOLDER_IMAGE = REFERENCE_PATH / "folder.jpg"

    WITH_TAGS = [
        MP3,
        FLAC,
        OGG,
        M4A,
    ]
    WITH_TAGS_IDS = [path.name for path in WITH_TAGS]

    WITH_ALLTAGS = [
        MP3_ALL,
        FLAC_ALL,
        OGG_ALL,
        M4A_ALL,
    ]
    WITH_ALLTAGS_IDS = [path.name for path in WITH_ALLTAGS]

    WITH_NOTAGS = [
        MP3_EMPTY,
        FLAC_EMPTY,
        OGG_EMPTY,
        M4A_EMPTY,
    ]
    WITH_NOTAGS_IDS = [path.name for path in WITH_NOTAGS]


run_withreferencefiles_tags = pytest.mark.parametrize(
    "in_path",
    ReferenceFiles.WITH_TAGS,
    ids=ReferenceFiles.WITH_TAGS_IDS,
)

run_withreferencefiles_alltags = pytest.mark.parametrize(
    "in_path",
    ReferenceFiles.WITH_ALLTAGS,
    ids=ReferenceFiles.WITH_ALLTAGS_IDS,
)

run_withreferencefiles_notags = pytest.mark.parametrize(
    "in_path",
    ReferenceFiles.WITH_NOTAGS,
    ids=ReferenceFiles.WITH_NOTAGS_IDS,
)


def mutagen_filter_tags(mutagen_file, search):
    """List filtered mutagen tag keys."""
    return [tag for tag in mutagen_file.tags.keys() if search in tag]

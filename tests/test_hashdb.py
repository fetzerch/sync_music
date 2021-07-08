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

"""Tests the HashDb implementation."""

import pathlib

import pytest

from sync_music.sync_music import HashDb


class TestHashDb:
    """Tests the HashDb implementation."""

    @staticmethod
    @pytest.fixture()
    def testfile(tmp_path):
        """Setup test file in temporary directory."""
        return tmp_path / "test_hashdb.db"

    @staticmethod
    def test_storeandload(testfile):
        """Test normal operation."""
        with HashDb(testfile) as hashdb:
            hashdb.add_item("test1", "test2", "test3")
        with HashDb(testfile) as hashdb:
            assert hashdb.get_item("test1") == ("test2", "test3")
            hashdb.delete_item("test1")
        with HashDb(testfile) as hashdb:
            assert not list(hashdb.get_items())

    @staticmethod
    def test_writeerror():
        """Test write error."""
        with HashDb(pathlib.Path("/proc/nonexistent")) as hashdb:
            hashdb.add_item("test1", "test2", "test3")

        with HashDb(pathlib.Path("/proc/nonexistent")) as hashdb:
            assert not list(hashdb.get_items())

    @staticmethod
    def test_hash(testfile):
        """Test file hashing."""
        with testfile.open("wb") as out_file:
            out_file.write(b"TEST")
        assert HashDb.calculate_hash(testfile) == "033bd94b1168d7e4f0d644c3c95e35bf"

    @staticmethod
    def test_internals(testfile):
        """Test potential API usage problems"""
        hashdb = HashDb(testfile)
        with pytest.raises(RuntimeError, match=r".*context manager.*"):
            hashdb.get_items()

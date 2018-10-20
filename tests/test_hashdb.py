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

import os

import pytest

from sync_music.sync_music import HashDb


class TestHashDb:
    """Tests the HashDb implementation."""
    # Format: { in_filename : (out_filename, hash) }
    data = {'test1': ('test2', 'test3'),
            'test_utf8': ('test_äöüß', 'test_ÄÖÜß')}

    @staticmethod
    @pytest.fixture()
    def testfile(tmpdir):
        """Setup test file in temporary directory."""
        return os.path.join(str(tmpdir), 'test_hashdb.db')

    @staticmethod
    def test_nonexistent():
        """Test non existent file."""
        hashdb = HashDb('/proc/nonexistent')
        hashdb.load()
        assert hashdb.database == {}

    def test_writeerror(self):
        """Test write error."""
        hashdb = HashDb('/proc/nonexistent')
        hashdb.database = self.data
        hashdb.store()
        hashdb.database = {}
        hashdb.load()
        assert hashdb.database == {}

    def test_storeandload(self, testfile):
        """Test normal operation."""
        hashdb = HashDb(testfile)
        hashdb.database = self.data
        hashdb.store()
        hashdb.load()
        assert hashdb.database == self.data

    @staticmethod
    def test_hash(testfile):
        """Test file hashing."""
        with open(testfile, 'wb') as out_file:
            out_file.write(b"TEST")
        assert HashDb.get_hash(testfile) == \
            '033bd94b1168d7e4f0d644c3c95e35bf'

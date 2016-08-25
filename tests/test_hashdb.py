# music_sync - Sync music library to external device
# Copyright (C) 2013-2015 Christian Fetzer
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

""" Tests the HashDb implementation """

from nose.tools import eq_

from sync_music.sync_music import HashDb

from . import util


class TestHashDb(object):
    """ Tests the HashDb implementation """
    # Format: { in_filename : (out_filename, hash) }
    data = {'test1': ('test2', 'test3'),
            'test_utf8': ('test_äöüß', 'test_ÄÖÜß')}
    filename = 'test_hashdb.db'

    def teardown(self):
        """ Remove test file after each testcase """
        util.silentremove(self.filename)

    @staticmethod
    def test_nonexistent():
        """ Test non existent file """
        hashdb = HashDb('/proc/nonexistent')
        hashdb.load()
        eq_(hashdb.database, {})

    def test_writeerror(self):
        """ Test write error """
        hashdb = HashDb('/proc/nonexistent')
        hashdb.database = self.data
        hashdb.store()
        hashdb.database = {}
        hashdb.load()
        eq_(hashdb.database, {})

    def test_storeandload(self):
        """ Test normal operation """
        hashdb = HashDb('test_hashdb.db')
        hashdb.database = self.data
        hashdb.store()
        hashdb.load()
        eq_(hashdb.database, self.data)

    def test_hash(self):
        """ Test file hashing """
        with open(self.filename, 'wb') as out_file:
            out_file.write(b"TEST")
        eq_(HashDb.get_hash(self.filename),
            '033bd94b1168d7e4f0d644c3c95e35bf')

# sync_music - Sync music library to external device
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

""" HashDb """

import os
import pickle
import hashlib


class HashDb(object):
    """ Lightwight database for file hash values """

    def __init__(self, path):
        self.database = {}
        self.path = path

    def load(self):
        """ Load hash database to disk """
        if os.path.exists(self.path):
            print("Loading hash database from %s" % self.path)
            hash_file = open(self.path, 'rb')
            self.database = pickle.load(hash_file, encoding="utf-8")
            hash_file.close()
        else:
            print("Failed to load hash database from %s" % self.path)

    def store(self):
        """ Store hash database to disk """
        print("Storing hash database to %s" % self.path)
        try:
            hash_file = open(self.path, 'wb')
            pickle.dump(self.database, hash_file)
            hash_file.close()
        except IOError:
            print("Failed to write hash database to %s" % self.path)

    @classmethod
    def get_hash(cls, path):
        """ Calculate hash value for the given path """
        hash_file = open(path, 'rb')
        hash_buffer = hash_file.read(4096)
        hash_file.close()
        return hashlib.md5(hash_buffer).hexdigest()

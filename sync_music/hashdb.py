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

"""HashDb."""

import contextlib
import functools
import logging
import pickle
import hashlib

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class HashDb(contextlib.ContextDecorator):
    """Lightwight database for file hash values."""

    def __init__(self, path):
        self._path = path
        self._database = None

    def __enter__(self):
        """Load hash database from disk."""
        if self._path.exists():
            logger.info("Loading hash database from %s", self._path)
            with self._path.open("rb") as database_file:
                self._database = pickle.load(database_file, encoding="utf-8")
        else:
            logger.info("No hash database file %s", self._path)
            self._database = {}
        return self

    def __exit__(self, *exc):
        """Store hash database to disk."""
        logger.info("Storing hash database to %s", self._path)
        try:
            with self._path.open("wb") as database_file:
                pickle.dump(self._database, database_file)
        except IOError:
            logger.error("Error: Failed to write hash database to %s", self._path)
        self._database = None

    class _Decorators:  # pylint: disable=too-few-public-methods
        @staticmethod
        def ensure_context_manager(func):
            """Ensure that the HashDb is opened within a context manager"""

            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                if self._database is None:  # pylint: disable=protected-access
                    raise RuntimeError("Method must be used within context manager")
                return func(self, *args, **kwargs)

            return wrapper

    @_Decorators.ensure_context_manager
    def get_items(self):
        """Returns a list of (in_filename, out_filename, hash) tuples"""
        return ((k, *v) for k, v in self._database.items())

    @_Decorators.ensure_context_manager
    def get_item(self, in_filename):
        """Get a single item from the database"""
        return self._database.get(str(in_filename), (None, None))

    @_Decorators.ensure_context_manager
    def add_item(self, in_filename, out_filename, file_hash):
        """Add item  to the database"""
        self._database[str(in_filename)] = (str(out_filename), file_hash)

    @_Decorators.ensure_context_manager
    def delete_item(self, in_filename):
        """Delete item from the database"""
        del self._database[str(in_filename)]

    @classmethod
    def calculate_hash(cls, path):
        """Calculate hash value for the given path."""
        with path.open("rb") as input_file:
            hash_buffer = input_file.read(4096)
        return hashlib.md5(hash_buffer).hexdigest()

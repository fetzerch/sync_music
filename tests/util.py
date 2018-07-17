# music_sync - Sync music library to external device
# Copyright (C) 2013-2017 Christian Fetzer
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

"""Utilities for testing."""

import os
import shutil


def silentremove(path):
    """Remove a file/directory that might not exist."""
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


class TemporaryOutputPathFixture:
    """Fixture that creates a temporary directory before a test runs and
       removes it afterwards."""
    def __init__(self, temporary_path):
        self.temporary_path = temporary_path

    def setup(self):
        """Create output directory."""
        silentremove(self.temporary_path)
        os.mkdir(self.temporary_path)

    def teardown(self):
        """Silently remove output directory."""
        silentremove(self.temporary_path)

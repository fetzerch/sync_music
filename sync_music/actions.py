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

"""Basic actions."""

import shutil


class Copy:
    """Copy action simply copies file."""

    def __init__(self):
        self.name = "Copying"

    @classmethod
    def get_out_filename(cls, path):
        """Determine output file path."""
        return path

    @classmethod
    def execute(cls, in_filepath, out_filepath):
        """Executes action."""
        shutil.copy(in_filepath, out_filepath)


class Skip:
    """Skip action does nothing."""

    def __init__(self):
        self.name = "Skipping"

    @classmethod
    def get_out_filename(cls, _):
        """Determine output file path."""

    @classmethod
    def execute(cls, in_filepath, out_filepath):  # pragma: no cover
        """Executes action."""
        pass

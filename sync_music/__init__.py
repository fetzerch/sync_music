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

"""sync_music - Sync music library to external device."""

import sys

from platform import python_version
from pkg_resources import parse_version


def verify_interpreter_version():
    """Verify the Pyhton interpreter version."""
    minversion = '3.5'
    version = python_version()
    if parse_version(version) < parse_version(minversion):  # pragma: no cover
        sys.stdout.write("Incompatible Python version, minimum supported "
                         "version {}, found version {}\n".format(
                             minversion, version))
        sys.exit(1)


verify_interpreter_version()

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

"""Utilities."""

import logging
import pathlib
import sys
import re


# Utility classes that allow using the built-in logging facilities with
# the newer string.format style instead of the '%' style.
# From: https://docs.python.org/3/howto/logging-cookbook.html


class LogBraceString:  # pylint: disable=too-few-public-methods
    """Log message that supports string.format()."""

    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        return self.fmt.format(*self.args)


class LogStyleAdapter(logging.LoggerAdapter):
    """Logging StyleAdapter that supports string.format()."""

    def __init__(self, logger_instance, extra=None):
        super().__init__(logger_instance, extra or {})

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):  # pragma: no cover
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(  # pylint: disable=protected-access
                level, LogBraceString(msg, args), (), **kwargs
            )


logger = LogStyleAdapter(logging.getLogger(__name__))  # pylint: disable=invalid-name


def list_all_files(dirpath):
    """Get a list with relative paths for all files in the given directory."""

    def _recursively_list_all_files(root, dirpath):
        for path in dirpath.iterdir():
            if path.name.startswith("."):
                continue
            if path.is_dir():
                yield from _recursively_list_all_files(root, path)
                continue
            yield path.relative_to(root)

    return _recursively_list_all_files(dirpath, dirpath)


def delete_empty_directories(path):
    """Recursively remove empty directories."""
    for directory in sorted(path.glob("**"), key=lambda p: len(str(p)), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def correct_path_fat32(filename):
    """Replace illegal characters in FAT32 filenames with '_'."""
    return pathlib.Path(re.sub(r'[\\|:|*|?|"|<|>|\|]', "_", str(filename)))


def query_yes_no(question):  # pragma: no cover
    """Ask a yes/no question, yes being the default."""
    while 1:
        sys.stdout.write(question + " [Y/n]: ")
        choice = input().lower()
        if choice == "":
            return True
        try:
            return choice.lower() in ["true", "1", "t", "y", "yes"]
        except ValueError:
            sys.stdout.write("Valid answers: 'yes' or 'no'\n")

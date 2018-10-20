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
import os
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
        super(LogStyleAdapter, self).__init__(logger_instance, extra or {})

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):  # pragma: no cover
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(  # pylint: disable=protected-access
                level, LogBraceString(msg, args), (), **kwargs)


logger = LogStyleAdapter(  # pylint: disable=invalid-name
    logging.getLogger(__name__))


def makepath(path):
    """Convert relative path into absolute path."""
    return os.path.abspath(os.path.expanduser(path))


def list_all_files(path):
    """Get a list with relative paths for all files in the given path."""
    all_files = []
    for dirpath, dirs, filenames in os.walk(path):
        # Don't process hidden files
        dirs[:] = [d for d in dirs if not d[0] == '.']
        filenames = [f for f in filenames if not f[0] == '.']

        relpath = os.path.relpath(dirpath, path)
        for filename in filenames:
            all_files.append(os.path.normpath(os.path.join(relpath, filename)))
    return all_files


def ensure_directory_exists(path):
    """Ensure that the given path exists."""
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError:
        pass


def delete_empty_directories(path):
    """Recursively remove empty directories."""
    if not os.path.isdir(path):
        return False
    if all([delete_empty_directories(os.path.join(path, filename))
            for filename in os.listdir(path)]):
        logger.info("Removing {}".format(path))
        os.rmdir(path)
        return True
    return False


def correct_path_fat32(filename):
    """Replace illegal characters in FAT32 filenames with '_'."""
    return re.sub(r'[\\|:|*|?|"|<|>|\|]', '_', filename)


def query_yes_no(question):  # pragma: no cover
    """Ask a yes/no question, yes being the default."""
    while 1:
        sys.stdout.write(question + ' [Y/n]: ')
        choice = input().lower()
        if choice == '':
            return True
        try:
            return choice.lower() in ['true', '1', 't', 'y', 'yes']
        except ValueError:
            sys.stdout.write("Valid answers: 'yes' or 'no'\n")

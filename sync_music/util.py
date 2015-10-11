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

""" Utilities """

import os
import sys
import re


def makepath(path):
    """ Convert relative path into absolute path """
    return os.path.abspath(os.path.expanduser(path))


def list_all_files(path):
    """ Get a list with relative paths for all files in the given path """
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
    """ Ensure that the given path exists """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError:
        pass


def correct_path_fat32(filename):
    """ Replace illegal characters in FAT32 filenames with '_' """
    return re.sub(r'[\\|:|*|?|"|<|>|\|]', '_', filename)


def query_yes_no(question):  # pragma: no cover
    """ Ask a yes/no question, yes being the default """
    while 1:
        sys.stdout.write(question + ' [Y/n]: ')
        choice = input().lower()
        if choice == '':
            return True
        try:
            return choice.lower() in ['true', '1', 't', 'y', 'yes']
        except ValueError:
            sys.stdout.write("Valid answers: 'yes' or 'no'\n")

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

""" sync_music - Sync music library to external device """

__version__ = '0.2.0'

import os
import codecs
import traceback
import argparse
import configparser

from multiprocessing import Pool

from . import util
from .hashdb import HashDb
from .actions import Copy
from .actions import Skip
from .transcode import Transcode

ARGS = None
HASH_DB = None
ACTION_SKIP = None
ACTION_TRANSCODE = None
ACTION_COPY = None


def process_file(current_file):
    """ Process single file

    :param current_file: tuple: (file_index, total_files, in_filename, action)
    """
    file_index, total_files, in_filename, action = current_file
    out_filename = action.get_out_filename(in_filename)
    if out_filename is not None:
        out_filename = util.correct_path_fat32(out_filename)
        print("%4d/%4d: %s %s to %s" % (file_index, total_files, action.name,
                                        in_filename, out_filename))
    else:
        print("%4d/%4d: %s %s" % (file_index, total_files, action.name,
                                  in_filename))
        return None

    in_filepath = os.path.join(ARGS.audio_src, in_filename)
    out_filepath = os.path.join(ARGS.audio_dest, out_filename)

    # Calculate hash to see if the input file has changed
    hash_current = HASH_DB.get_hash(in_filepath)
    hash_database = None
    if in_filename in HASH_DB.database:
        hash_database = HASH_DB.database[in_filename][1]

    if (ARGS.force or hash_database is None or hash_database != hash_current
            or not os.path.exists(out_filepath)):
        util.ensure_directory_exists(os.path.dirname(out_filepath))
        try:
            action.execute(in_filepath, out_filepath)
        except IOError as err:
            print("Error: %s" % err)
            return
        return (in_filename, out_filename, hash_current)
    else:
        print("Skipping up to date file")
        return None


def get_file_action(in_filename):
    """ Determine the action for the given file """
    extension = os.path.splitext(in_filename)[1]
    if extension in ['.flac', '.ogg', '.mp3']:
        if ARGS.force_copy:
            return ACTION_COPY
        else:
            return ACTION_TRANSCODE
    elif in_filename.endswith('folder.jpg'):
        return ACTION_COPY
    else:
        return ACTION_SKIP


def clean_up_missing_files():
    """ Remove files in the destination, where the source file doesn't exist
        anymore
    """
    print("Cleaning up missing files")
    files = [(k, v[0]) for k, v in HASH_DB.database.items()]
    for in_filename, out_filename in files:
        in_filepath = os.path.join(ARGS.audio_src, in_filename)
        out_filepath = os.path.join(ARGS.audio_dest, out_filename)

        if not os.path.exists(in_filepath):
            if os.path.exists(out_filepath):
                result = util.query_yes_no(
                    "File %s does not exist, do you want to remove %s"
                    % (in_filename, out_filename))
                if result:
                    try:
                        os.remove(out_filepath)
                    except OSError as err:
                        print("Failed to remove file %s", err)
            if not os.path.exists(out_filepath):
                del HASH_DB.database[in_filename]


def sync_audio():
    """ Sync audio """
    # Create a list of all tracks ordered by their last modified time stamp
    files = [(f, get_file_action(f),
             os.path.getmtime(os.path.join(ARGS.audio_src, f)))
             for f in util.list_all_files(ARGS.audio_src)]
    files = [(index, len(files), f[0], f[1])
             for index, f in enumerate(files, 1)]
    if len(files) == 0:
        print("No input files")
        exit(1)

    # Cleanup files that does not exist any more
    clean_up_missing_files()

    # Do the work
    print("Starting actions")
    try:
        if ARGS.jobs == 1:
            # pool.map doesn't might not show all exceptions
            file_hashes = []
            for current_file in files:
                file_hashes.append(process_file(current_file))
        else:
            pool = Pool(processes=ARGS.jobs)
            file_hashes = pool.map(process_file, files)
    except:  # pylint: disable=W0702
        print(">>> traceback <<<")
        traceback.print_exc()
        print(">>> end of traceback <<<")

    # Store new hashes in the database
    for file_hash in file_hashes:
        if file_hash is not None:
            HASH_DB.database[file_hash[0]] = (file_hash[1], file_hash[2])


def sync_playlists():
    """ Sync m3u playlists """
    for dirpath, _, filenames in os.walk(ARGS.playlist_src):
        relpath = os.path.relpath(dirpath, ARGS.playlist_src)
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.m3u':
                try:
                    sync_playlist(os.path.normpath(
                                  os.path.join(relpath, filename)))
                except IOError as err:
                    print("Error: %s" % err)


def sync_playlist(filename):
    """ Sync playlist """
    print("Syncing playlist %s" % filename)
    srcpath = os.path.join(ARGS.playlist_src, filename)
    destpath = os.path.join(ARGS.audio_dest, filename)

    if os.path.exists(destpath):
        os.remove(destpath)

    # Copy file
    in_file = codecs.open(srcpath, 'r', encoding='windows-1252')
    out_file = codecs.open(destpath, 'w', encoding='windows-1252')
    for line in in_file.read().splitlines():
        if not line.startswith('#EXT'):
            in_filename = os.path.relpath(line, ARGS.audio_src)
            in_filename = in_filename
            if in_filename in HASH_DB.database:
                out_filename = HASH_DB.database[in_filename][0]
            else:
                print("Warning: File does not exist: %s" % in_filename)
                continue
            line = out_filename
            line = line.replace('/', '\\')
        line = line + '\r\n'
        out_file.write(line)
    in_file.close()
    out_file.close()


def load_settings():
    """ Load settings """
    # ArgumentParser 1: Get config file (disable help)
    config_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)
    config_parser.add_argument("-c", "--config-file",
                               help="Specify config file", metavar="FILE")
    args, remaining_argv = config_parser.parse_known_args()

    # Read default settings from config file
    if args.config_file is None:
        args.config_file = util.makepath('~/.sync_music')
    config = configparser.SafeConfigParser()
    config.read([args.config_file])
    try:
        defaults = dict(config.items("Defaults"))
    except configparser.NoSectionError:
        defaults = {}

    # ArgumentParser 2: Get rest of the arguments
    parser = argparse.ArgumentParser(parents=[config_parser])
    parser.set_defaults(**defaults)
    parser.add_argument('--audio-src', type=str, nargs='?',
                        help="Folder containing the audio sources")
    parser.add_argument('--audio-dest', type=str, nargs='?',
                        help="Target directory for converted audio files")
    parser.add_argument('--playlist-src', type=str, nargs='?',
                        help='Folder containing the source playlists')

    # Audio sync options
    parser.add_argument('-j', '--jobs', type=int, default=4,
                        help="Number of parallel jobs")
    parser.add_argument('-f', '--force', action="store_true",
                        help="Rerun action even if the file has not changed")
    parser.add_argument('-b', '--batch', action="store_true",
                        help="Batch mode, no user input")
    parser.add_argument('--force-copy', action="store_true",
                        help="Run copy action instead of transcode action")

    # Optons for action transcode
    parser.add_argument('--transcode-only', action="store_true",
                        help="Transcode but do not copy tags")
    parser.add_argument('--tags-only', action="store_true",
                        help="Do not transcode, "
                             "but copy tags for already existing files")
    parser.add_argument('--albumartist-hack', action="store_true",
                        help="Write album artist into composer field")
    parser.add_argument('--discnumber-hack', action="store_true",
                        help="Extend album field by disc number")
    parser.add_argument('--tracknumber-hack', action="store_true",
                        help="Remove track total from track number")

    # Parse
    settings = parser.parse_args(remaining_argv)

    # Check required arguments and make absolute paths
    try:
        paths = ['audio_src', 'audio_dest']
        if settings.playlist_src is not None:
            paths.append('playlist_src')
        settings_dict = vars(settings)
        for path in paths:
            settings_dict[path] = util.makepath(settings_dict[path])
            if not os.path.isdir(settings_dict[path]):
                raise IOError("%s is not a directory" % settings_dict[path])
    except AttributeError:
        parser.print_usage()
        parser.error("arguments audio-src and audio-dest are required and "
                     "need to be accessible folders")
    except IOError as err:
        parser.print_usage()
        parser.error(err)

    return settings


def main():
    """ sync_music - Sync music library to external device """
    print(__doc__)
    print("")
    global ARGS
    ARGS = load_settings()
    print("Settings:")
    print(" - audio-src:  %s" % ARGS.audio_src)
    print(" - audio-dest: %s" % ARGS.audio_dest)
    if ARGS.playlist_src:
        print(" - playlist-src: %s" % ARGS.playlist_src)
    if ARGS.force:
        print(" - force: Process also up to date files")
    if ARGS.force_copy:
        print(" - force-copy: Copy files only")
    print("")

    # Globals
    global ACTION_COPY
    ACTION_COPY = Copy()
    global ACTION_SKIP
    ACTION_SKIP = Skip()
    if not ARGS.force_copy:
        global ACTION_TRANSCODE
        ACTION_TRANSCODE = Transcode(
            transcode=not ARGS.tags_only,
            copy_tags=not ARGS.transcode_only,
            composer_hack=ARGS.albumartist_hack,
            discnumber_hack=ARGS.discnumber_hack,
            tracknumber_hack=ARGS.tracknumber_hack)
    global HASH_DB
    HASH_DB = HashDb(os.path.join(ARGS.audio_dest, 'sync_music.db'))

    if (not ARGS.batch and not util.query_yes_no("Do you want to continue?")):
        exit(1)

    HASH_DB.load()
    sync_audio()
    HASH_DB.store()
    if ARGS.playlist_src:
        sync_playlists()

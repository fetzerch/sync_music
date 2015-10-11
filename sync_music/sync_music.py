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

from multiprocessing import Pool  # pylint: disable=E0611

from . import util
from .hashdb import HashDb
from .actions import Copy
from .actions import Skip
from .transcode import Transcode


class SyncMusic():
    """ sync_music - Sync music library to external device """

    def __init__(self, args):
        """ Initialize SyncMusic """
        print(__doc__)
        print("")
        self._args = args
        self._hashdb = HashDb(os.path.join(args.audio_dest, 'sync_music.db'))
        print("Settings:")
        print(" - audio-src:  %s" % args.audio_src)
        print(" - audio-dest: %s" % args.audio_dest)
        if args.playlist_src:
            print(" - playlist-src: %s" % args.playlist_src)
        if args.force:
            print(" - force: Process also up to date files")
        if args.force_copy:
            print(" - force-copy: Copy files only")
        print("")
        self._action_copy = Copy()
        self._action_skip = Skip()
        self._action_transcode = Transcode(
            transcode=not self._args.tags_only,
            copy_tags=not self._args.transcode_only,
            composer_hack=self._args.albumartist_hack,
            discnumber_hack=self._args.discnumber_hack,
            tracknumber_hack=self._args.tracknumber_hack)

    def _process_file(self, current_file):
        """ Process single file

        :param current_file: tuple:
            (file_index, total_files, in_filename, action)
        """
        file_index, total_files, in_filename, action = current_file
        out_filename = action.get_out_filename(in_filename)
        if out_filename is not None:
            out_filename = util.correct_path_fat32(out_filename)
            print("%4d/%4d: %s %s to %s" %
                  (file_index, total_files, action.name,
                   in_filename, out_filename))
        else:
            print("%4d/%4d: %s %s" %
                  (file_index, total_files, action.name, in_filename))
            return None

        in_filepath = os.path.join(self._args.audio_src, in_filename)
        out_filepath = os.path.join(self._args.audio_dest, out_filename)

        # Calculate hash to see if the input file has changed
        hash_current = self._hashdb.get_hash(in_filepath)
        hash_database = None
        if in_filename in self._hashdb.database:
            hash_database = self._hashdb.database[in_filename][1]

        if (self._args.force or hash_database is None
                or hash_database != hash_current
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

    def _get_file_action(self, in_filename):
        """ Determine the action for the given file """
        extension = os.path.splitext(in_filename)[1]
        if extension in ['.flac', '.ogg', '.mp3']:
            if self._args.force_copy:
                return self._action_copy
            else:
                return self._action_transcode
        elif in_filename.endswith('folder.jpg'):
            return self._action_copy
        else:
            return self._action_skip

    def _clean_up_missing_files(self):
        """ Remove files in the destination, where the source file doesn't
            exist anymore
        """
        print("Cleaning up missing files")
        files = [(k, v[0]) for k, v in self._hashdb.database.items()]
        for in_filename, out_filename in files:
            in_filepath = os.path.join(self._args.audio_src, in_filename)
            out_filepath = os.path.join(self._args.audio_dest, out_filename)

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
                    del self._hashdb.database[in_filename]

    def sync_audio(self):
        """ Sync audio """
        self._hashdb.load()

        # Create a list of all tracks ordered by their last modified time stamp
        files = [(f, self._get_file_action(f),
                  os.path.getmtime(os.path.join(self._args.audio_src, f)))
                 for f in util.list_all_files(self._args.audio_src)]
        files = [(index, len(files), f[0], f[1])
                 for index, f in enumerate(files, 1)]
        if len(files) == 0:
            raise FileNotFoundError("No input files")

        # Cleanup files that does not exist any more
        self._clean_up_missing_files()

        # Do the work
        print("Starting actions")
        try:
            if self._args.jobs == 1:
                # pool.map doesn't might not show all exceptions
                file_hashes = []
                for current_file in files:
                    file_hashes.append(self._process_file(current_file))
            else:
                pool = Pool(processes=self._args.jobs)
                file_hashes = pool.map(self._process_file, files)
        except:  # pylint: disable=W0702
            print(">>> traceback <<<")
            traceback.print_exc()
            print(">>> end of traceback <<<")

        # Store new hashes in the database
        for file_hash in file_hashes:
            if file_hash is not None:
                self._hashdb.database[file_hash[0]] = \
                    (file_hash[1], file_hash[2])
        self._hashdb.store()

    def sync_playlists(self):
        """ Sync m3u playlists """
        for dirpath, _, filenames in os.walk(self._args.playlist_src):
            relpath = os.path.relpath(dirpath, self._args.playlist_src)
            for filename in filenames:
                if os.path.splitext(filename)[1] == '.m3u':
                    try:
                        self._sync_playlist(
                            os.path.normpath(
                                os.path.join(relpath, filename)))
                    except IOError as err:
                        print("Error: %s" % err)

    def _sync_playlist(self, filename):
        """ Sync playlist """
        print("Syncing playlist %s" % filename)
        srcpath = os.path.join(self._args.playlist_src, filename)
        destpath = os.path.join(self._args.audio_dest, filename)

        if os.path.exists(destpath):
            os.remove(destpath)

        # Copy file
        in_file = codecs.open(srcpath, 'r', encoding='windows-1252')
        out_file = codecs.open(destpath, 'w', encoding='windows-1252')
        for line in in_file.read().splitlines():
            if not line.startswith('#EXT'):
                in_filename = os.path.relpath(line, self._args.audio_src)
                if in_filename in self._hashdb.database:
                    out_filename = self._hashdb.database[in_filename][0]
                else:
                    print("Warning: File does not exist: %s" % in_filename)
                    continue
                line = out_filename
                line = line.replace('/', '\\')
            line = line + '\r\n'
            out_file.write(line)
        in_file.close()
        out_file.close()


def load_settings(arguments=None):
    """ Load settings """
    # ArgumentParser 1: Get config file (disable help)
    config_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)
    config_parser.add_argument("-c", "--config-file",
                               help="Specify config file", metavar="FILE")
    args, remaining_argv = config_parser.parse_known_args(arguments)

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
        if settings_dict['audio_dest']:
            util.ensure_directory_exists(
                util.makepath(settings_dict['audio_dest']))
        for path in paths:
            settings_dict[path] = util.makepath(settings_dict[path])
            if not os.path.isdir(settings_dict[path]):
                raise IOError("%s is not a directory" % settings_dict[path])
    except AttributeError:
        parser.error("arguments audio-src and audio-dest are required and "
                     "need to be accessible folders")
    except IOError as err:
        parser.error(err)

    return settings


def main():  # pragma: no cover
    """ sync_music - Sync music library to external device """
    args = load_settings()
    sync_music = SyncMusic(args)

    if not args.batch and not util.query_yes_no("Do you want to continue?"):
        exit(1)

    try:
        sync_music.sync_audio()
    except FileNotFoundError as err:
        print("Error: %s" % err)
        exit(1)

    if args.playlist_src:
        sync_music.sync_playlists()

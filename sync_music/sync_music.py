# music_sync - Sync music library to external device
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

import os
import codecs
import logging
import argparse
import configparser
import sys

from multiprocessing import Pool

import pbr.version

from . import util
from .hashdb import HashDb
from .actions import Copy
from .actions import Skip
from .transcode import Transcode

__version__ = pbr.version.VersionInfo('kasserver').release_string()

logger = util.LogStyleAdapter(  # pylint: disable=invalid-name
    logging.getLogger(__name__))


class SyncMusic():
    """sync_music - Sync music library to external device."""

    def __init__(self, args):
        """Initialize SyncMusic."""
        logger.info(__doc__)
        logger.info("")
        self._args = args
        self._hashdb = HashDb(os.path.join(args.audio_dest, 'sync_music.db'))
        logger.info("Settings:")
        logger.info(" - audio-src:  {}".format(args.audio_src))
        logger.info(" - audio-dest: {}".format(args.audio_dest))
        if args.playlist_src:
            logger.info(" - playlist-src: {}".format(args.playlist_src))
        logger.info(" - mode: {}".format(args.mode))
        logger.info("")
        self._action_copy = Copy()
        self._action_skip = Skip()
        self._action_transcode = Transcode(
            mode=self._args.mode,
            replaygain_preamp_gain=self._args.replaygain_preamp_gain,
            transcode=not self._args.disable_file_processing,
            copy_tags=not self._args.disable_tag_processing,
            albumartist_artist_hack=self._args.albumartist_artist_hack,
            albumartist_composer_hack=self._args.albumartist_composer_hack,
            discnumber_hack=self._args.discnumber_hack,
            tracknumber_hack=self._args.tracknumber_hack)

    def _process_file(self, current_file):
        """Process single file.

        :param current_file: tuple:
            (file_index, total_files, in_filename, action)
        """
        file_index, total_files, in_filename, action = current_file
        out_filename = action.get_out_filename(in_filename)
        if out_filename is not None:
            out_filename = util.correct_path_fat32(out_filename)
            logger.info("{:04}/{:04}: {} {} to {}",
                        file_index, total_files, action.name,
                        in_filename, out_filename)
        else:
            logger.info("{:04}/{:04}: {} {}",
                        file_index, total_files, action.name, in_filename)
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
                logger.error("Error: {}", err)
                return None
            return (in_filename, out_filename, hash_current)
        logger.info("Skipping up to date file")
        return None

    def _get_file_action(self, in_filename):
        """Determine the action for the given file."""
        extension = os.path.splitext(in_filename)[1]
        if extension in ['.flac', '.ogg', '.mp3']:
            if self._args.mode == 'copy':
                return self._action_copy
            return self._action_transcode
        if in_filename.endswith('folder.jpg'):
            return self._action_copy
        return self._action_skip

    def _clean_up_missing_files(self):
        """Remove files in the destination, where the source file doesn't
           exist anymore.
        """
        logger.info("Cleaning up missing files")
        files = [(k, v[0]) for k, v in self._hashdb.database.items()]
        for in_filename, out_filename in files:
            in_filepath = os.path.join(self._args.audio_src, in_filename)
            out_filepath = os.path.join(self._args.audio_dest, out_filename)

            if not os.path.exists(in_filepath):
                if os.path.exists(out_filepath):
                    if (self._args.batch or util.query_yes_no(
                            "File {} does not exist, do you want to remove {}"
                            .format(in_filename, out_filename))):
                        try:
                            os.remove(out_filepath)
                        except OSError as err:
                            logger.error("Error: Failed to remove file {}",
                                         err)
                if not os.path.exists(out_filepath):
                    del self._hashdb.database[in_filename]

    def _clean_up_empty_directories(self):
        """Remove empty directories in the destination."""
        logger.info("Cleaning up empty directories")
        util.delete_empty_directories(self._args.audio_dest)

    def sync_audio(self):
        """Sync audio."""
        self._hashdb.load()

        # Create a list of all tracks ordered by their last modified time stamp
        files = [(f, self._get_file_action(f),
                  os.path.getmtime(os.path.join(self._args.audio_src, f)))
                 for f in util.list_all_files(self._args.audio_src)]
        files = [(index, len(files), f[0], f[1])
                 for index, f in enumerate(files, 1)]
        if not files:
            raise FileNotFoundError("No input files")

        # Cleanup files that does not exist any more
        self._clean_up_missing_files()
        self._clean_up_empty_directories()

        # Do the work
        logger.info("Starting actions")
        try:
            if self._args.jobs == 1:
                # pool.map doesn't might not show all exceptions
                file_hashes = []
                for current_file in files:
                    file_hashes.append(self._process_file(current_file))
            else:
                pool = Pool(processes=self._args.jobs)
                file_hashes = pool.map(self._process_file, files)
        except:  # noqa, pylint: disable=bare-except
            logger.error(">>> traceback <<<")
            logger.exception("Exception")
            logger.error(">>> end of traceback <<<")

        # Store new hashes in the database
        for file_hash in file_hashes:
            if file_hash is not None:
                self._hashdb.database[file_hash[0]] = \
                    (file_hash[1], file_hash[2])
        self._hashdb.store()

    def sync_playlists(self):
        """Sync m3u playlists."""
        for dirpath, _, filenames in os.walk(self._args.playlist_src):
            relpath = os.path.relpath(dirpath, self._args.playlist_src)
            for filename in filenames:
                if os.path.splitext(filename)[1] == '.m3u':
                    try:
                        self._sync_playlist(
                            os.path.normpath(
                                os.path.join(relpath, filename)))
                    except IOError as err:
                        logger.error("Error: {}", err)

    def _sync_playlist(self, filename):
        """Sync playlist."""
        logger.info("Syncing playlist {}", filename)
        srcpath = os.path.join(self._args.playlist_src, filename)
        destpath = os.path.join(self._args.audio_dest, filename)

        if os.path.exists(destpath):
            os.remove(destpath)

        # Copy file
        in_file = codecs.open(srcpath, 'r', encoding='windows-1252')
        out_file = codecs.open(destpath, 'w', encoding='windows-1252')
        for line in in_file.read().splitlines():
            if not line.startswith('#EXT'):
                in_filename = line
                try:
                    while True:
                        if in_filename in self._hashdb.database:
                            line = self._hashdb.database[in_filename][0]
                            line = line.replace('/', '\\')
                            break
                        else:
                            in_filename = in_filename.split('/', 1)[1]
                except IndexError:
                    logger.warning("File does not exist: {}", line)
                    continue
            line = line + '\r\n'
            out_file.write(line)
        in_file.close()
        out_file.close()


def load_settings(arguments=None):  # pylint: disable=too-many-locals
    """Load settings."""
    # ArgumentParser 1: Get config file (disable help)
    config_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)
    config_parser.add_argument('-c', '--config-file',
                               help='specify config file', metavar='FILE')
    args, remaining_argv = config_parser.parse_known_args(arguments)

    # Read default settings from config file
    if args.config_file is None:
        args.config_file = util.makepath('~/.sync_music')
    config = configparser.ConfigParser()
    config.read([args.config_file])
    try:
        defaults = dict(config.items("Defaults"))
    except configparser.NoSectionError:
        defaults = {}

    # ArgumentParser 2: Get rest of the arguments
    parser = argparse.ArgumentParser(parents=[config_parser])
    parser.set_defaults(**defaults)
    parser.add_argument(
        '-v', '--version', action='version',
        version='%(prog)s {}'.format(__version__))
    parser.add_argument(
        '-b', '--batch', action='store_true', help="batch mode, no user input")
    parser.add_argument(
        '-o', '--logfile', type=str, default='./sync_music.log',
        help="write log output to file")

    parser_paths = parser.add_argument_group("Paths")
    parser_paths.add_argument(
        '--audio-src', type=str, required='audio_src' not in defaults,
        help="folder containing the audio sources")
    parser_paths.add_argument(
        '--audio-dest', type=str, required='audio_dest' not in defaults,
        help="target directory for converted files")
    parser_paths.add_argument(
        '--playlist-src', type=str,
        help='folder containing the source playlists')

    # Audio sync options
    parser_audio = parser.add_argument_group("Transcoding options")
    parser_audio.add_argument(
        '--mode',
        choices=['auto', 'transcode', 'replaygain', 'replaygain-album',
                 'copy'],
        default='auto',
        help="auto: copy MP3s, transcode others and adapt tags (default); "
             "transcode: transcode all files and adapt tags (slow); "
             "replaygain: transcode all files, apply ReplayGain track based "
             "normalization and adapt tags (slow), "
             "replaygain-album: transcode all files, apply ReplayGain album "
             "based normalization and adapt tags (slow), "
             "copy: copy all files, leave tags untouched (implies "
             "--disable-tag-processing)")
    parser_audio.add_argument(
        '--replaygain-preamp-gain', type=float,
        default=4.0,
        help="modify ReplayGain pre-amp gain if transcoded files are "
             "too quiet or too loud (default +4.0 as many players are "
             "calibrated for higher volume)")
    parser_audio.add_argument(
        '--disable-file-processing', action='store_true',
        help="disable processing files, update tags "
             "(if not explicitly disabled)")
    parser_audio.add_argument(
        '--disable-tag-processing', action='store_true',
        help="disable processing tags, update files "
             "(if not explicitly disabled)")
    parser_audio.add_argument(
        '-f', '--force', action='store_true',
        help="rerun action even if the source file has not changed")
    parser_audio.add_argument(
        '-j', '--jobs', type=int, default=4, help="number of parallel jobs")

    # Optons for action transcode
    parser_hacks = parser.add_argument_group(
        "Hacks", "Modify target files to work around player shortcomings")
    parser_hacks.add_argument(
        '--albumartist-artist-hack', action='store_true',
        help="write album artist into artist field")
    parser_hacks.add_argument(
        '--albumartist-composer-hack', action='store_true',
        help="write album artist into composer field")
    parser_hacks.add_argument(
        '--discnumber-hack', action='store_true',
        help="extend album field by disc number")
    parser_hacks.add_argument(
        '--tracknumber-hack', action='store_true',
        help="remove track total from track number")

    # Parse
    settings = parser.parse_args(remaining_argv)

    # Check required arguments and make absolute paths
    try:
        if settings.mode == 'copy' and (settings.albumartist_artist_hack or
                                        settings.albumartist_composer_hack or
                                        settings.discnumber_hack or
                                        settings.tracknumber_hack):
            parser.error("hacks cannot be used in copy mode")
        paths = ['audio_src', 'audio_dest']
        if settings.playlist_src is not None:
            paths.append('playlist_src')
        settings_dict = vars(settings)
        util.ensure_directory_exists(
            util.makepath(settings_dict['audio_dest']))
        for path in paths:
            settings_dict[path] = util.makepath(settings_dict[path])
            if not os.path.isdir(settings_dict[path]):
                raise IOError("{} is not a directory".format(
                    settings_dict[path]))
    except IOError as err:
        parser.error(err)

    return settings


def main():  # pragma: no cover
    """sync_music - Sync music library to external device."""
    args = load_settings()

    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)

    consolelogger = logging.StreamHandler(sys.stdout)
    consolelogger.setLevel(logging.INFO)
    consolelogger.setFormatter(logging.Formatter("{message}", style='{'))
    rootlogger.addHandler(consolelogger)

    if args.logfile:
        filelogger = logging.FileHandler(args.logfile, 'w')
        filelogger.setLevel(logging.INFO)
        filelogger.setFormatter(logging.Formatter(
            "{asctime} {levelname:8s} {message}", style='{'))
        rootlogger.addHandler(filelogger)

    sync_music = SyncMusic(args)

    if not args.batch and not util.query_yes_no("Do you want to continue?"):
        exit(1)

    try:
        sync_music.sync_audio()
    except FileNotFoundError as err:
        logger.critical("Failed to sync music {}", err)
        exit(1)

    if args.playlist_src:
        sync_music.sync_playlists()

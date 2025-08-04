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

import codecs
import collections
import logging
import argparse
import importlib.metadata
import configparser
import pathlib
import sys

from multiprocessing import Pool

from . import util
from .hashdb import HashDb
from .copy import Copy
from .metadata import ProcessMetadata
from .transcode import Transcode

__version__ = importlib.metadata.version("sync_music")

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


FileTask = collections.namedtuple(
    "FileTask", ["index", "total", "in_filename", "actions"]
)


class SyncMusic:
    """sync_music - Sync music library to external device."""

    def __init__(self, args):
        """Initialize SyncMusic."""
        logger.info(__doc__)
        logger.info("")
        self._args = args
        self._hashdb = HashDb(args.audio_dest / "sync_music.db")
        logger.info("Sync-Music Configuration:")
        logger.info(" - audio-src:    %s", args.audio_src)
        logger.info(" - audio-dest:   %s", args.audio_dest)
        if args.playlist_src:
            logger.info(" - playlist-src: %s", args.playlist_src)
        logger.info(" - mode:         %s", args.mode)
        logger.info("")
        self._action_copy = Copy()
        self._action_transcode = (
            Transcode(
                mode=self._args.mode,
                replaygain_preamp_gain=self._args.replaygain_preamp_gain,
            )
            if not self._args.disable_file_processing
            else None
        )
        self._action_processmetadata = (
            ProcessMetadata(
                copy_replaygain="replaygain" not in self._args.mode,
                albumartist_artist_hack=self._args.albumartist_artist_hack,
                albumartist_composer_hack=self._args.albumartist_composer_hack,
                artist_albumartist_hack=self._args.artist_albumartist_hack,
                discnumber_hack=self._args.discnumber_hack,
                tracknumber_hack=self._args.tracknumber_hack,
            )
            if not self._args.disable_tag_processing
            else None
        )

    def _process_file(self, file_task):
        """Process single file.

        :param current_file: FileTask(index, total, in_filename, actions)
        """
        out_filename = (
            util.correct_path_fat32(
                file_task.actions[0].get_out_filename(file_task.in_filename)
            )
            if file_task.actions
            else None
        )
        logger.info(
            "%04d/%04d: %s %s%s",
            file_task.index,
            file_task.total,
            (
                ", ".join(action.name for action in file_task.actions)
                if file_task.actions
                else "Skipping"
            ),
            file_task.in_filename,
            f" to {out_filename}" if out_filename else "",
        )
        if not file_task.actions:
            return None

        in_filepath = self._args.audio_src / file_task.in_filename
        out_filepath = self._args.audio_dest / out_filename

        # Calculate hash to see if the input file has changed
        hash_current = self._hashdb.calculate_hash(in_filepath)
        _, hash_database = self._hashdb.get_item(file_task.in_filename)

        if (
            self._args.force
            or hash_database is None
            or hash_database != hash_current
            or not out_filepath.exists()
        ):
            out_filepath.parent.mkdir(parents=True, exist_ok=True)

            try:
                for action in file_task.actions:
                    action.execute(in_filepath, out_filepath)
            except IOError as err:
                logger.error("Error: %s", err)
                return None

            # We can't store to the hashdb here because this is executed in multiple threads.

            return (file_task.in_filename, out_filename, hash_current)

        logger.info("Skipping up to date file")
        return None

    def _get_file_actions(self, in_filename):
        """Determine the action for the given file."""
        actions = []
        if in_filename.name.endswith("folder.jpg"):
            actions = [self._action_copy]
        elif (
            self._action_transcode
            and in_filename.suffix in self._action_transcode.get_supported_filetypes()
        ):
            if self._args.mode == "copy" or (
                self._args.mode == "auto"
                and in_filename.suffix == self._action_transcode.get_out_filetype()
            ):
                actions = [self._action_copy]
            else:
                actions = [self._action_transcode, self._action_processmetadata]
        return list(filter(None, actions))

    def _clean_up_missing_files(self):
        """Remove files in the destination, where the source file doesn't
        exist anymore. This can lead to empty directories, remove them as well.
        """
        logger.info("Cleaning up missing files")
        for in_filename, out_filename, _ in list(self._hashdb.get_items()):
            in_filepath = self._args.audio_src / in_filename
            out_filepath = self._args.audio_dest / out_filename

            if not in_filepath.exists():
                if out_filepath.exists():
                    if self._args.batch or util.query_yes_no(
                        f"File {in_filename} does not exist, do you want to remove {out_filename}"
                    ):
                        try:
                            out_filepath.unlink()
                        except OSError as err:
                            logger.error("Error: Failed to remove file %s", err)
                if not out_filepath.exists():
                    self._hashdb.delete_item(in_filename)

        logger.info("Cleaning up empty directories")
        util.delete_empty_directories(self._args.audio_dest)

    def sync_audio(self):
        """Sync audio."""
        with self._hashdb:
            files = list(util.list_all_files(self._args.audio_src))
            if not files:
                raise FileNotFoundError("No input files")

            # Cleanup files that do not exist any more and empty directories
            self._clean_up_missing_files()

            # Do the work
            logger.info("Starting actions")
            file_tasks = [
                FileTask(index, len(files), file, self._get_file_actions(file))
                for index, file in enumerate(files, 1)
            ]
            file_hashes = []
            try:
                if self._args.jobs == 1:
                    # pool.map doesn't might not show all exceptions
                    for file_task in file_tasks:
                        file_hashes.append(self._process_file(file_task))
                else:
                    with Pool(processes=self._args.jobs) as pool:
                        file_hashes = pool.map(self._process_file, file_tasks)

            except:  # pylint: disable=bare-except # noqa: E722
                logger.error(">>> traceback <<<")
                logger.exception("Exception")
                logger.error(">>> end of traceback <<<")

            for file_hash in filter(None, file_hashes):
                self._hashdb.add_item(*file_hash)

    def sync_playlists(self):
        """Sync m3u playlists."""
        with self._hashdb:
            for playlist_path in self._args.playlist_src.rglob("*.m3u"):
                try:
                    self._sync_playlist(
                        playlist_path.relative_to(self._args.playlist_src)
                    )
                except IOError as err:
                    logger.error("Error: %s", err)

    def _sync_playlist(self, filename):
        """Sync playlist."""
        logger.info("Syncing playlist %s", filename)
        srcpath = self._args.playlist_src / filename
        destpath = self._args.audio_dest / filename

        if destpath.exists():
            destpath.unlink()

        # Copy file
        with codecs.open(srcpath, "r", encoding="windows-1252") as in_file:
            with codecs.open(destpath, "w", encoding="windows-1252") as out_file:
                for line in in_file.read().splitlines():
                    if not line.startswith("#EXT"):
                        in_filename = line
                        try:
                            while True:
                                out_filename, _ = self._hashdb.get_item(in_filename)
                                if out_filename:
                                    line = out_filename.replace("/", "\\")
                                    break
                                in_filename = in_filename.split("/", 1)[1]
                        except IndexError:
                            logger.warning("File does not exist: %s", line)
                            continue
                    line = line + "\r\n"
                    out_file.write(line)


def load_settings(arguments=None):  # pylint: disable=too-many-locals
    """Load settings."""
    # ArgumentParser 1: Get config file (disable help)
    config_parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    config_parser.add_argument(
        "-c", "--config-file", help="specify config file", metavar="FILE"
    )
    args, remaining_argv = config_parser.parse_known_args(arguments)

    # Read default settings from config file
    if args.config_file is None:
        args.config_file = pathlib.Path("~/.sync_music")
    config = configparser.ConfigParser()
    config.read([args.config_file])
    try:
        defaults = dict(config.items("Defaults"))
    except configparser.NoSectionError:
        defaults = {}

    def _pathlib_dir(path):
        path = pathlib.Path(path)
        if path.is_dir():
            return path
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")

    # ArgumentParser 2: Get rest of the arguments
    parser = argparse.ArgumentParser(parents=[config_parser])
    parser.set_defaults(**defaults)
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-b", "--batch", action="store_true", help="batch mode, no user input"
    )
    parser.add_argument(
        "-o",
        "--logfile",
        type=pathlib.Path,
        default=pathlib.Path("sync_music.log"),
        help="write log output to file",
    )

    parser_paths = parser.add_argument_group("Paths")
    parser_paths.add_argument(
        "--audio-src",
        type=_pathlib_dir,
        required="audio_src" not in defaults,
        help="folder containing the audio sources",
    )
    parser_paths.add_argument(
        "--audio-dest",
        type=_pathlib_dir,
        required="audio_dest" not in defaults,
        help="target directory for converted files",
    )
    parser_paths.add_argument(
        "--playlist-src",
        type=_pathlib_dir,
        help="folder containing the source playlists",
    )

    # Audio sync options
    parser_audio = parser.add_argument_group("Transcoding options")
    parser_audio.add_argument(
        "--mode",
        choices=["auto", "transcode", "replaygain", "replaygain-album", "copy"],
        default="auto",
        help="auto: copy MP3s, transcode others and adapt tags (default); "
        "transcode: transcode all files and adapt tags (slow); "
        "replaygain: transcode all files, apply ReplayGain track based "
        "normalization and adapt tags (slow), "
        "replaygain-album: transcode all files, apply ReplayGain album "
        "based normalization and adapt tags (slow), "
        "copy: copy all files, leave tags untouched (implies "
        "--disable-tag-processing)",
    )
    parser_audio.add_argument(
        "--replaygain-preamp-gain",
        type=float,
        default=4.0,
        help="modify ReplayGain pre-amp gain if transcoded files are "
        "too quiet or too loud (default +4.0 as many players are "
        "calibrated for higher volume)",
    )
    parser_audio.add_argument(
        "--disable-file-processing",
        action="store_true",
        help="disable processing files, update tags (if not explicitly disabled)",
    )
    parser_audio.add_argument(
        "--disable-tag-processing",
        action="store_true",
        help="disable processing tags, update files (if not explicitly disabled)",
    )
    parser_audio.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="rerun action even if the source file has not changed",
    )
    parser_audio.add_argument(
        "-j", "--jobs", type=int, default=4, help="number of parallel jobs"
    )

    # Optons for action transcode
    parser_hacks = parser.add_argument_group(
        "Hacks", "Modify target files to work around player shortcomings"
    )
    parser_hacks.add_argument(
        "--albumartist-artist-hack",
        action="store_true",
        help="write album artist into artist field",
    )
    parser_hacks.add_argument(
        "--albumartist-composer-hack",
        action="store_true",
        help="write album artist into composer field",
    )
    parser_hacks.add_argument(
        "--artist-albumartist-hack",
        action="store_true",
        help="write artist into album artist field",
    )
    parser_hacks.add_argument(
        "--discnumber-hack",
        action="store_true",
        help="extend album field by disc number",
    )
    parser_hacks.add_argument(
        "--tracknumber-hack",
        action="store_true",
        help="remove track total from track number",
    )

    # Parse
    settings = parser.parse_args(remaining_argv)

    # Check required arguments
    if settings.mode == "copy" and (  # pylint: disable=too-many-boolean-expressions
        settings.albumartist_artist_hack
        or settings.albumartist_composer_hack
        or settings.artist_albumartist_hack
        or settings.discnumber_hack
        or settings.tracknumber_hack
    ):
        parser.error("hacks cannot be used in copy mode")

    return settings


def main():  # pragma: no cover
    """sync_music - Sync music library to external device."""
    args = load_settings()

    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)

    consolelogger = logging.StreamHandler(sys.stdout)
    consolelogger.setLevel(logging.INFO)
    consolelogger.setFormatter(logging.Formatter("{message}", style="{"))
    rootlogger.addHandler(consolelogger)

    if args.logfile:
        filelogger = logging.FileHandler(args.logfile, "w")
        filelogger.setLevel(logging.INFO)
        filelogger.setFormatter(
            logging.Formatter("{asctime} {levelname:8s} {message}", style="{")
        )
        rootlogger.addHandler(filelogger)

    try:
        sync_music = SyncMusic(args)
    except FileNotFoundError as err:
        logger.critical("Failed to initialize sync music %s", err)
        sys.exit(1)

    if not args.batch and not util.query_yes_no("Do you want to continue?"):
        sys.exit(1)

    try:
        sync_music.sync_audio()
    except FileNotFoundError as err:
        logger.critical("Failed to sync music %s", err)
        sys.exit(1)

    if args.playlist_src:
        sync_music.sync_playlists()

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

"""Transcode action."""

import logging
import re
import subprocess

from .replaygain import ReplayGain

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Transcode:
    """Transcodes audio files."""

    name = "Transcoding"
    _format = "mp3"
    _quality = "2"

    def __init__(
        self,
        mode="auto",
        replaygain_preamp_gain=0.0,
    ):
        self._mode = mode
        self._replaygain_preamp_gain = replaygain_preamp_gain

        logger.info(
            "Transcoding audio files with FFmpeg (%s):",
            self._get_ffmpeg_version(),
        )
        logger.info(
            " - Converting to '%s' in quality 'V%s'",
            self._format.upper(),
            self._quality,
        )
        if mode.startswith("replaygain"):
            logger.info(" - Performing ReplayGain normalization")
            if replaygain_preamp_gain != 0.0:
                logger.info(
                    " - Applying ReplayGain pre-amp gain '%s'", replaygain_preamp_gain
                )
        logger.info("")

    @staticmethod
    def get_supported_filetypes():
        """Determine supported file types."""
        return [".flac", ".ogg", ".mp3", ".m4a"]

    def get_out_filetype(self):
        """Determine output file type."""
        return f".{self._format}"

    def get_out_filename(self, path):
        """Determine output file path."""
        return path.with_suffix(self.get_out_filetype())

    def execute(self, in_filepath, out_filepath):
        """Transcode audio file."""
        logger.info("Transcoding from %s to %s", in_filepath, out_filepath)

        filter_arguments = []
        if self._mode.startswith("replaygain"):
            # The ffmpeg volume filter supports automatic volume normalization
            # based on the tags (-af volume=replaygain=track).
            # Unfortunately this doesn't seem to work with (some) ogg files
            # (for example tests/reference_data/audiofiles/withalltags.ogg).

            rp_info = ReplayGain.from_tags(
                in_filepath, album_gain=self._mode == "replaygain-album"
            )
            if rp_info:
                filter_arguments.extend(
                    [
                        "-af",
                        f"volume={rp_info.get_volume_multiplier(self._replaygain_preamp_gain)}",
                    ]
                )
            else:
                logger.warning("No ReplayGain info found: %s", in_filepath)
        try:
            subprocess.check_call(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-i",
                    str(in_filepath),
                ]
                + filter_arguments
                + [
                    "-map_chapters",
                    "-1",
                    "-map_metadata",
                    "-1",
                    "-vn",
                    "-q:a",
                    self._quality,
                    str(out_filepath),
                ]
            )
        except subprocess.CalledProcessError as err:
            raise IOError from err

    @staticmethod
    def _get_ffmpeg_version():
        """Get FFmpeg version."""
        output = subprocess.check_output(
            [
                "ffmpeg",
                "-version",
            ],
        )
        match = re.search(
            r"^ffmpeg version (\S+)",
            output.decode("utf-8"),
        )
        return match.group(1)

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

import collections
import logging
import re
import subprocess

import mutagen

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

ReplayGain = collections.namedtuple("ReplayGain", ["gain", "peak"])


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
        return [".flac", ".ogg", ".mp3"]

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

            rp_info = self.get_replaygain(
                in_filepath, album_gain=self._mode == "replaygain-album"
            )
            if rp_info:
                # Convert gain in dB to a multiplier (float)
                volume_multiplier = 10.0 ** (
                    (rp_info.gain + self._replaygain_preamp_gain) / 20
                )

                # Apply clipping protection
                volume_multiplier = min(volume_multiplier, 1.0 / rp_info.peak)

                filter_arguments.extend(
                    [
                        "-af",
                        f"volume={volume_multiplier}",
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

    @staticmethod
    def get_replaygain(in_filepath, album_gain=False):
        """Read ReplayGain info from tags."""
        in_file = mutagen.File(in_filepath)
        tag_prefix = "TXXX:" if isinstance(in_file.tags, mutagen.id3.ID3) else ""
        try:

            def _get_rp_value(tag):
                value = in_file.tags[f"{tag_prefix}{tag}"][0]
                return float(value.replace("dB", ""))

            if album_gain:
                return ReplayGain(
                    _get_rp_value("replaygain_album_gain"),
                    _get_rp_value("replaygain_album_peak"),
                )

            return ReplayGain(
                _get_rp_value("replaygain_track_gain"),
                _get_rp_value("replaygain_track_peak"),
            )
        except (TypeError, KeyError):
            return None

    @staticmethod
    def calculate_replaygain(in_filepath):
        """Calculate replaygain data for the given file."""
        output = subprocess.check_output(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-i",
                str(in_filepath),
                "-af",
                "ebur128=peak=sample:framelog=verbose",
                "-f",
                "null",
                "-",
            ],
            stderr=subprocess.STDOUT,
        )
        # Parse lines such as:
        #     I:         -11.3 LUFS
        #     Peak:        0.1 dBFS
        result = {
            key: float(value)
            for key, value in re.findall(
                r"(\w+):\s+([+-]?\d+\.\d+)\s+(?:\w+)\n",
                output.decode("utf-8"),
            )
        }
        # Convert gain to ReplayGain v2.0 reference of 18 LUFS, convert peak dBFS to float
        return ReplayGain(-(result["I"] + 18.0), 10 ** (result["Peak"] / 20.0))

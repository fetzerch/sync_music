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

import audiotools
import audiotools.replaygain
import mutagen

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

ReplayGain = collections.namedtuple("ReplayGain", ["gain", "peak"])


class Transcode:
    """Transcodes audio files."""

    name = "Transcoding"

    def __init__(
        self,
        mode="auto",
        replaygain_preamp_gain=0.0,
    ):
        self._format = audiotools.MP3Audio
        self._compression = "standard"

        logger.info("Transcoding settings:")
        logger.info(" - Audiotools %s", audiotools.VERSION)
        self._mode = mode

        logger.info(
            " - Converting to %s in quality %s",
            self._format.NAME,
            self._compression,
        )
        self._replaygain_preamp_gain = replaygain_preamp_gain
        if mode.startswith("replaygain") and replaygain_preamp_gain != 0.0:
            logger.info(
                " - Applying ReplayGain pre-amp gain %s", replaygain_preamp_gain
            )

        logger.info("")

    @staticmethod
    def get_supported_filetypes():
        """Determine supported file types."""
        return [".flac", ".ogg", ".mp3"]

    def get_out_filetype(self):
        """Determine output file type."""
        return f".{self._format.SUFFIX}"

    def get_out_filename(self, path):
        """Determine output file path."""
        return path.with_suffix(self.get_out_filetype())

    def execute(self, in_filepath, out_filepath):
        """Transcode audio file."""
        logger.info("Transcoding from %s to %s", in_filepath, out_filepath)
        try:
            if not self._mode.startswith("replaygain"):
                audiotools.open(str(in_filepath)).convert(
                    str(out_filepath), self._format, compression=self._compression
                )
            else:
                in_file = audiotools.open(str(in_filepath))
                rp_info = self._get_replaygain(in_filepath)
                if rp_info:
                    pcmreader = audiotools.replaygain.ReplayGainReader(
                        in_file.to_pcm(),
                        rp_info.gain + self._replaygain_preamp_gain,
                        rp_info.peak,
                    )
                    self._format.from_pcm(
                        str(out_filepath), pcmreader, compression=self._compression
                    )
                else:
                    logger.warning("No ReplayGain info found %s", in_filepath)
                    audiotools.open(str(in_filepath)).convert(
                        str(out_filepath), self._format, compression=self._compression
                    )
        except (audiotools.EncodingError, audiotools.UnsupportedFile) as err:
            raise IOError(f"Failed to transcode file {in_filepath}: {err}") from err

    def _get_replaygain(self, in_filepath):
        """Read ReplayGain info from tags."""
        in_file = mutagen.File(in_filepath)
        tag_prefix = "TXXX:" if isinstance(in_file, mutagen.mp3.MP3) else ""
        try:

            def _get_value(tag):
                value = in_file.tags[f"{tag_prefix}{tag}"][0]
                return float(value.replace("dB", ""))

            if self._mode == "replaygain-album":
                return ReplayGain(
                    _get_value("replaygain_album_gain"),
                    _get_value("replaygain_album_peak"),
                )

            return ReplayGain(
                _get_value("replaygain_track_gain"), _get_value("replaygain_track_peak")
            )
        except (TypeError, KeyError):
            return None

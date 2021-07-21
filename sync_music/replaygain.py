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

"""ReplayGain utils."""

import argparse
import logging
import math
import pathlib
import re
import subprocess
import sys

import mutagen

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ReplayGain:
    """ReplayGain information"""

    def __init__(self, gain, peak):
        self.gain = gain
        self.peak = peak

    def __str__(self):  # pragma: no cover
        return (
            f"ReplayGain(gain={self.gain:.1f} dB, "
            f"peak={self.peak:.6f} ({math.log10(self.peak) * 20.0:.1f} dBFS), "
            f"volume_multiplier={self.get_volume_multiplier():.6f})"
        )

    def get_volume_multiplier(self, preamp_gain=0):
        """Calculate volume multiplier based on ReplayGain information."""
        # Convert gain in dB to a multiplier (float)
        volume_multiplier = 10.0 ** ((self.gain + preamp_gain) / 20)

        # Apply clipping protection
        if self.peak:
            volume_multiplier = min(volume_multiplier, 1.0 / self.peak)

        return volume_multiplier

    @classmethod
    def from_tags(cls, in_filepath, album_gain=False):
        """Read ReplayGain info from tags."""
        in_file = mutagen.File(in_filepath)
        tag_type = "album" if album_gain else "track"
        try:
            if isinstance(in_file, mutagen.mp3.MP3):
                gain = in_file.tags[f"TXXX:replaygain_{tag_type}_gain"].text[0]
                peak = in_file.tags[f"TXXX:replaygain_{tag_type}_peak"].text[0]
            elif isinstance(in_file, (mutagen.flac.FLAC, mutagen.oggvorbis.OggVorbis)):
                gain = in_file.tags[f"replaygain_{tag_type}_gain"][0]
                peak = in_file.tags[f"replaygain_{tag_type}_peak"][0]
            else:
                return None
            return cls(float(gain.replace("dB", "")), float(peak))
        except (TypeError, KeyError):
            return None

    @classmethod
    def from_audiotrack(cls, in_filepath):
        """Calculate replaygain data from an audio file."""
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
        try:
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
            return cls(-(result["I"] + 18.0), math.pow(10, result["Peak"] / 20.0))
        except (TypeError, KeyError):
            return None


def main():  # pragma: no cover
    """replaygain - Get ReplayGain v2 info (EBU R-128, -18 LUFS)."""

    consolelogger = logging.StreamHandler(sys.stdout)
    consolelogger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        type=pathlib.Path,
        nargs="+",
        help="calculate ReplayGain info for file",
    )
    args = parser.parse_args()

    for in_file in args.file:
        print(f"{str(in_file)}: Audio: {ReplayGain.from_audiotrack(in_file)}")
        print(f"{str(in_file)}: Tags:  {ReplayGain.from_tags(in_file)}")

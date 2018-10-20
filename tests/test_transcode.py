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

"""Tests the transcoding implementation."""

import os
import shutil

import pytest

from sync_music.sync_music import Transcode


class TestTranscode():
    """Tests the transcoding implementation."""

    in_filename_flac = 'withtags.flac'
    in_filename_flacall = 'withalltags.flac'
    in_filename_flacempty = 'stripped.flac'
    in_filename_ogg = 'withtags.ogg'
    in_filename_oggall = 'withalltags.ogg'
    in_filename_oggempty = 'stripped.ogg'
    in_filename_mp3 = 'withtags.mp3'
    in_filename_mp3all = 'withalltags.mp3'
    in_filename_mp3empty = 'stripped.mp3'
    in_filename_aiff = 'withtags.aiff'
    out_filename = 'withtags.mp3'
    img_filename = 'folder.jpg'
    input_path = 'tests/reference_data/audiofiles'
    output_path = None

    @pytest.fixture(autouse=True)
    def init_output_path(self, tmpdir):
        """Setup temporary output directory."""
        self.output_path = str(tmpdir)

    def test_filename(self):
        """Tests retrieving the output file name."""
        transcode = Transcode()
        out_filename = transcode.get_out_filename(self.in_filename_flac)
        assert self.out_filename == out_filename

    def execute_transcode(self, transcode, in_filename=in_filename_flac,
                          out_filename=out_filename):
        """Helper method to run transcoding tests."""
        transcode.execute(
            os.path.join(self.input_path, in_filename),
            os.path.join(self.output_path, out_filename))

    def test_transcode_default(self):
        """Test transcoding with default options."""
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_flac)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_flacall)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_flacempty)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_ogg)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_oggall)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_oggempty)

    def test_transcode_copy(self):
        """Tests transcoding with copying instead of transcoding."""
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_mp3)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_mp3all)
        self.execute_transcode(Transcode(),
                               in_filename=self.in_filename_mp3empty)

    def test_transcode_transcode(self):
        """Tests transcoding with forced transcode."""
        self.execute_transcode(Transcode(mode='transcode'),
                               in_filename=self.in_filename_mp3)

    def test_transcode_replaygain(self):
        """Tests transcoding with ReplayGain (track based)."""
        self.execute_transcode(Transcode(mode='replaygain'),
                               in_filename=self.in_filename_mp3all)
        self.execute_transcode(Transcode(mode='replaygain'),
                               in_filename=self.in_filename_mp3)

    def test_transcode_replaygainalbum(self):
        """Tests transcoding with ReplayGain (album based)."""
        self.execute_transcode(Transcode(mode='replaygain-album',
                                         replaygain_preamp_gain=10.0),
                               in_filename=self.in_filename_mp3)

    def test_transcode_folderimage(self):
        """Tests transcoding without folder image."""
        # Copy input file to a folder without folder.jpg (output folder)
        in_filename = os.path.join(self.output_path, self.in_filename_flac)
        shutil.copy(
            os.path.join(self.input_path, self.in_filename_flac),
            in_filename)
        self.execute_transcode(Transcode(), in_filename=in_filename)

    def test_transcode_artist_hack(self):
        """Tests transcoding with albumartist to artist hack enabled."""
        self.execute_transcode(Transcode(albumartist_artist_hack=True))
        self.execute_transcode(Transcode(albumartist_artist_hack=True),
                               in_filename=self.in_filename_mp3empty)

    def test_transcode_composer_hack(self):
        """Tests transcoding with albumartist to composer hack enabled."""
        self.execute_transcode(Transcode(albumartist_composer_hack=True))
        self.execute_transcode(Transcode(albumartist_composer_hack=True),
                               in_filename=self.in_filename_mp3empty)

    def test_transcode_discnumber_hack(self):
        """Tests transcoding with disc number hack enabled."""
        self.execute_transcode(Transcode(discnumber_hack=True))
        self.execute_transcode(Transcode(discnumber_hack=True),
                               in_filename=self.in_filename_mp3all)

    def test_transcode_tracknumber_hack(self):
        """Tests transcoding with track number hack enabled."""
        self.execute_transcode(Transcode(tracknumber_hack=True))
        self.execute_transcode(Transcode(tracknumber_hack=True),
                               in_filename=self.in_filename_mp3empty)
        self.execute_transcode(Transcode(tracknumber_hack=True),
                               in_filename='brokentag_tracknumber.mp3')

    def test_transcodeerror_transcode(self):
        """Tests transcoding failure."""
        # IOError is raised on audiotools.EncodingError. The easiest way that
        # leads into this exception is writing to a non writable path.
        with pytest.raises(IOError):
            self.execute_transcode(Transcode(), out_filename='/')

    def test_transcodeerror_copytags(self):
        """Tests copying tag failure."""
        # Copy tags expects the output file to be an MP3 file.
        # Don't transcode as this would rewrite the output file.
        shutil.copy(
            os.path.join(self.input_path, self.img_filename),
            os.path.join(self.output_path, self.out_filename))
        with pytest.raises(IOError):
            self.execute_transcode(Transcode(mode='copy'))

    def test_transcodingerror_format(self):
        """Tests transcoding a non supported format."""
        with pytest.raises(IOError):
            self.execute_transcode(Transcode(),
                                   in_filename=self.in_filename_aiff)

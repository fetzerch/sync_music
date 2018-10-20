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

"""Tests sync_music."""

import os
import shutil

from unittest import mock

import pytest

from sync_music.sync_music import SyncMusic
from sync_music.sync_music import load_settings
from sync_music.util import list_all_files


class TestSyncMusicSettings:
    """Tests sync_music load_settings function."""

    @staticmethod
    def test_noparams():
        """Tests loading of settings without parameters."""
        with pytest.raises(SystemExit):
            load_settings('')

    @staticmethod
    def test_nonexistent():
        """Tests loading of settings with incorrect paths."""
        argv = ['--audio-src', '/proc/nonexistingpath',
                '--audio-dest', '/proc/nonexistingpath']
        with pytest.raises(SystemExit):
            load_settings(argv)

    @staticmethod
    def test_forcecopy_with_hacks():
        """Tests loading of settings with force copy and hacks."""
        argv = ['--audio-src', '/tmp',
                '--audio-dest', '/tmp',
                '--mode=copy', '--albumartist-artist-hack']
        with pytest.raises(SystemExit):
            load_settings(argv)

    @staticmethod
    def test_configfile():
        """Tests loading of settings within config file."""
        filename = '/tmp/sync_music.cfg'
        argv = ['-c', filename]
        with open(filename, 'w') as configfile:
            configfile.write("[Defaults]\n")
            configfile.write("audio_src=/tmp\n")
            configfile.write("audio_dest=/tmp\n")
        try:
            load_settings(argv)
        finally:
            os.remove(filename)


class TestSyncMusicFiles():
    """Tests sync_music audio conversion."""

    input_path = 'tests/reference_data/regular'
    output_path = None

    output_files = [
        'stripped_flac.mp3', 'stripped_mp3.mp3', 'stripped_ogg.mp3',
        'withtags_flac.mp3', 'withtags_mp3.mp3', 'withtags_ogg.mp3',
        'sync_music.db', 'folder.jpg', 'dir/folder.jpg'
    ]

    @pytest.fixture(autouse=True)
    def init_output_path(self, tmpdir):
        """Setup temporary output directory."""
        self.output_path = str(tmpdir)

    def _execute_sync_music(self, input_path=input_path, output_files=None,
                            arguments=None, jobs=None):
        """Helper method to run sync_music tests."""
        if output_files is None:
            output_files = self.output_files
        argv = [] if arguments is None else arguments
        argv += ['--audio-src', input_path,
                 '--audio-dest', self.output_path]
        args = load_settings(argv)
        args.jobs = 1 if jobs is None else jobs
        sync_music = SyncMusic(args)
        sync_music.sync_audio()
        assert set(list_all_files(self.output_path)) == set(output_files)

    def test_emptyfolder(self):
        """Test empty input folder."""
        with pytest.raises(FileNotFoundError):
            self._execute_sync_music(self.output_path, [])

    def test_filenames_utf8(self):
        """Test UTF-8 input file names."""
        input_path = 'tests/reference_data/filenames_utf8'
        output_files = ['test_äöüß.mp3', 'sync_music.db']
        self._execute_sync_music(input_path, output_files)

    def test_filenames_fat32(self):
        """Test input file names incompatible with FAT32."""
        input_path = 'tests/reference_data/filenames_fat32'
        output_files = ['A___A.mp3', 'B___B.mp3', 'C___C.mp3', 'D___D.mp3',
                        'E___E.mp3', 'F___F.mp3', 'G___G.mp3', 'H___H.mp3',
                        'sync_music.db']
        self._execute_sync_music(input_path, output_files)

    def test_reference_default(self):
        """Test reference folder with default arguements."""
        self._execute_sync_music()

    def test_reference_withdatabase(self):
        """Test reference folder with default arguements (2 runs)."""
        self._execute_sync_music()
        self._execute_sync_music()

    def test_reference_cleanup(self):
        """Test reference folder with cleanup (file removed from input)."""
        input_path = 'tests/reference_data/regular_cleanup'
        output_files = self.output_files

        # Run a regular sync
        self._execute_sync_music()

        # First run: don't delete files
        def query_no(_):
            """Replacement for sync_music.util.query_yes_no."""
            return False
        with mock.patch('sync_music.util.query_yes_no', side_effect=query_no):
            self._execute_sync_music(input_path, output_files)

        # Delete a file also in output directory (to check double deletion)
        os.remove(os.path.join(self.output_path, 'withtags_ogg.mp3'))

        # Simulate OSError by creating a folder (that can't be removed)
        os.remove(os.path.join(self.output_path, 'withtags_mp3.mp3'))
        os.mkdir(os.path.join(self.output_path, 'withtags_mp3.mp3'))

        # Second run: delete files
        def query_yes(_):
            """Replacement for sync_music.util.query_yes_no."""
            return True
        output_files = [
            'stripped_mp3.mp3', 'sync_music.db'
        ]
        with mock.patch('sync_music.util.query_yes_no', side_effect=query_yes):
            self._execute_sync_music(input_path, output_files)

    def test_reference_multiprocessing(self):
        """Test reference folder with parallel jobs."""
        self._execute_sync_music(jobs=4)

    def test_reference_forcecopy(self):
        """Test reference folder with force copy."""
        output_files = [
            'stripped_flac.flac', 'stripped_mp3.mp3', 'stripped_ogg.ogg',
            'withtags_flac.flac', 'withtags_mp3.mp3', 'withtags_ogg.ogg',
            'sync_music.db', 'folder.jpg', 'dir/folder.jpg'
        ]
        self._execute_sync_music(output_files=output_files,
                                 arguments=['--mode=copy'])

    def test_reference_transcodeonly(self):
        """Test reference folder with tag processing only."""
        self._execute_sync_music()
        self._execute_sync_music(arguments=['-f', '--disable-file-processing'])

    def test_reference_tagsonly(self):
        """Test reference folder with file processing only."""
        self._execute_sync_music(arguments=['--disable-tag-processing'])

    def test_reference_hacks(self):
        """Test reference folder with hacks."""
        self._execute_sync_music(arguments=[
            '--albumartist-artist-hack', '--albumartist-composer-hack',
            '--discnumber-hack', '--tracknumber-hack'
        ])

    def test_reference_ioerror(self, mocker):
        """Test reference folder with mocked IOError."""
        mocker.patch('sync_music.transcode.Transcode.execute',
                     side_effect=IOError('Mocked exception'))
        mocker.patch('sync_music.actions.Copy.execute',
                     side_effect=IOError('Mocked exception'))
        self._execute_sync_music(output_files=['sync_music.db'])

    def test_reference_exception(self, mocker):
        """Test reference folder with mocked random exception."""
        mocker.patch('sync_music.transcode.Transcode.execute',
                     side_effect=Exception('Mocked exception'))
        mocker.patch('sync_music.actions.Copy.execute',
                     side_effect=Exception('Mocked exception'))
        self._execute_sync_music(output_files=['sync_music.db'])


class TestSyncMusicPlaylists():
    """Tests sync_music playlist conversion."""

    input_path = 'tests/reference_data/regular'
    output_path = None
    playlist_path = 'tests/reference_data/playlists'

    @pytest.fixture(autouse=True)
    def init_output_path(self, tmpdir):
        """Setup temporary output directory."""
        self.output_path = str(tmpdir)

    def _execute_sync_music(self, playlist_path=playlist_path):
        """Helper method to run sync_music tests."""
        argv = ['--audio-src', self.input_path,
                '--audio-dest', self.output_path,
                '--playlist-src', playlist_path]
        args = load_settings(argv)
        sync_music = SyncMusic(args)
        sync_music.sync_audio()
        sync_music.sync_playlists()

    def test_playlists(self):
        """Tests playlist generation."""
        self._execute_sync_music()

    def test_playlists_exists(self):
        """Tests playlist generation when playlist exists."""
        shutil.copy('tests/reference_data/playlists/normal.m3u',
                    os.path.join(self.output_path, 'normal.m3u'))
        self._execute_sync_music()

    def test_playlists_ioerror(self):
        """Tests playlist generation with playlist that can't be opened."""
        os.symlink('/dev/null', os.path.join(self.output_path, 'null.m3u'))
        self._execute_sync_music(self.output_path)

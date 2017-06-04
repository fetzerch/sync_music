# sync_music - Sync music library to external device
# Copyright (C) 2015 Christian Fetzer
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

"""Packaging for sync_music."""

import io
import os
import re

from setuptools import setup

from sync_music.__init__ import verify_interpreter_version
verify_interpreter_version()


def read(*names, **kwargs):
    """Read file relative to the directory where this file is located."""
    return io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


def find_version(*file_paths):
    """Get version number from file."""
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


VERSION = find_version('sync_music/sync_music.py')
URL = 'https://github.com/fetzerch/sync_music'
setup(
    name='sync_music',
    version=VERSION,
    license='GPLv2+',
    description='Sync music library to external devices',
    long_description=read('README.rst'),
    author='Christian Fetzer',
    author_email='fetzer.ch@gmail.com',
    url=URL,
    download_url='{}/archive/sync_music-{}.tar.gz'.format(URL, VERSION),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: '
        'GNU General Public License v2 or later (GPLv2+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
    ],
    keywords='music synchronization',
    packages=['sync_music'],
    entry_points={
        "console_scripts": ['sync_music = sync_music.sync_music:main']
    },
    install_requires=[
        'mutagen>=1.29',
        'audiotools>=3.0',
    ],
    dependency_links=[
        'https://github.com/tuffy/python-audio-tools/tarball/v3.0'
        '#egg=audiotools-3.0'
    ],
)

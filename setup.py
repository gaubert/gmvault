'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2012>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
from setuptools import setup, find_packages
version = '1.0-beta'
README = os.path.join(os.path.dirname(__file__), './README.md')
if os.path.exists(README):
	long_description = open(README).read() + 'nn'
else:
   long_description = "Gmvault"

setup(name='gmvault',
      version=version,
      description=("gmvault - Backup and restore your Gmail emails"),
      long_description=long_description,
      classifiers=[
        "Programming Language :: Python",
        ("Topic :: Util :: Libraries :: Python Modules"),
        ],
      keywords='gmail, email, backup, gmail backup, imap',
      author='Guillaume Aubert',
      author_email='guillaume.aubert@gmail.com',
      url='www.gmvault.org',
      license='GPLv3',
      packages=['gmv'],
      package_dir = {'gmv':'./src/gmv'},
      scripts=['./etc/scripts/gmvault'],
      install_requires=['Logbook==0.3', 'IMAPClient==0.8.1','gdata==2.0.17']
      )

"""
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
"""

import os
import sys
import re
from setuptools import setup


# function to find the version in gmv_cmd
def find_version(path):
    with open(path) as f:
        for line in f:
            match = re.match(r'GMVAULT_VERSION\s=\s"(?P<version>[\d.]+)"', line)
            if match is not None:
                version = match.groupdict().get('version')
                return version

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % path)

top_dir = os.path.dirname(os.path.realpath(__file__))

utils_path = os.path.join(top_dir, 'src/gmv/gmvault_utils.py')
print("PATH = %s\n" % utils_path)

try:
    version = find_version(utils_path)
except Exception as e:
    print(str(e))
    sys.exit(1)
else:
    print("Gmvault version = %s\n" % version)

readme_path = os.path.join(top_dir, 'README.md')
try:
    with open(readme_path) as f:
        long_description = f.read() + '\n\n'
except IOError as e:
    long_description = 'Gmvault'

setup(name='gmvault',
      version=version,
      description=("Tool to backup and restore your Gmail emails at will. http://www.gmvault.org for more info"),
      long_description=long_description,
      classifiers=[
          "Programming Language :: Python",
          "License :: OSI Approved :: GNU Affero General Public License v3",
          "Topic :: Communications :: Email",
          "Topic :: Communications :: Email :: Post-Office :: IMAP",
      ],
      keywords='gmail, email, backup, gmail backup, imap',
      author='Guillaume Aubert',
      author_email='guillaume.aubert@gmail.com',
      url='http://www.gmvault.org',
      license='AGPLv3',
      packages=['gmv', 'gmv.conf', 'gmv.conf.utils'],
      package_dir = {'gmv': './src/gmv'},
      scripts=['./etc/scripts/gmvault'],
      package_data={'': ['release-note.txt']},
      include_package_data=True,
      # install_requires=['argparse', 'Logbook==0.4.1', 'IMAPClient==0.9.2','gdata==2.0.17']
      install_requires=['argparse', 'Logbook==0.10.1', 'IMAPClient==0.13', 'chardet==2.3.0']
      )

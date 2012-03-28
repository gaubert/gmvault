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
version = '0.5'
README = os.path.join(os.path.dirname(__file__), '../README')
print(README)
long_description = open(README).read() + 'nn'
setup(name='gmvault',
      version=version,
      description=("gmvault - Backup and restore your Gmail emails"),
      long_description=long_description,
      classifiers=[
        "Programming Language :: Python",
        ("Topic :: Util :: Libraries :: Python Modules"),
        ],
      keywords='configuration, resources',
      author='Guillaume Aubert',
      author_email='guillaume.aubert@gmail.com',
      url='www.gmvault.org',
      license='Apache 2.0',
      packages=['gmv'],
      #package_data=dict(gmvault=['']),
      #package_data={'org.ctbto.conf': ['tests/test.config','tests/foo.config','tests/rn.par','tests/rn1.par']},
      #data_files=[('/tmp/py-tests',['/home/aubert/dev/src-reps/java-balivernes/RNpicker/dists/conf-dist/tests/foo.config','/home/aubert/dev/src-reps/java-balivernes/RNpicker/dists/conf-dist/tests/test.config'])],
      install_requires=['Logbook>=0.3', 'IMAPClient']
      )

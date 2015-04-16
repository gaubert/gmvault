"""
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import sys
import re

def find_version(path):
    with open(path) as f:
        for line in f:
            index = line.find('GMVAULT_VERSION="')
            if index > -1:
                print(line[index+17:-2])
                return line[index+17:-2]

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % (path))

VERSION_PATTERN = r'###GMVAULTVERSION###' 
VERSION_RE      = re.compile(VERSION_PATTERN)

def add_version(a_input, a_output, a_version):
    with open(a_input, 'r') as f_in:
        with open(a_output, 'w') as f_out:
            for line in f_in:
                line = VERSION_RE.sub(a_version, line)
                f_out.write(line)

if __name__ == '__main__':

    if len(sys.argv) < 4:
        print("Error: need more parameters for %s." % (sys.argv[0]))
        print("Usage: add_version.py input_path output_path version.")
        exit(-1)

    #print("path = %s\n" % (sys.argv[1]))

    add_version(sys.argv[1], sys.argv[2], sys.argv[3])

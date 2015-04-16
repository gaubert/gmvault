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


def find_version(path):
    with open(path) as f:
        for line in f:
            index = line.find('GMVAULT_VERSION = "')
            if index > -1:
                print(line[index+19:-2])
                res = line[index+19:-2]
                return res.strip()

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % path)

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print("Error: Need the path to gmv_cmd.py")
        exit(-1)

    #print("path = %s\n" % (sys.argv[1]))

    find_version(sys.argv[1])

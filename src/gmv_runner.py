'''
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

'''
import os
import sys
import gmv.gmv_cmd

# pyinstaller doesn't accept to path -u option with a spec 
# but it is needed on windows to have unbuffered IOs
# instead need to programatically reopen all stdin,err,out without buffering
os.environ['PYTHONUNBUFFERED'] = "1" 
sys.stdout = os.fdopen(sys.stdout.fileno(), "a+", 0)
sys.stdin = os.fdopen(sys.stdin.fileno(), "a+", 0)
sys.stderr = os.fdopen(sys.stderr.fileno(), "a+", 0)

gmv.gmv_cmd.bootstrap_run()

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
import sys
import os

import logbook


class StdoutHandler(logbook.StreamHandler):
    """A handler that writes to what is currently at stdout. At the first
glace this appears to just be a :class:`StreamHandler` with the stream
set to :data:`sys.stdout` but there is a difference: if the handler is
created globally and :data:`sys.stdout` changes later, this handler will
point to the current `stdout`, whereas a stream handler would still
point to the old one.
"""

    def __init__(self, level=logbook.base.NOTSET, format_string=None, a_filter = None, bubble=False): 
        logbook.StreamHandler.__init__(self, logbook.base._missing, level, format_string,
                               None, a_filter, bubble)

    @property
    def stream(self):
        return sys.stdout

#default log file
DEFAULT_LOG = "%s/gmvault.log" % (os.getenv("HOME", "."))

class LoggerFactory(object):
    '''
       My Logger Factory
    '''
    
    @classmethod
    def get_logger(cls, name):
        """
          Simply return a logger
        """
        return logbook.Logger(name)
    
    
    @classmethod
    def setup_simple_stderr_handler(cls):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = logbook.StderrHandler(format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    @classmethod
    def setup_simple_stdout_handler(cls):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = StdoutHandler(format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    @classmethod
    def setup_simple_file_handler(cls, file_path):
        """
           Push a file handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = logbook.FileHandler(file_path, format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
        
    @classmethod
    def setup_cli_app_handler(cls, activate_log_file=False, console_level= 'CRITICAL', file_path=DEFAULT_LOG, log_file_level = 'DEBUG'):
        """
           Setup a handler for communicating with the user and still log everything in a logfile
        """
        null_handler      = logbook.NullHandler()
        
        out_handler       = StdoutHandler(format_string='{record.message}', level = console_level , bubble = False)
        
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        
        # add output Handler
        out_handler.push_application() 
        
        # add file Handler
        if activate_log_file:
            
            file_handler      = logbook.FileHandler(file_path, mode='w', format_string='[{record.time:%Y-%m-%d %H:%M}]:{record.level_name}:{record.channel}:{record.message}', level = log_file_level, bubble = True)
            
            file_handler.push_application() 

        
        
        
        
        

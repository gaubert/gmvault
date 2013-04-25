'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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
import sys
import os

import logbook

#different types of LoggerFactory
STANDALONE = "STANDALONE"
GUI        = "GUI"


class StdoutHandler(logbook.StreamHandler):
    """A handler that writes to what is currently at stdout. At the first
glace this appears to just be a :class:`StreamHandler` with the stream
set to :data:`sys.stdout` but there is a difference: if the handler is
created globally and :data:`sys.stdout` changes later, this handler will
point to the current `stdout`, whereas a stream handler would still
point to the old one.
"""

    def __init__(self, level=logbook.base.NOTSET, format_string=None, a_filter = None, bubble=False): #pylint: disable=W0212
        super(StdoutHandler, self).__init__(logbook.base._missing, level, \
                                            format_string, None, a_filter, bubble )

    @property
    def stream(self): #pylint: disable=W0212
        """
           Return the stream where to write
        """
        return sys.stdout

#default log file
DEFAULT_LOG = "%s/gmvault.log" % (os.getenv("HOME", "."))


class GUILogger(logbook.Logger):
    """
       Work on a GUI Logger. We want message for the console and control message.
       Control message can be:
       - short information to be added and printable
       - progress information
       - short error message
       Process record => if notice get extension and format message:
       [gmv-msg]: the message
       [gmv-progress]: x over y
       [gmv-error]: the error
    """

    def process_record(self, record):
        logbook.Logger.process_record(self, record)
        if record.level_name == "NOTICE":
            if record.extra.get('type', 'DEF') == 'MSG':
                record.msg = '[gmv-msg]:%s' % (record.msg)
            elif record.extra.get('type', 'DEF') == 'PRO':
                record.msg = '[gmv-pro]:%s' % (record.msg)
            elif record.extra.get('type', 'DEF') == 'ERR':
                record.msg = '[gmv-err]:%s' % (record.msg)
            else:
                record.msg = '[gmv-def]:%s' % (record.msg)
            
class LogbookLoggerFactory(object):
    """
       Factory for creating the right logbook handler
    """
    
    def __init__(self):
        pass
    
    def setup_cli_app_handler(self, activate_log_file=False, console_level= 'CRITICAL', \
                              file_path=DEFAULT_LOG, log_file_level = 'DEBUG'):
        """
           Setup a handler for communicating with the user and still log everything in a logfile
        """
        null_handler = logbook.NullHandler()
        
        out_handler  = StdoutHandler(format_string='{record.message}', level = console_level , bubble = False)
        
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        
        # add output Handler
        out_handler.push_application() 
        
        # add file Handler
        if activate_log_file:
            file_handler = logbook.FileHandler(file_path, mode='w', format_string=\
                           '[{record.time:%Y-%m-%d %H:%M}]:{record.level_name}:{record.channel}:{record.message}',\
                                                level = log_file_level, bubble = True)
            
            file_handler.push_application()
    
    def setup_simple_file_handler(self, file_path):
        """
           Push a file handler logging only the message (no timestamp)
        """
        null_handler = logbook.NullHandler()
        
        handler      = logbook.FileHandler(file_path, format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    def setup_simple_stdout_handler(self):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = StdoutHandler(format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    def setup_simple_stderr_handler(self):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        
        null_handler = logbook.NullHandler()
        
        handler      = logbook.StderrHandler(format_string='{record.message}', level = 2, bubble = False)
         
        # first stack null handler to not have anything else logged 
        null_handler.push_application()
        # add Stderr Handler
        handler.push_application() 
    
    def get_logger(self, name):
        """
           Return a logbook logger
        """
        return logbook.Logger(name)
        return GUILogger(name)

class GUILogbookLoggerFactory(LogbookLoggerFactory):
    """
       Factory for creating the right logbook handler for the GUI
    """
    def get_logger(self, name):
        """ return GUI Logger """
        return GUILogger(name)

class LoggerFactory(object):
    '''
       My Logger Factory
    '''
    _factory = LogbookLoggerFactory()
    _created = False
    
    @classmethod
    def get_factory(cls, the_type):
        """
           Get logger factory
        """
        
        if cls._created:
            return cls._factory
        
        if the_type == STANDALONE:
            cls._factory = LogbookLoggerFactory()
            cls._created = True
        elif the_type == GUI:
            cls._factory = GUILogbookLoggerFactory()
            cls._created = True
        else:
            raise Exception("LoggerFactory type %s is unknown." % (the_type))
        
        return cls._factory
    
    @classmethod
    def get_logger(cls, name):
        """
          Simply return a logger
        """
        return cls._factory.get_logger(name)
    
    
    @classmethod
    def setup_simple_stderr_handler(cls, the_type):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        cls.get_factory(the_type).setup_simple_stderr_handler()
    
    @classmethod
    def setup_simple_stdout_handler(cls, the_type):
        """
           Push a stderr handler logging only the message (no timestamp)
        """
        cls.get_factory(the_type).setup_simple_stdout_handler()
        
    @classmethod
    def setup_simple_file_handler(cls, the_type, file_path):
        """
           Push a file handler logging only the message (no timestamp)
        """
        cls.get_factory(the_type).setup_simple_file_handler(file_path)
        
    @classmethod
    def setup_cli_app_handler(cls, the_type, activate_log_file=False, \
                              console_level= 'CRITICAL', file_path=DEFAULT_LOG,\
                               log_file_level = 'DEBUG'):
        """
           init logging engine
        """
        cls.get_factory(the_type).setup_cli_app_handler(activate_log_file, \
                                                    console_level, \
                                                    file_path, log_file_level)

'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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

import argparse
import sys

import gmv.log_utils as log_utils

LOG = log_utils.LoggerFactory.get_logger('cmdline_utils')

class CmdLineParser(argparse.ArgumentParser): #pylint: disable=R0904
    """ 
        Added service to OptionParser.
       
        Comments regarding usability of the lib. 
        By default you want to print the default in the help if you had them so the default formatter should print them
        Also new lines are eaten in the epilogue strings. You would use an epilogue to show examples most of the time so you
        want to have the possiblity to go to a new line. There should be a way to format the epilogue differently from  the rest  

    """ 
    
    BOOL_TRUE  = ['yes', 'true', '1']
    BOOL_FALSE = ['no', 'false', '0']
    BOOL_VALS  = BOOL_TRUE + BOOL_FALSE
   
    def __init__(self, *args, **kwargs): 
        """ constructor """    
        argparse.ArgumentParser.__init__(self, *args, **kwargs) #pylint: disable=W0142
   
        # I like my help option message better than the default... 
        #self.remove_option('-h') 
        #self.add_option('-h', '--help', action='help', help='Show this message and exit.') 
           
        self.epilogue = None 
    
    @classmethod 
    def convert_to_boolean(cls, val):
        """
           Convert yes, True, true, YES to boolean True and
           no, False, false, NO to boolean NO
        """
        lower_val = val.lower()
        if lower_val in cls.BOOL_TRUE:
            return True
        elif lower_val in cls.BOOL_FALSE:
            return False
        else:
            raise Exception("val %s should be in %s to be convertible to a boolean." % (val, cls.BOOL_VALS))
   
    def print_help(self, out=sys.stderr): 
        """ 
          Print the help message, followed by the epilogue (if set), to the 
          specified output file. You can define an epilogue by setting the 
          ``epilogue`` field. 
           
          :param out: file desc where to write the usage message
         
        """ 
        super(CmdLineParser, self).print_help(out)
        if self.epilogue: 
            #print >> out, '\n%s' % textwrap.fill(self.epilogue, 100, replace_whitespace = False) 
            print >> out, '\n%s' % self.epilogue
            out.flush() 
   
    def show_usage(self, msg=None): 
        """
           Print usage message          
        """
        self.die_with_usage(msg) 
           
    def die_with_usage(self, msg=None, exit_code=2): 
        """ 
          Display a usage message and exit. 
   
          :Parameters: 
              msg : str 
                  If not set to ``None`` (the default), this message will be 
                  displayed before the usage message 
                   
              exit_code : int 
                  The process exit code. Defaults to 2. 
        """ 
        if msg != None: 
            print >> sys.stderr, msg 
        
        self.print_help(sys.stderr) 
        sys.exit(exit_code) 
   
    def error(self, msg): 
        """ 
          Overrides parent ``OptionParser`` class's ``error()`` method and 
          forces the full usage message on error. 
        """ 
        self.die_with_usage("%s: error: %s\n" % (self.prog, msg))
        
    def message(self, msg):
        """
           Print a message 
        """
        print("%s: %s\n" % (self.prog, msg))
        
        
SYNC_HELP_EPILOGUE = """Examples:

a) full synchronisation with email and password login

#> gmvault --email foo.bar@gmail.com --passwd vrysecrtpasswd 

b) full synchronisation for german users that have to use googlemail instead of gmail

#> gmvault --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd

c) restrict synchronisation with an IMAP request

#> gmvault --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' --email foo.bar@gmail.com --passwd sosecrtpasswd 

"""

def test_command_parser():
    """
       Test the command parser
    """
    #parser = argparse.ArgumentParser()
    
    
    parser = CmdLineParser()
    
    subparsers = parser.add_subparsers(help='commands')
    
    # A sync command
    sync_parser = subparsers.add_parser('sync', formatter_class=argparse.ArgumentDefaultsHelpFormatter, \
                                        help='synchronize with given gmail account')
    #email argument can be optional so it should be an option
    sync_parser.add_argument('-l', '--email', action='store', dest='email', help='email to sync with')
    # sync typ
    sync_parser.add_argument('-t', '--type', action='store', default='full-sync', help='type of synchronisation')
    
    sync_parser.add_argument("-i", "--imap-server", metavar = "HOSTNAME", \
                          help="Gmail imap server hostname. (default: imap.gmail.com)",\
                          dest="host", default="imap.gmail.com")
        
    sync_parser.add_argument("-p", "--imap-port", metavar = "PORT", \
                          help="Gmail imap server port. (default: 993)",\
                          dest="port", default=993)
    
    sync_parser.set_defaults(verb='sync')

    
    sync_parser.epilogue = SYNC_HELP_EPILOGUE
    
    # A restore command
    restore_parser = subparsers.add_parser('restore', help='restore email to a given email account')
    restore_parser.add_argument('email', action='store', help='email to sync with')
    restore_parser.add_argument('--recursive', '-r', default=False, action='store_true',
                               help='Remove the contents of the directory, too',
                               )
    
    restore_parser.set_defaults(verb='restore')
    
    # A config command
    config_parser = subparsers.add_parser('config', help='add/delete/modify properties in configuration')
    config_parser.add_argument('dirname', action='store', help='New directory to create')
    config_parser.add_argument('--read-only', default=False, action='store_true',
                               help='Set permissions to prevent writing to the directory',
                               )
    
    config_parser.set_defaults(verb='config')
    
    
    
    
    # global help
    #print("================ Global Help (-h)================")
    sys.argv = ['gmvault.py']
    print(parser.parse_args())
    
    #print("================ Global Help (--help)================")
    #sys.argv = ['gmvault.py', '--help']
    #print(parser.parse_args())
    
    #print("================ Sync Help (--help)================")
    #sys.argv = ['gmvault.py', 'sync', '-h']
    #print(parser.parse_args())
    
    #sys.argv = ['gmvault.py', 'sync', 'guillaume.aubert@gmail.com', '--type', 'quick-sync']
    
    #print(parser.parse_args())
    #print("options = %s\n" % (options))
    #print("args = %s\n" % (args))
    

if __name__ == '__main__':
    
    test_command_parser()


    
    

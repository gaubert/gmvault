'''
Created on Jan 30, 2012

@author: guillaume.aubert@gmail.com
'''

import argparse
import sys

""" 
   Comments regarding usability of the lib. 
   By default you want to print the default in the help if you had them so the default formatter should print them
   Also new lines are eaten in the epilogue strings. You would use an epilogue to show examples most of the time so you
   want to have the possiblity to go to a new line. There should be a way to format the epilogue differently from  the rest  

"""
class CmdLineParser(argparse.ArgumentParser): #pylint: disable-msg=R0904
    """ Added service on OptionParser """ 
    
    BOOL_TRUE  = ['yes', 'true', '1']
    BOOL_FALSE = ['no', 'false', '0']
    BOOL_VALS  = BOOL_TRUE + BOOL_FALSE
   
    def __init__(self, *args, **kwargs): 
        """ constructor """    
        argparse.ArgumentParser.__init__(self, *args, **kwargs) #pylint: disable-msg=W0142
   
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
        self.die_with_usage("%s: error: %s\n" % (self.get_prog_name(), msg))
        
    def message(self, msg):
        """
           Print a message 
        """
        print("%s: %s\n" % (self.get_prog_name(), msg))
        
        
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
    sync_parser = subparsers.add_parser('sync', formatter_class=argparse.ArgumentDefaultsHelpFormatter, help='synchronize with given gmail account')
    #email argument can be optional so it should be an option
    sync_parser.add_argument('-l', '--email', action='store', dest='email', help='email to sync with')
    # sync typ
    sync_parser.add_argument('-t','--type', action='store', default='full-sync', help='type of synchronisation')
    
    sync_parser.add_argument("-i", "--imap-server", metavar = "HOSTNAME", \
                          help="Gmail imap server hostname. (default: imap.gmail.com)",\
                          dest="host", default="imap.gmail.com")
        
    sync_parser.add_argument("-p", "--imap-port", metavar = "PORT", \
                          help="Gmail imap server port. (default: 993)",\
                          dest="port", default=993)
    
    sync_parser.set_defaults(verb='sync')

    
    sync_parser.epilogue = SYNC_HELP_EPILOGUE
    
    # A restore command
    delete_parser = subparsers.add_parser('restore', help='restore email to a given email account')
    delete_parser.add_argument('email', action='store', help='email to sync with')
    delete_parser.add_argument('--recursive', '-r', default=False, action='store_true',
                               help='Remove the contents of the directory, too',
                               )
    
    # A config command
    create_parser = subparsers.add_parser('config', help='add/delete/modify properties in configuration')
    create_parser.add_argument('dirname', action='store', help='New directory to create')
    create_parser.add_argument('--read-only', default=False, action='store_true',
                               help='Set permissions to prevent writing to the directory',
                               )
    
    # global help
    #print("================ Global Help (-h)================")
    #sys.argv = ['gmvault.py', '-h']
    #print(parser.parse_args())
    
    #print("================ Global Help (--help)================")
    #sys.argv = ['gmvault.py', '--help']
    #print(parser.parse_args())
    
    print("================ Sync Help (--help)================")
    sys.argv = ['gmvault.py', 'sync', '-h']
    print(parser.parse_args())
    
    #sys.argv = ['gmvault.py', 'sync', 'guillaume.aubert@gmail.com', '--type', 'quick-sync']
    
    #print(parser.parse_args())
    #print("options = %s\n" % (options))
    #print("args = %s\n" % (args))
    

if __name__ == '__main__':
    
    test_command_parser()


    
    
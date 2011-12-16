'''
Created on 17 Nov 2011

@author: guillaume.aubert@eumetsat.int

CommandLine Helper

'''

import sys 
from optparse import OptionParser

class CmdLineParser(OptionParser): #pylint: disable-msg=R0904
    """ Added service on OptionParser """ 
   
    def __init__(self, *args, **kwargs): 
        """ constructor """    
        OptionParser.__init__(self, *args, **kwargs) #pylint: disable-msg=W0142
   
        # I like my help option message better than the default... 
        self.remove_option('-h') 
        self.add_option('-h', '--help', action='help', help='Show this message and exit.') 
           
        self.epilogue = None 
   
    def print_help(self, out=sys.stderr): 
        """ 
          Print the help message, followed by the epilogue (if set), to the 
          specified output file. You can define an epilogue by setting the 
          ``epilogue`` field. 
           
          :param out: file desc where to write the usage message
         
        """ 
        OptionParser.print_help(self, out) 
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
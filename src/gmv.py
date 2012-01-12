'''
Created on Dec 16, 2011

@author: guillaume.aubert@gmail.com
'''
import socket
import sys

from cmdline_utils  import CmdLineParser
import log_utils
import gmvault




HELP_USAGE = """ gmvault [options]
                                     
Arguments: a list of request files or an inline request."""

HELP_EPILOGUE = """Examples:

a) full synchronisation with email and password login

#> gmvault --email foo.bar@gmail.com --passwd vrysecrtpasswd 

b) full synchronisation for german users that have to use googlemail instead of gmail

#> gmvault --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd

c) restrict synchronisation with an IMAP request

#> gmvault --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd 

"""

LOG = log_utils.LoggerFactory.get_logger('gmv')

class GMVaultLauncher(object):
    
    def __init__(self):
        """ constructor """
        super(GMVaultLauncher, self).__init__()

    def parse_args(self):
        """ Parse command line arguments 
            
            :returns: a dict that contains the arguments
               
            :except Exception Error
            
        """
        #print sys.argv
        
        parser = CmdLineParser()
        
        parser.add_option("-s", "--sync", help = "Full synchronisation between gmail with local db. (default sync mode).", \
                          action ="store_true", dest="sync", default= False)
        
        parser.add_option("-q", "--quick-sync", help = "Quick synchronisation between  gmail with local db.", \
                          action ="store_true", dest="qsync", default= False)
        
        parser.add_option("-n", "--inc-sync", help = "Incremental synchronisation between gmail with local db.", \
                          action ="store_true", dest="isync", default= False)
        
        parser.add_option("-i", "--imap-server", metavar = "HOSTNAME", \
                          help="Gmail imap server hostname.",\
                          dest="host", default="imap.gmail.com")
        
        parser.add_option("-t", "--imap-port", metavar = "PORT", \
                          help="Gmail imap server port.",\
                          dest="port", default=993)
        
        parser.add_option("-l", "--email", \
                          help="Gmail email.",\
                          dest="email", default=None)
        
        parser.add_option("-p", "--passwd", \
                          help="Gmail password.",\
                          dest="passwd", default=None)
        
        parser.add_option("-r", "--imap-request", metavar = "REQ",\
                          help="Imap request to restrict sync.",\
                          dest="request", default="ALL")
        
        parser.add_option("-d", "--db-dir", \
                          help="Database root directory.",\
                          dest="db_dir", default="./gmvault-db")
        
        parser.add_option("-o", "--oauth-token", metavar = "TOK", \
                          help="Oauth-token.",\
                          dest="oauth_token", default=None)
        
        parser.add_option("-z", "--db-cleaning", \
                          help="To activate or deactive the disk db cleaning. Automatically deactivated if a imap req is passed in args.",\
                          dest="db_cleaning", default=None)
        
        parser.add_option("-v", "--verbose", \
                          help="Activate the verbose mode.",\
                          action="store_true", dest="verbose", default=False)
       
        """
        dir_help =  "Directory where the result files will be stored.".ljust(66)
        dir_help += "(Default =. the current dir)".ljust(66)
        dir_help += "The directory will be created if it doesn't exist.".ljust(66)
        
        parser.add_option("-d", "--dir", metavar="DIR", \
                          help = dir_help,\
                          dest ="output_dir", default=".")
        """
        
        # add custom usage and epilogue
        parser.epilogue = HELP_EPILOGUE
        parser.usage    = HELP_USAGE
        
        (options, args) = parser.parse_args() #pylint: disable-msg=W0612
        
        parsed_args = { }
        
        #check the sync mode
        if options.qsync:
            parsed_args['sync-mode'] = 'quick-sync'
        elif options.isync:
            parsed_args['sync-mode'] = 'inc-sync'
        else:
            parsed_args['sync-mode'] = 'full-sync'
        
        # add host
        parsed_args['host']             = options.host
        
        #convert to int if necessary
        port_type = type(options.port)
        
        try:
            if port_type == type('s') or port_type == type("s"):
                port = int(options.port)
            else:
                port = options.port
        except Exception, e:
            self.error("port option %s is not a number. Please check the port value" % (port))
        
        # add port
        parsed_args['port']             = port
        
        # add login
        parsed_args['email']            = options.email
        
        # Cannot have passwd and oauth-token at the same time
        if options.passwd and options.oauth_token:
            self.error("Only one authentication mode can be used (password or oauth-token)")
        
        # add passwd
        parsed_args['passwd']           = options.passwd
        
        # add imap request
        parsed_args['request']          = options.request

        # add oauth token
        parsed_args['oauth-token']      = options.oauth_token
        
        # add passwd
        parsed_args['db-dir']           = options.db_dir
        
        # add db-cleaning
        # if request passed put it False unless it has been forced by the user
        # default is True (db-cleaning done)
    
        #default 
        parsed_args['db-cleaning'] = True
        
        # if there is a value then it is forced
        if options.db_cleaning: 
            parsed_args['db-cleaning'] = parser.convert_to_boolean(options.db_cleaning)
        elif parsed_args['request'] and not options.db_cleaning:
            #else if we have a request and not forced put it to false
            parsed_args['db-cleaning'] = False
            
        #verbose
        parsed_args['verbose']          = options.verbose
        
        #add parser itself for error handling
        parsed_args['parser'] = parser
        
        return parsed_args
            
    
    
    def run(self, args):
        """
           Run the grep with the given args 
        """
        on_error       = True
        die_with_usage = True
        
        try:
            syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], args['passwd'])
            
            
            syncer.sync(args['request'], compress_on_disk = True, db_cleaning = args['db-cleaning'])
        
            on_error = False
        
        except KeyboardInterrupt, kb:
            LOG.critical("CRTL^C. Stop all operations.")
            on_error = False
        except socket.error:
            LOG.critical("ERROR: Network problem. Please check your gmail server hostname, the internet connection or your network setup.")
            LOG.critical("For more information see log file.\n")
            die_with_usage = False
        except Exception, err:
            LOG.critical("Error %s. For more information see log file" % (err) )
            LOG.exception(err)
        finally: 
            if on_error and die_with_usage:
                args['parser'].die_with_usage()
 
def init_logging():
    """
       init logging infrastructure
    """       
    #setup application logs: one handler for stdout and one for a log file
    log_utils.LoggerFactory.setup_cli_app_handler(activate_log_file=True, file_path="./gmvault.log") 
    
    
def bootstrap_run():
    """ temporary bootstrap """
    
    init_logging()
    
    LOG.critical("")
    
    gmvault = GMVaultLauncher()
    
    args = gmvault.parse_args()
    
    gmvault.run(args)
   
    
if __name__ == '__main__':
    
    bootstrap_run()
    
    sys.exit(0)

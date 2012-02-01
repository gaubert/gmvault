'''
Created on Jan 31, 2012

@author: guillaume.aubert@gmail.com
'''
import socket
import sys
import getpass

import argparse
import log_utils
import imaplib
import gmvault_utils
import gmvault

from sandbox  import CmdLineParser, CredentialHelper

SYNC_HELP_EPILOGUE = """Examples:

a) full synchronisation with email and password login

#> gmvault --email foo.bar@gmail.com --passwd vrysecrtpasswd 

b) full synchronisation for german users that have to use googlemail instead of gmail

#> gmvault --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd

c) restrict synchronisation with an IMAP request

#> gmvault --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' --email foo.bar@gmail.com --passwd sosecrtpasswd 

"""

LOG = log_utils.LoggerFactory.get_logger('gmv')

class NotSeenAction(argparse.Action):
    """
       to differenciate between a seen and non seen command
    """
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, 'empty')

class GMVaultLauncher(object):
    
    def __init__(self):
        """ constructor """
        super(GMVaultLauncher, self).__init__()

    def parse_args(self):
        """ Parse command line arguments 
            
            :returns: a dict that contains the arguments
               
            :except Exception Error
            
        """
        parser = CmdLineParser()
    
        subparsers = parser.add_subparsers(help='commands')
        
        # A sync command
        sync_parser = subparsers.add_parser('sync', \
                                            formatter_class=argparse.ArgumentDefaultsHelpFormatter, \
                                            help='synchronize with given gmail account')
        #email argument can be optional so it should be an option
        sync_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email to sync with')
        # sync typ
        sync_parser.add_argument('-t','--type', \
                                 action='store', dest='type', \
                                 default='full-sync', help='type of synchronisation')
        
        sync_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory",\
                                 dest="db_dir", default="./gmvault-db")
        
        sync_parser.add_argument("-r", "--imap-req", metavar = "REQ", \
                                 help="Imap request to restrict sync. (default: ALL)",\
                                 dest="request", default="ALL")
        
        sync_parser.add_argument("-z", "--db-cleaning", \
                          help="To activate or deactive the disk db cleaning. Automatically deactivated if a imap req is passed in args.",\
                          dest="db_cleaning", default=None)
        
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        sync_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication (default method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        sync_parser.add_argument("-p", "--passwd", \
                          help="use password authentication (not recommended)",
                          action='store_const', dest="passwd", const='empty', default='not_seen')
        
        sync_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        sync_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        sync_parser.set_defaults(verb='sync')
    
        
        sync_parser.epilogue = SYNC_HELP_EPILOGUE
        
        # A config command
        config_parser = subparsers.add_parser('config', help='add/delete/modify properties in configuration')
        config_parser.add_argument('dirname', action='store', help='New directory to create')
        config_parser.add_argument('--read-only', default=False, action='store_true',
                                   help='Set permissions to prevent writing to the directory',
                                   )
        config_parser.set_defaults(verb='config') 
        
        options = parser.parse_args()
        
        print("Namespace = %s\n" % (options))
        
        parsed_args = { }
        
        parsed_args['command'] = options.verb
        
        if parsed_args.get('command', '') == 'sync':
            
            #add email
            parsed_args['email']            = options.email
            
            
            if options.passwd == 'empty' and options.oauth_token == 'empty':
                parser.error('You have to use one credential method. Please choose between oauth and password (recommend oauth).')
        
            # handle the credential
            if options.passwd == 'not_seen' and options.oauth_token == 'not_seen':
                #default to xoauth
                LOG.critical('Default to xoauth authentication')
                options.oauth_token = 'empty'
            
        
            # Cannot have passwd and oauth-token at the same time
            #if options.passwd and options.oauth_token:
            #    self.error("Only one authentication mode can be used (password or oauth-token)")
            
            # add passwd
            parsed_args['passwd']           = options.passwd
            
            # add oauth tok
            parsed_args['oauth']            = options.oauth_token
            
            #add sync type
            parsed_args['type']             = options.type
            
            # add imap request
            parsed_args['request']          = options.request
            
            #add db_dir
            parsed_args['db-dir']           = options.db_dir
            
            # add host
            parsed_args['host']             = options.host
            
            #convert to int if necessary
            port_type = type(options.port)
            
            try:
                if port_type == type('s') or port_type == type("s"):
                    port = int(options.port)
                else:
                    port = options.port
            except Exception, _:
                parser.error("--port option %s is not a number. Please check the port value" % (port))
                
            # add port
            parsed_args['port']             = port
            
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
            
            #add parser
            parsed_args['parser']           = parser
        
        
        return parsed_args
    
    
    def run(self, args, credential):
        """
           Run the grep with the given args 
        """
        on_error       = True
        die_with_usage = True
        
        try:
            
            # hanlde credential in all levels
            syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential)
            
            
            syncer.sync(args['request'], compress_on_disk = True, db_cleaning = args['db-cleaning'])
        
            on_error = False
        
        except KeyboardInterrupt, _:
            LOG.critical("CRTL^C. Stop all operations.")
            on_error = False
        except socket.error:
            LOG.critical("ERROR: Network problem. Please check your gmail server hostname, the internet connection or your network setup.")
            LOG.critical("For more information see log file.\n")
            die_with_usage = False
        except imaplib.IMAP4.error, imap_err:
            #bad login or password
            if str(imap_err) in ['[AUTHENTICATIONFAILED] Invalid credentials (Failure)', \
                                 '[ALERT] Web login required: http://support.google.com/mail/bin/answer.py?answer=78754 (Failure)', \
                                 '[ALERT] Invalid credentials (Failure)'] :
                LOG.critical("ERROR: Invalid credentials, cannot login to the gmail server. Please check your login and password or xoauth token.")
                die_with_usage = False
            else:
                LOG.critical("Error %s. For more information see log file" % (imap_err) )
                LOG.exception(gmvault_utils.get_exception_traceback())
        except Exception, err:
            LOG.critical("Error %s. For more information see log file" % (err) )
            LOG.exception(gmvault_utils.get_exception_traceback())
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
    
    gmvlt = GMVaultLauncher()
    
    args = gmvlt.parse_args()
    
    credential = CredentialHelper.get_credential(args)
    
    gmvlt.run(args, credential)
   
    
if __name__ == '__main__':
    
    #import sys
    #sys.argv = ['gmvault.py', 'sync', 'guillaume.aubert@gmail.com']
    
    bootstrap_run()
    
    sys.exit(0)
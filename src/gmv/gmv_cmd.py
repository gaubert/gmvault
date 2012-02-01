'''
Created on Jan 31, 2012

@author: guillaume.aubert@gmail.com
'''
import socket
import sys
import getpass
import datetime

import argparse
import log_utils
import imaplib
import gmvault_utils
import gmvault

from cmdline_utils  import CmdLineParser, CredentialHelper

GLOBAL_HELP_EPILOGUE="""Examples:

a) Get help for each of the individual commands

#> gmvault sync -h
#> gmvault restore --help

"""

REST_HELP_EPILOGUE = """Examples:
"""

SYNC_HELP_EPILOGUE = """Examples:

a) Full synchronisation with email and oauth login in ./gmvault-db

#> gmvault sync foo.bar@gmail.com

b) Full synchronisation for German users that have to use googlemail instead of gmail

#> gmvault sync --imap-server imap.googlemail.com 'foo.bar@gmail.com'

c) Quick synchronisation (only the last 2 months are scanned)

#> gmvault sync --type quick foo.bar@gmail.com

g) Custom synchronisation with an IMAP request

#> gmvault sync --type custom --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' 'foo.bar@gmail.com'

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
        
    @gmvault_utils.memoized
    def _create_parser(self):
        """
           Create the argument parser
           Return the created parser
        """
        parser = CmdLineParser()
        
        parser.epilogue = GLOBAL_HELP_EPILOGUE
    
        subparsers = parser.add_subparsers(help='commands (mandatory).')
         
        # A sync command
        sync_parser = subparsers.add_parser('sync', \
                                            help='synchronize with given gmail account.')
        #email argument can be optional so it should be an option
        sync_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email to sync with.')
        # sync typ
        sync_parser.add_argument('-t','--type', \
                                 action='store', dest='type', \
                                 default='full', help='type of synchronisation: full|quick|custom. (default: full)')
        
        sync_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: ./gmvault-db)",\
                                 dest="db_dir", default="./gmvault-db")
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        sync_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        sync_parser.add_argument("-p", "--passwd", \
                          help="use password authentication. (not recommended)",
                          action='store_const', dest="passwd", const='empty', default='not_seen')
        
        sync_parser.add_argument("-r", "--imap-req", metavar = "REQ", \
                                 help="Imap request to restrict sync.",\
                                 dest="request", default="ALL")
        
        sync_parser.add_argument("-z", "--db-cleaning", \
                          help="To activate or deactive the disk db cleaning. Automatically deactivated if a imap req is passed in args.",\
                          dest="db_cleaning", default=None)
        
        sync_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        sync_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        sync_parser.set_defaults(verb='sync')
    
        sync_parser.epilogue = SYNC_HELP_EPILOGUE
        
        # restore command
        rest_parser = subparsers.add_parser('restore', \
                                            help='restore gmvault-db to a given email account.')
        #email argument can be optional so it should be an option
        rest_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email account to restore.')
        # restore mode
        rest_parser.add_argument('-t','--type', \
                                 action='store', dest='type', \
                                 default='full', help='restore modes: full|quick|mirror. (default: full)')
        
        # add a label
        rest_parser.add_argument('-l','--label', \
                                 action='store', dest='label', \
                                 default=None, help='Apply a label to restored emails')
        
        rest_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: ./gmvault-db)",\
                                 dest="db_dir", default="./gmvault-db")
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        rest_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        rest_parser.add_argument("-p", "--passwd", \
                          help="use password authentication. (not recommended)",
                          action='store_const', dest="passwd", const='empty', default='not_seen')
        
        rest_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        rest_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        rest_parser.set_defaults(verb='restore')
    
        rest_parser.epilogue = REST_HELP_EPILOGUE
    
        
        
        # A config command
        config_parser = subparsers.add_parser('config', help='add/delete/modify properties in configuration.')
        config_parser.add_argument('dirname', action='store', help='New directory to create')
        config_parser.add_argument('--read-only', default=False, action='store_true',
                                   help='Set permissions to prevent writing to the directory',
                                   )
        config_parser.set_defaults(verb='config') 
        
        return parser
      
        
    def parse_args(self):
        """ Parse command line arguments 
            
            :returns: a dict that contains the arguments
               
            :except Exception Error
            
        """
        
        parser = self._create_parser()
          
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
                ('Use ')
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
                
        elif parsed_args.get('command', '') == 'restore':
            
            #add email
            parsed_args['email']            = options.email
            
            
            if options.passwd == 'empty' and options.oauth_token == 'empty':
                parser.error('You have to use one credential method. Please choose between oauth and password (recommend oauth).')
        
            # handle the credential
            if options.passwd == 'not_seen' and options.oauth_token == 'not_seen':
                #default to xoauth
                ('Use ')
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
            
            # add label
            parsed_args['label']            = options.label
            
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
    
        elif parsed_args.get('command', '') == 'config':
            pass
    
        #add parser
        parsed_args['parser']           = parser
        
        return parsed_args
    
    
    def _sync(self, args, credential):
        """
           Execute All synchronisation operations
        """
        
        LOG.critical("Connect to Gmail server.\n")
        # handle credential in all levels
        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential)
        
        #full sync is the first one
        if args.get('type', '') == 'full':
        
            #choose full sync. Ignore the request
            syncer.sync('ALL', compress_on_disk = True, db_cleaning = args['db-cleaning'])
            
        elif args.get('type', '') == 'quick':
            
            #sync only the last 2 months in order to be quick (cleaning is import here because recent days might move again
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(2*365/12)
            
            # today + 1 day
            end   = today + datetime.timedelta(1)
            
            syncer.sync(syncer.get_imap_request_btw_2_dates(begin, end), compress_on_disk = True, db_cleaning = args['db-cleaning'])
            
            
            
        elif args.get('type', '') == 'custom':
            
            # pass an imap request. Assume that the user know what to do here
            syncer.sync(args['request'], compress_on_disk = True, db_cleaning = args['db-cleaning'])
            
    
    
    def run(self, args, credential):
        """
           Run the grep with the given args 
        """
        on_error       = True
        die_with_usage = True
        
        try:
            
            if args.get('command', '') == 'sync':
                self._sync(args, credential)
                
                on_error = False
            elif args.get('command', '') == 'restore':
                LOG.critical("Restore Something TBD.\n")
            elif args.get('command', '') == 'config':
                LOG.critical("Configure something. TBD.\n")
        
        except KeyboardInterrupt, _:
            LOG.critical("CRTL^C. Stop all operations.\n")
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
                LOG.critical("ERROR: Invalid credentials, cannot login to the gmail server. Please check your login and password or xoauth token.\n")
                die_with_usage = False
            else:
                LOG.critical("Error %s. For more information see log file\n" % (imap_err) )
                LOG.exception(gmvault_utils.get_exception_traceback())
        except Exception, err:
            LOG.critical("Error %s. For more information see log file\n" % (err) )
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
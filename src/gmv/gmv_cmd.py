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

import socket
import sys
import datetime
import os

import argparse
import log_utils
import imaplib
import gmvault_utils
import gmvault

from cmdline_utils  import CmdLineParser
from credential_utils import CredentialHelper

GMVAULT_VERSION="1.0-beta"

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

#> gmvault sync --type custom --imap-req 'Since 1-Nov-2011 Before 10-Nov-2011' 'foo.bar@gmail.com'

"""

LOG = log_utils.LoggerFactory.get_logger('gmv')

class NotSeenAction(argparse.Action):
    """
       to differenciate between a seen and non seen command
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            setattr(namespace, self.dest, 'empty')
        else:
            setattr(namespace, self.dest, values)

class GMVaultLauncher(object):
    
    SYNC_TYPES    = ['full', 'quick', 'custom']
    RESTORE_TYPES = ['full', 'quick']
    
    DEFAULT_GMVAULT_DB = "%s/gmvault-db" % (os.getenv("HOME", "."))
    
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

        parser.add_argument("-v", '--version', action='version', version='Gmvault v%s' % (GMVAULT_VERSION))
        
        subparsers = parser.add_subparsers(title='subcommands', help='valid subcommands.')
         
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
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        sync_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default recommended method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        #sync_parser.add_argument("-p", "--passwd", metavar = "PASS", \
        #                  help="use password authentication. (not recommended)",
        #                  action= NotSeenAction , dest="passwd", default='not_seen')
        sync_parser.add_argument("--renew-passwd", \
                          help="renew the stored password via an interactive authentication session. (not recommended)",
                          action= 'store_const' , dest="passwd", const='renew')
        
        sync_parser.add_argument("--store-passwd", \
                          help="use interactive password authentication, encrypt and store the password. (not recommended)",
                          action= 'store_const' , dest="passwd", const='store')
        
        sync_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action= 'store_const' , dest="passwd", const='empty', default='not_seen')
        
        sync_parser.add_argument("-r", "--imap-req", metavar = "REQ", \
                                 help="Imap request to restrict sync.",\
                                 dest="imap_request", default=None)
        
        sync_parser.add_argument("-g", "--gmail-req", metavar = "REQ", \
                                 help="Gmail search request to restrict sync as defined in https://support.google.com/mail/bin/answer.py?hl=en&answer=7190",\
                                 dest="gmail_request", default=None)
        
        sync_parser.add_argument("-e", "--encrypt", \
                                 help="encrypt stored email messages in the database.",\
                                 action='store_true',dest="encrypt", default=False)
        
        sync_parser.add_argument("-z", "--db-cleaning", \
                          help="To activate or deactive the disk db cleaning. Automatically deactivated if a imap req is passed in args.",\
                          dest="db_cleaning", default=None)
        
        sync_parser.add_argument("-m", "--multiple-db-owner", \
                                 help="Allow the email database to be synchronized with emails from multiple accounts.",\
                                 action='store_true',dest="allow_mult_owners", default=False)
        
        sync_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        sync_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        sync_parser.add_argument("--debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        
        sync_parser.set_defaults(verb='sync')
    
        sync_parser.epilogue = SYNC_HELP_EPILOGUE
        
        # restore command
        rest_parser = subparsers.add_parser('restore', \
                                            help='restore gmvault-db to a given email account.')
        #email argument can be optional so it should be an option
        rest_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email account to restore.')
        
        # restore typ
        rest_parser.add_argument('-t','--type', \
                                 action='store', dest='type', \
                                 default='full', help='type of restoration: full|quick. (default: full)')
        
        # add a label
        rest_parser.add_argument('-l','--label', \
                                 action='store', dest='label', \
                                 default=None, help='Apply a label to restored emails')
        
        # activate the restart mode
        rest_parser.add_argument("--restart", \
                                 action='store_true', dest='restart', \
                                 default=False, help= 'Restart from the last saved gmail id.')
        
        rest_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: ./gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        rest_parser.add_argument("-o", "--oauth", \
                          help="use oauth for authentication. (default method)",\
                          action='store_const', dest="oauth_token", const='empty', default='not_seen')
        
        rest_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action='store_const', dest="passwd", const='empty', default='not_seen')
        
        rest_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        rest_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        rest_parser.add_argument("--debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        rest_parser.set_defaults(verb='restore')
    
        rest_parser.epilogue = REST_HELP_EPILOGUE
    
        
        
        # A config command
        #config_parser = subparsers.add_parser('config', help='add/delete/modify properties in configuration.')
        #config_parser.add_argument('dirname', action='store', help='New directory to create')
        #config_parser.add_argument('--read-only', default=False, action='store_true', help='Set permissions to prevent writing to the directory',)
        #config_parser.set_defaults(verb='config') 
        
        return parser
      
    
    def _parse_common_args(self, options, parser, parsed_args, list_of_types = []):
        """
           Parse the common arguments for sync and restore
        """
        #add email
        parsed_args['email']            = options.email
        
        parsed_args['debug']            = options.debug
        
        #user entered both authentication methods
        if options.passwd == 'empty' and options.oauth_token == 'empty':
            parser.error('You have to use one credential method. Please choose between oauth and password (recommend oauth).')
        
        # user entered no authentication methods => go to default oauth
        if options.passwd == 'not_seen' and options.oauth_token == 'not_seen':
            #default to xoauth
            options.oauth_token = 'empty'
            
        # add passwd
        parsed_args['passwd']           = options.passwd
        
        # add oauth tok
        parsed_args['oauth']            = options.oauth_token
        
        #add sync type
        if options.type:
            if options.type.lower() in list_of_types:
                parsed_args['type'] = options.type.lower()
            else:
                parser.error('Unknown type for command %s. The type should be one of %s' % (parsed_args['command'], list_of_types))
        
        #add db_dir
        parsed_args['db-dir']           = options.db_dir

        LOG.critical("Use gmvault-db %s." % (parsed_args['db-dir'])) 
        
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
             
        return parsed_args
        
    def parse_args(self):
        """ Parse command line arguments 
            
            :returns: a dict that contains the arguments
               
            :except Exception Error
            
        """
        
        parser = self._create_parser()
          
        options = parser.parse_args()
        
        LOG.debug("Namespace = %s\n" % (options))
        
        parsed_args = { }
                
        parsed_args['command'] = options.verb
        
        if parsed_args.get('command', '') == 'sync':
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.SYNC_TYPES)
            
            # handle the search requests (IMAP or GMAIL dialect)
            if options.imap_request and options.gmail_request:
                parser.error('Please use only one search request type. You can use --imap-req or --gmail-req.')
            elif not options.imap_request and not options.gmail_request:
                LOG.debug("No search request type passed: Get everything.")
                parsed_args['request']   = {'type': 'imap', 'req':'ALL'}
            elif options.gmail_request and not options.imap_request:
                parsed_args['request']   = { 'type': 'gmail', 'req' : options.gmail_request}
            else:
                parsed_args['request']    = { 'type':'imap',   'req' : options.imap_request}
        
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
                
            #add encryption option
            parsed_args['encrypt'] = options.encrypt
            
            #add ownership checking
            parsed_args['ownership_control'] = not options.allow_mult_owners
                
                
        elif parsed_args.get('command', '') == 'restore':
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.RESTORE_TYPES)
            
            # add restore label if there is any
            parsed_args['label'] = options.label
            
            parsed_args['restart'] = options.restart

    
        elif parsed_args.get('command', '') == 'config':
            pass
    
        #add parser
        parsed_args['parser']           = parser
        
        return parsed_args
    
    def _restore(self, args, credential):
        """
           Execute All restore operations
        """
        LOG.critical("Connect to Gmail server.")
        # Create a gmvault releaving read_only_access
        restorer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential, read_only_access = False)
        
        #full sync is the first one
        if args.get('type', '') == 'full':
            
            #call restore
            labels = [args['label']] if args['label'] else []
            restorer.restore(extra_labels = labels, restart = args['restart'])
            
        elif args.get('type', '') == 'quick':
            
            #take the last two to 3 months depending on the current date
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(2*365/12)
            
            starting_dir = gmvault_utils.get_ym_from_datetime(begin)
            
            #call restore
            labels = [args['label']] if args['label'] else []
            restorer.restore(pivot_dir = starting_dir, extra_labels = labels, restart = args['restart'])
        
        else:
            raise ValueError("Unknown synchronisation mode %s. Please use full (default), quick.")
        
        #print error report
        LOG.critical(restorer.get_error_report()) 
            
            
    def _sync(self, args, credential):
        """
           Execute All synchronisation operations
        """
        
        LOG.critical("Connect to Gmail server.")
        
        # handle credential in all levels
        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential, read_only_access = True, use_encryption = args['encrypt'])
        
        
        
        #full sync is the first one
        if args.get('type', '') == 'full':
        
            #choose full sync. Ignore the request
            syncer.sync({ 'type': 'imap', 'req': 'ALL' } , compress_on_disk = True, \
                        db_cleaning = args['db-cleaning'], ownership_checking = args['ownership_control'])
            
        elif args.get('type', '') == 'quick':
            
            #sync only the last 2 months in order to be quick (cleaning is import here because recent days might move again
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(2*365/12)
            
            # today + 1 day
            end   = today + datetime.timedelta(1)
            
            syncer.sync( { 'type': 'imap', 'req': syncer.get_imap_request_btw_2_dates(begin, end) }, \
                           compress_on_disk = True, \
                           db_cleaning = args['db-cleaning'], \
                           ownership_checking = args['ownership_control'])
            
        elif args.get('type', '') == 'custom':
            
            # pass an imap request. Assume that the user know what to do here
            LOG.critical("Perform custom synchronisation with request: %s" % (args['request']['req']))
            
            syncer.sync(args['request'], compress_on_disk = True, db_cleaning = args['db-cleaning'], \
                        ownership_checking = args['ownership_control'])
        else:
            raise ValueError("Unknown synchronisation mode %s. Please use full (default), quick or custom.")
        
        
        #print error report
        LOG.critical(syncer.get_error_report())
            
    
    
    def run(self, args):
        """
           Run the grep with the given args 
        """
        on_error       = True
        die_with_usage = True
        
        try:
            
            credential = CredentialHelper.get_credential(args)
            
            if args.get('command', '') == 'sync':
                
                self._sync(args, credential)
                
            elif args.get('command', '') == 'restore':
                
                self._restore(args, credential)
                
            elif args.get('command', '') == 'config':
                
                LOG.critical("Configure something. TBD.\n")
            
            on_error = False
        
        except KeyboardInterrupt, _:
            LOG.critical("\nCRTL^C. Stop all operations.\n")
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
    log_utils.LoggerFactory.setup_cli_app_handler(activate_log_file=False, file_path="./gmvault.log") 
    
def activate_debug_mode():
    """
       Activate debugging logging
    """
    log_utils.LoggerFactory.setup_cli_app_handler(activate_log_file=True, console_level= 'DEBUG', file_path="%s/gmvault.log" % os.getenv("HOME","."))
    
def bootstrap_run():
    """ temporary bootstrap """
    
    #force argv[0] to gmvault
    sys.argv[0] = "gmvault"
    
    init_logging()
    
    LOG.critical("")
    
    gmvlt = GMVaultLauncher()
    
    args = gmvlt.parse_args()
    
    #activate debug if enabled
    if args['debug']:
        LOG.critical("Activate debugging information.")
        activate_debug_mode()
    
    gmvlt.run(args)
   
    
if __name__ == '__main__':
     
    #import sys
    #sys.argv = ['gmvault.py', 'sync', 'guillaume.aubert@gmail.com']
    bootstrap_run()
    
    sys.exit(0)

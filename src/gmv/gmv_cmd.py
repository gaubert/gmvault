# -*- coding: utf-8 -*-
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
import socket
import sys
import datetime
import os
import signal
import traceback

import argparse
import imaplib
import gmv.log_utils as log_utils
import gmv.gmvault_utils as gmvault_utils
import gmv.gmvault as gmvault
import gmv.gmvault_export as gmvault_export
import gmv.collections_utils as collections_utils

from gmv.cmdline_utils  import CmdLineParser
from gmv.credential_utils import CredentialHelper

GMVAULT_VERSION = gmvault_utils.GMVAULT_VERSION

GLOBAL_HELP_EPILOGUE = """Examples:

a) Get help for each of the individual commands

#> gmvault sync -h
#> gmvault restore --help
#> gmvault check -h
#> gmvault export -h

"""

REST_HELP_EPILOGUE = """Examples:

a) Complete restore of your gmail account (backed up in ~/gmvault-db) into anewfoo.bar@gmail.com 

#> gmvault restore -d ~/gmvault-db anewfoo.bar@gmail.com

b) Quick restore (restore only the last 2 months to make regular updates) of your gmail account into anewfoo.bar@gmail.com 

#> gmvault restore --type quick -d ~/gmvault-db foo.bar@gmail.com

c) Restart a restore after a previous error (Gmail can cut the connection if it is too long)

#> gmvault restore -d ~/gmvault-db anewfoo.bar@gmail.com --resume

d) Apply a label to all restored emails

#> gmvault restore --apply-label "20120422-gmvault" -d ~/gmvault-db anewfoo.bar@gmail.com
"""

SYNC_HELP_EPILOGUE = """Examples:

a) Full synchronisation with email and oauth login in ./gmvault-db

#> gmvault sync foo.bar@gmail.com

b) Quick daily synchronisation (only the last 2 months are scanned)

#> gmvault sync --type quick foo.bar@gmail.com

c) Resume Full synchronisation from where it failed to not go through your mailbox again

#> gmvault sync foo.bar@gmail.com --resume

d) Encrypt stored emails to save them safely anywhere

#> gmvault sync foo.bar@gmail.com --encrypt

d) Custom synchronisation with an IMAP request for advance users

#> gmvault sync --type custom --imap-req "Since 1-Nov-2011 Before 10-Nov-2011" foo.bar@gmail.com

e) Custom synchronisation with an Gmail request for advance users.
   Get all emails with label work and sent by foo.

#> gmvault sync --type custom --gmail-req "in:work from:foo" foo.bar@gmail.com

"""

EXPORT_HELP_EPILOGUE = """Warning: Experimental Functionality requiring more testing.

Examples:

a) Export default gmvault-db ($HOME/gmvault-db or %HOME$/gmvault-db) as a maildir mailbox.

#> gmvault export ~/my-mailbox-dir

b) Export a gmvault-db as a mbox mailbox (compliant with Thunderbird).

#> gmvault export -d /tmp/gmvault-db /tmp/a-mbox-dir

c) Export only a limited set of labels from the default gmvault-db as a mbox mailbox (compliant with Thunderbird).

#> gmvault export -l "label1" -l "TopLabel/LabelLev1" /tmp/a-mbox-dir

d) Use one of the export type dedicated to a specific tool (dovecot or offlineIMAP)

#> gmvault export -t dovecot /tmp/a-dovecot-dir
"""

LOG = log_utils.LoggerFactory.get_logger('gmv')

class NotSeenAction(argparse.Action): #pylint:disable=R0903,w0232
    """
       to differenciate between a seen and non seen command
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            setattr(namespace, self.dest, 'empty')
        else:
            setattr(namespace, self.dest, values)

class GMVaultLauncher(object):
    """
       GMVault launcher handling the command parsing
    """
    
    SYNC_TYPES    = ['full', 'quick', 'custom']
    RESTORE_TYPES = ['full', 'quick']
    CHECK_TYPES   = ['full']
    EXPORT_TYPES  = collections_utils.OrderedDict([
                     ('offlineimap', gmvault_export.OfflineIMAP),
                     ('dovecot', gmvault_export.Dovecot),
                     ('maildir', gmvault_export.OfflineIMAP),
                     ('mbox', gmvault_export.MBox)])
    EXPORT_TYPE_NAMES = ", ".join(EXPORT_TYPES)
    
    DEFAULT_GMVAULT_DB = "%s/gmvault-db" % (os.getenv("HOME", "."))
    
    def __init__(self):
        """ constructor """
        super(GMVaultLauncher, self).__init__()

    @gmvault_utils.memoized
    def _create_parser(self): #pylint: disable=R0915
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
                                            help='synchronize with a given gmail account.')
        #email argument can be optional so it should be an option
        sync_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='email to sync with.')
        # sync typ
        sync_parser.add_argument('-t', '-type', '--type', \
                                 action='store', dest='type', \
                                 default='full', help='type of synchronisation: full|quick|custom. (default: full)')
        
        sync_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        sync_parser.add_argument("-y", "--oauth2", \
                          help="use oauth for authentication. (default recommended method)",\
                          action='store_const', dest="oauth2_token", const='empty', default='not_seen')

        sync_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action= 'store_const' , dest="passwd", const='empty', default='not_seen')

        sync_parser.add_argument("--renew-oauth2-tok", \
                          help="renew the stored oauth token (two legged or normal) via an interactive authentication session.",
                          action= 'store_const' , dest="oauth2_token", const='renew')

        sync_parser.add_argument("--renew-passwd", \
                          help="renew the stored password via an interactive authentication session. (not recommended)",
                          action= 'store_const' , dest="passwd", const='renew')
        
        sync_parser.add_argument("--store-passwd", \
                          help="use interactive password authentication, encrypt and store the password. (not recommended)",
                          action= 'store_const' , dest="passwd", const='store')
        
        #sync_parser.add_argument("-r", "--imap-req", type = get_unicode_commandline_arg, metavar = "REQ", \
        #                         help="Imap request to restrict sync.",\
        #                         dest="imap_request", default=None)

        sync_parser.add_argument("-r", "--imap-req", metavar = "REQ", \
                                 help="Imap request to restrict sync.",\
                                 dest="imap_request", default=None)
        
        sync_parser.add_argument("-g", "--gmail-req", metavar = "REQ", \
                                 help="Gmail search request to restrict sync as defined in"\
                                      "https://support.google.com/mail/bin/answer.py?hl=en&answer=7190",\
                                 dest="gmail_request", default=None)
        
        # activate the resume mode --restart is deprecated
        sync_parser.add_argument("--resume", "--restart", \
                                 action='store_true', dest='restart', \
                                 default=False, help= 'Resume the sync action from the last saved gmail id.')
        
        # activate the resume mode --restart is deprecated
        sync_parser.add_argument("--emails-only", \
                                 action='store_true', dest='only_emails', \
                                 default=False, help= 'Only sync emails.')
        
        # activate the resume mode --restart is deprecated
        sync_parser.add_argument("--chats-only", \
                                 action='store_true', dest='only_chats', \
                                 default=False, help= 'Only sync chats.')
        
        sync_parser.add_argument("-e", "--encrypt", \
                                 help="encrypt stored email messages in the database.",\
                                 action='store_true',dest="encrypt", default=False)
        
        sync_parser.add_argument("-c", "--check-db", metavar = "VAL", \
                          help="enable/disable the removal from the gmvault db of the emails "\
                               "that have been deleted from the given gmail account. VAL = yes or no.",\
                          dest="db_cleaning", default=None)
        
        sync_parser.add_argument("-m", "--multiple-db-owner", \
                                 help="Allow the email database to be synchronized with emails from multiple accounts.",\
                                 action='store_true',dest="allow_mult_owners", default=False)
        
        # activate the restart mode
        sync_parser.add_argument("--no-compression", \
                                 action='store_false', dest='compression', \
                                 default=True, help= 'disable email storage compression (gzip).')
        
        sync_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        sync_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        sync_parser.add_argument("--debug", "-debug", \
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
        rest_parser.add_argument('-t', '-type', '--type', \
                                 action='store', dest='type', \
                                 default='full', help='type of restoration: full|quick. (default: full)')
        
        # add a label
        rest_parser.add_argument('-a', '--apply-label' , \
                                 action='store', dest='apply_label', \
                                 default=None, help='Apply a label to restored emails')
        
        # activate the resume mode --restart is deprecated
        rest_parser.add_argument("--resume", "--restart", \
                                 action='store_true', dest='restart', \
                                 default=False, help= 'Restart from the last saved gmail id.')
                                 
        # activate the resume mode --restart is deprecated
        rest_parser.add_argument("--emails-only", \
                                 action='store_true', dest='only_emails', \
                                 default=False, help= 'Only sync emails.')
        
        # activate the resume mode --restart is deprecated
        rest_parser.add_argument("--chats-only", \
                                 action='store_true', dest='only_chats', \
                                 default=False, help= 'Only sync chats.')
        
        rest_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
               
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        rest_parser.add_argument("-y", "--oauth2", \
                          help="use oauth for authentication. (default recommended method)",\
                          action='store_const', dest="oauth2_token", const='empty', default='not_seen')

        rest_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action= 'store_const' , dest="passwd", const='empty', default='not_seen')

        rest_parser.add_argument("--renew-oauth2-tok", \
                          help="renew the stored oauth token (two legged or normal) via an interactive authentication session.",
                          action= 'store_const' , dest="oauth2_token", const='renew')

        rest_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        rest_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        rest_parser.add_argument("--debug", "-debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        rest_parser.set_defaults(verb='restore')
    
        rest_parser.epilogue = REST_HELP_EPILOGUE
        
        # check_db command
        check_parser = subparsers.add_parser('check', \
                                            help='check and clean the gmvault-db disk database.')

        #email argument
        check_parser.add_argument('email', \
                                 action='store', default='empty_$_email', help='gmail account against which to check.')
        
        check_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)
     
        # for both when seen add const empty otherwise not_seen
        # this allow to distinguish between an empty value and a non seen option
        check_parser.add_argument("-y", "--oauth2", \
                          help="use oauth for authentication. (default recommended method)",\
                          action='store_const', dest="oauth2_token", const='empty', default='not_seen')

        check_parser.add_argument("-p", "--passwd", \
                          help="use interactive password authentication. (not recommended)",
                          action= 'store_const' , dest="passwd", const='empty', default='not_seen')

        check_parser.add_argument("--renew-oauth2-tok", \
                          help="renew the stored oauth token (two legged or normal) via an interactive authentication session.",
                          action= 'store_const' , dest="oauth2_token", const='renew')

        check_parser.add_argument("--server", metavar = "HOSTNAME", \
                              action='store', help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        check_parser.add_argument("--port", metavar = "PORT", \
                              action='store', help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        check_parser.add_argument("--debug", "-debug", \
                              action='store_true', help="Activate debugging info",\
                              dest="debug", default=False)
        
        check_parser.set_defaults(verb='check')
        
        # export command
        export_parser = subparsers.add_parser('export', \
                                            help='Export the gmvault-db database to another format.')

        export_parser.add_argument('output_dir', \
                                   action='store', help='destination directory to export to.')

        export_parser.add_argument("-d", "--db-dir", \
                                 action='store', help="Database root directory. (default: $HOME/gmvault-db)",\
                                 dest="db_dir", default= self.DEFAULT_GMVAULT_DB)

        export_parser.add_argument('-t', '-type', '--type', \
                          action='store', dest='type', \
                          default='mbox', help='type of export: %s. (default: mbox)' % self.EXPORT_TYPE_NAMES)

        export_parser.add_argument('-l', '--label', \
                                   action='append', dest='label', \
                                   default=None,
                                   help='specify a label to export')
        export_parser.add_argument("--debug", "-debug", \
                       action='store_true', help="Activate debugging info",\
                       dest="debug", default=False)

        export_parser.set_defaults(verb='export')
        
        export_parser.epilogue = EXPORT_HELP_EPILOGUE

        return parser
      
    @classmethod
    def _parse_common_args(cls, options, parser, parsed_args, list_of_types = []): #pylint:disable=W0102
        """
           Parse the common arguments for sync and restore
        """
        #add email
        parsed_args['email']            = options.email
        
        parsed_args['debug']            = options.debug
        
        parsed_args['restart']          = options.restart
        
        #user entered both authentication methods
        if options.passwd == 'empty' and (options.oauth2_token == 'empty'):
            parser.error('You have to use one authentication method. '\
                         'Please choose between OAuth2 and password (recommend OAuth2).')
        
        # user entered no authentication methods => go to default oauth
        if options.passwd == 'not_seen' and options.oauth2_token == 'not_seen':
            #default to xoauth
            options.oauth2_token = 'empty'
            
        # add passwd
        parsed_args['passwd']           = options.passwd

        # add oauth2 tok
        if options.oauth2_token == 'empty':
            parsed_args['oauth2']      = options.oauth2_token
        elif options.oauth2_token == 'renew':
            parsed_args['oauth2'] = 'renew'

        #add ops type
        if options.type:
            tempo_list = ['auto']
            tempo_list.extend(list_of_types)
            if options.type.lower() in tempo_list:
                parsed_args['type'] = options.type.lower()
            else:
                parser.error('Unknown type for command %s. The type should be one of %s' \
                             % (parsed_args['command'], list_of_types))
        
        #add db_dir
        parsed_args['db-dir']           = options.db_dir

        LOG.critical("Use gmvault-db located in %s.\n" % (parsed_args['db-dir'])) 
        
        # add host
        parsed_args['host']             = options.host
        
        #convert to int if necessary
        port_type = type(options.port)
        
        try:
            if port_type == type('s') or port_type == type("s"):
                port = int(options.port)
            else:
                port = options.port
        except Exception, _: #pylint:disable=W0703
            parser.error("--port option %s is not a number. Please check the port value" % (port))
            
        # add port
        parsed_args['port']             = port
             
        return parsed_args
    
    def parse_args(self): #pylint: disable=R0912
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
                parsed_args['request']  = { 'type': 'gmail', 'req' : self._clean_imap_or_gm_request(options.gmail_request)}
            else:
                parsed_args['request']  = { 'type':'imap',  'req' : self._clean_imap_or_gm_request(options.imap_request)}
                
            # handle emails or chats only
            if options.only_emails and options.only_chats:
                parser.error("--emails-only and --chats-only cannot be used together. Please choose one.")
           
            parsed_args['emails_only'] = options.only_emails
            parsed_args['chats_only']  = options.only_chats
        
            # add db-cleaning
            # if request passed put it False unless it has been forced by the user
            # default is True (db-cleaning done)
            #default 
            parsed_args['db-cleaning'] = True
            
            # if there is a value then it is forced
            if options.db_cleaning: 
                parsed_args['db-cleaning'] = parser.convert_to_boolean(options.db_cleaning)
            
            #elif parsed_args['request']['req'] != 'ALL' and not options.db_cleaning:
            #    #else if we have a request and not forced put it to false
            #    parsed_args['db-cleaning'] = False
                
            if parsed_args['db-cleaning']:
                LOG.critical("Activate Gmvault db cleaning.")
            else:
                LOG.critical("Disable deletion of emails that are in Gmvault db and not anymore in Gmail.")
                
            #add encryption option
            parsed_args['encrypt'] = options.encrypt

            #add ownership checking
            parsed_args['ownership_control'] = not options.allow_mult_owners
            
            #compression flag
            parsed_args['compression'] = options.compression
                
                
        elif parsed_args.get('command', '') == 'restore':
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.RESTORE_TYPES)
            
            # apply restore labels if there is any
            parsed_args['apply_label'] = options.apply_label
            
            parsed_args['restart'] = options.restart
            
            # handle emails or chats only
            if options.only_emails and options.only_chats:
                parser.error("--emails-only and --chats-only cannot be used together. Please choose one.")
           
            parsed_args['emails_only'] = options.only_emails
            parsed_args['chats_only']  = options.only_chats
            
        elif parsed_args.get('command', '') == 'check':
            
            #add defaults for type
            options.type    = 'full'
            options.restart = False
            
            # parse common arguments for sync and restore
            self._parse_common_args(options, parser, parsed_args, self.CHECK_TYPES)
    
        elif parsed_args.get('command', '') == 'export':
            parsed_args['labels']     = options.label
            parsed_args['db-dir']     = options.db_dir
            parsed_args['output-dir'] = options.output_dir
            if options.type.lower() in self.EXPORT_TYPES:
                parsed_args['type'] = options.type.lower()
            else:
                parser.error('Unknown type for command export. The type should be one of %s' % self.EXPORT_TYPE_NAMES)
            parsed_args['debug'] = options.debug

        elif parsed_args.get('command', '') == 'config':
            pass
    
        #add parser
        parsed_args['parser'] = parser
        
        return parsed_args
    
    @classmethod
    def _clean_imap_or_gm_request(cls, request):
        """
           Clean request passed by the user with the option --imap-req or --gmail-req.
           Windows batch script preserve the single quote and unix shell doesn't.
           If the request starts and ends with single quote eat them.
        """
        LOG.debug("clean_imap_or_gm_request. original request = %s\n" % (request))
        
        if request and (len(request) > 2) and (request[0] == "'" and request[-1] == "'"):
            request =  request[1:-1]
            
        LOG.debug("clean_imap_or_gm_request. processed request = %s\n" % (request))
        return request
    
    @classmethod
    def _export(cls, args):
        """
           Export gmvault-db into another format
        """
        export_type = cls.EXPORT_TYPES[args['type']]
        output_dir = export_type(args['output-dir'])
        LOG.critical("Export gmvault-db as a %s mailbox." % (args['type']))
        exporter = gmvault_export.GMVaultExporter(args['db-dir'], output_dir,
            labels=args['labels'])
        exporter.export()
        output_dir.close()

    @classmethod
    def _restore(cls, args, credential):
        """
           Execute All restore operations
        """
        LOG.critical("Connect to Gmail server.\n")
        # Create a gmvault releaving read_only_access
        restorer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential, read_only_access = False)
        
        #full sync is the first one
        if args.get('type', '') == 'full':
            
            #call restore
            labels = [args['apply_label']] if args['apply_label'] else []
            restorer.restore(extra_labels = labels, restart = args['restart'], \
                             emails_only = args['emails_only'], chats_only = args['chats_only'])
            
        elif args.get('type', '') == 'quick':
            
            #take the last two to 3 months depending on the current date
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(gmvault_utils.get_conf_defaults().getint("Restore", "quick_days", 8))
            
            starting_dir = gmvault_utils.get_ym_from_datetime(begin)
            
            #call restore
            labels = [args['apply_label']] if args['apply_label'] else []
            restorer.restore(pivot_dir = starting_dir, extra_labels = labels, restart = args['restart'], \
                             emails_only = args['emails_only'], chats_only = args['chats_only'])
        
        else:
            raise ValueError("Unknown synchronisation mode %s. Please use full (default), quick.")
        
        #print error report
        LOG.critical(restorer.get_operation_report()) 
            
    @classmethod        
    def _sync(cls, args, credential):
        """
           Execute All synchronisation operations
        """
        LOG.critical("Connect to Gmail server.\n")
        
        # handle credential in all levels
        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                   args['email'], credential, read_only_access = True, \
                                   use_encryption = args['encrypt'])
        #full sync is the first one
        if args.get('type', '') == 'full':
        
            #choose full sync. Ignore the request
            syncer.sync({ 'mode': 'full', 'type': 'imap', 'req': 'ALL' } , compress_on_disk = args['compression'], \
                        db_cleaning = args['db-cleaning'], ownership_checking = args['ownership_control'],\
                        restart = args['restart'], emails_only = args['emails_only'], chats_only = args['chats_only'])
        
        elif args.get('type', '') == 'auto':
        
            #choose auto sync. imap request = ALL and restart = True
            syncer.sync({ 'mode': 'auto', 'type': 'imap', 'req': 'ALL' } , compress_on_disk = args['compression'], \
                        db_cleaning = args['db-cleaning'], ownership_checking = args['ownership_control'],\
                        restart = True, emails_only = args['emails_only'], chats_only = args['chats_only'])
              
        elif args.get('type', '') == 'quick':
            
            #sync only the last x days (taken in defaults) in order to be quick 
            #(cleaning is import here because recent days might move again
            
            # today - 2 months
            today = datetime.date.today()
            begin = today - datetime.timedelta(gmvault_utils.get_conf_defaults().getint("Sync", "quick_days", 8))
            
            LOG.critical("Quick sync mode. Check for new emails since %s." % (begin.strftime('%d-%b-%Y')))
            
            # today + 1 day
            end   = today + datetime.timedelta(1)
            
            req   = { 'type' : 'imap', \
                      'req'  : syncer.get_imap_request_btw_2_dates(begin, end), \
                      'mode' : 'quick'}
            
            syncer.sync( req, \
                         compress_on_disk = args['compression'], \
                         db_cleaning = args['db-cleaning'], \
                         ownership_checking = args['ownership_control'], restart = args['restart'], \
                         emails_only = args['emails_only'], chats_only = args['chats_only'])
            
        elif args.get('type', '') == 'custom':
            
            #convert args to unicode
            u_str = gmvault_utils.convert_argv_to_unicode(args['request']['req'])
            args['request']['req']     = u_str
            args['request']['charset'] = 'utf-8' #for the moment always utf-8
            args['request']['mode']    = 'custom'

            # pass an imap request. Assume that the user know what to do here
            LOG.critical("Perform custom synchronisation with %s request: %s.\n" \
                         % (args['request']['type'], args['request']['req']))
            
            syncer.sync(args['request'], compress_on_disk = args['compression'], db_cleaning = args['db-cleaning'], \
                        ownership_checking = args['ownership_control'], restart = args['restart'], \
                        emails_only = args['emails_only'], chats_only = args['chats_only'])
        else:
            raise ValueError("Unknown synchronisation mode %s. Please use full (default), quick or custom.")
        
        
        #print error report
        LOG.critical(syncer.get_operation_report())
    
    @classmethod
    def _check_db(cls, args, credential):
        """
           Check DB
        """
        LOG.critical("Connect to Gmail server.\n")
        
        # handle credential in all levels
        checker = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                   args['email'], credential, read_only_access = True)
        
        checker.check_clean_db(db_cleaning = True)
            

    def run(self, args): #pylint:disable=R0912
        """
           Run the grep with the given args 
        """
        on_error       = True
        die_with_usage = True
        
        try:
            if args.get('command') not in ('export'):
                credential = CredentialHelper.get_credential(args)
            
            if args.get('command', '') == 'sync':
                self._sync(args, credential)
                
            elif args.get('command', '') == 'restore':
                
                self._restore(args, credential)
            
            elif args.get('command', '') == 'check':
                
                self._check_db(args, credential)
                
            elif args.get('command', '') == 'export':

                self._export(args)

            elif args.get('command', '') == 'config':
                
                LOG.critical("Configure something. TBD.\n")
            
            on_error = False
        
        except KeyboardInterrupt, _:
            LOG.critical("\nCTRL-C. Stop all operations.\n")
            on_error = False
        except socket.error:
            LOG.critical("Error: Network problem. Please check your gmail server hostname,"\
                         " the internet connection or your network setup.\n")
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
            die_with_usage = False
        except imaplib.IMAP4.error, imap_err:
            #bad login or password
            if str(imap_err) in ['[AUTHENTICATIONFAILED] Invalid credentials (Failure)', \
                                 '[ALERT] Web login required: http://support.google.com/'\
                                 'mail/bin/answer.py?answer=78754 (Failure)', \
                                 '[ALERT] Invalid credentials (Failure)'] :
                LOG.critical("ERROR: Invalid credentials, cannot login to the gmail server."\
                             " Please check your login and password or xoauth token.\n")
                die_with_usage = False
            else:
                LOG.critical("Error: %s. \n" % (imap_err) )
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")
        except Exception, err:
            LOG.critical("Error: %s. \n" % (err) )
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
            die_with_usage = False
        finally: 
            if on_error:
                if die_with_usage:
                    args['parser'].die_with_usage()
                sys.exit(1)
 
def init_logging():
    """
       init logging infrastructure
    """       
    #setup application logs: one handler for stdout and one for a log file
    log_utils.LoggerFactory.setup_cli_app_handler(log_utils.STANDALONE, activate_log_file=False, file_path="./gmvault.log") 
    
def activate_debug_mode():
    """
       Activate debugging logging
    """
    LOG.critical("Debugging logs are going to be saved in file %s/gmvault.log.\n" % os.getenv("HOME","."))
    log_utils.LoggerFactory.setup_cli_app_handler(log_utils.STANDALONE, activate_log_file=True, \
                               console_level= 'DEBUG', file_path="%s/gmvault.log" % os.getenv("HOME","."))

def sigusr1_handler(signum, frame): #pylint:disable=W0613
    """
      Signal handler to get stack trace if the program is stuck
    """

    filename = './gmvault.traceback.txt'

    print("GMVAULT: Received SIGUSR1 -- Printing stack trace in %s..." %
          os.path.abspath(filename))

    with open(filename, 'a') as f:
        traceback.print_stack(file=f)

def register_traceback_signal():
    """ To register a USR1 signal allowing to get stack trace """
    signal.signal(signal.SIGUSR1, sigusr1_handler)

def setup_default_conf():
    """
       set the environment GMVAULT_CONF_FILE which is necessary for Conf object
    """
    gmvault_utils.get_conf_defaults() # force instanciation of conf to load the defaults

def bootstrap_run():
    """ temporary bootstrap """
    
    init_logging()

    #force argv[0] to gmvault
    sys.argv[0] = "gmvault"
    
    LOG.critical("")
    
    gmvlt = GMVaultLauncher()
    
    args = gmvlt.parse_args()

    #activate debug if enabled
    if args['debug']:
        LOG.critical("Activate debugging information.")
        activate_debug_mode()
    
    # force instanciation of conf to load the defaults
    gmvault_utils.get_conf_defaults() 
    
    gmvlt.run(args)
   
    
if __name__ == '__main__':
     
    #import memdebug
    
    #memdebug.start(8080)
    #import sys
    #print("sys.argv=[%s]" %(sys.argv))
    
    register_traceback_signal()
    
    bootstrap_run()
    
    #sys.exit(0)

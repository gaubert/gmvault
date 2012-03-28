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
import os
import getpass

from cmdline_utils  import CmdLineParser
import log_utils
import imaplib
import blowfish
import oauth_utils
import gmvault_utils
import gmvault




HELP_USAGE = """ gmv [options]
                                     
Arguments: None"""

HELP_EPILOGUE = """Examples:

a) full synchronisation with email and password login

#> gmvault --email foo.bar@gmail.com --passwd vrysecrtpasswd 

b) full synchronisation for german users that have to use googlemail instead of gmail

#> gmvault --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd

c) restrict synchronisation with an IMAP request

#> gmvault --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' --email foo.bar@gmail.com --passwd sosecrtpasswd 

"""

LOG = log_utils.LoggerFactory.get_logger('gmv')

def empty_handling(option, opt_str, value, parser):
    """
       to differenciate between a seen and non seen passwd command
    """
    # there is a passwd but it might be empty
    setattr(parser.values, option.dest, 'empty')

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
        
        parser.add_option("-S", "--sync", help = "Full synchronisation between gmail with local db. (default sync mode).", \
                          action ="store_true", dest="sync", default= False)
        
        parser.add_option("-Q", "--quick-sync", help = "Quick synchronisation between  gmail with local db.", \
                          action ="store_true", dest="qsync", default= False)
        
        parser.add_option("-N", "--inc-sync", help = "Incremental synchronisation between gmail with local db.", \
                          action ="store_true", dest="isync", default= False)
        
        parser.add_option("-i", "--imap-server", metavar = "HOSTNAME", \
                          help="Gmail imap server hostname. (default: imap.gmail.com)",\
                          dest="host", default="imap.gmail.com")
        
        parser.add_option("-t", "--imap-port", metavar = "PORT", \
                          help="Gmail imap server port. (default: 993)",\
                          dest="port", default=993)
        
        parser.add_option("-l", "--email", \
                          help="Gmail email.",\
                          dest="email", default=None)
        
        parser.add_option("-p", "--passwd",
                          action="callback", callback = empty_handling, dest="passwd", default='not_seen')
        
        parser.add_option("--save-passwd", \
                          help="Save gmail password in conf file.",\
                          action="store_true", dest="save_passwd", default=False)
        
        parser.add_option("--interactive", \
                          help="force interactive mode to redefine the password",\
                          action="store_true", dest="force_interactive", default=False)
        
        parser.add_option("-r", "--imap-request", metavar = "REQ", \
                          help="Imap request to restrict sync. (default: ALL)",\
                          dest="request", default="ALL")
        
        parser.add_option("-o", "--oauth-token", metavar = "TOK", \
                          help="Oauth-token.",\
                          action="callback", callback = empty_handling, dest="oauth_token", default='not_seen')
        
        
        parser.add_option("-d", "--db-dir", \
                          help="Database root directory. (default: ./gmvault-db)",\
                          dest="db_dir", default="./gmvault-db")
        
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
        except Exception, _:
            parser.error("--port option %s is not a number. Please check the port value" % (port))
            
        
        # add port
        parsed_args['port']             = port
        
        if options.email == None:
            parser.error("--email (-l) is a mandatory option. Please pass your email address")
        
        # add login
        parsed_args['email']            = options.email
        
        if options.passwd == 'empty' and options.oauth_token == 'empty':
            parser.error('You have to use one credential method. Please choose between xoauth and password (recommend xoauth).')
        
        # handle the credential
        if options.passwd == 'not_seen' and options.oauth_token == 'not_seen':
            #default to xoauth
            LOG.critical('Default to xoauth authentication')
            options.oauth_token = 'empty'
            
        
        
        # Cannot have passwd and oauth-token at the same time
        #if options.passwd and options.oauth_token:
        #    self.error("Only one authentication mode can be used (password or oauth-token)")
        
        # add passwd
        parsed_args['passwd']            = options.passwd
        
        # add imap request
        parsed_args['request']           = options.request

        # add oauth token
        parsed_args['oauth_token']       = options.oauth_token
        
        # add passwd
        parsed_args['db-dir']            = options.db_dir
        
        # add save_password
        parsed_args['save_passwd']       = options.save_passwd
        
        #force interactive mode
        parsed_args['force_interactive'] = options.force_interactive
        
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
    
    
    GMVAULT_DIR    = "GMVAULT_DIR"

    @classmethod 
    @gmvault_utils.memoized
    def get_home_dir_path(cls):
        """
           Get the Home dir
        """
        gmvault_dir = os.getenv(cls.GMVAULT_DIR, None)
    
        # check by default in user[HOME]
        if not gmvault_dir:
            LOG.info("no ENV variable $GMVAULT_DIR defined. Set by default $GMVAULT_DIR to $HOME/.gmvault")
            gmvault_dir = "%s/.gmvault" % (os.getenv("HOME", "."))
        
        #create dir if not there
        gmvault_utils.makedirs(gmvault_dir)
    
        return gmvault_dir
    
    
    @classmethod
    def get_secret(cls):
        """
           Get a secret from secret file or generate it
        """
        secret_file_path = '%s/token.sec' % (cls.get_home_dir_path())
        if os.path.exists(secret_file_path):
            secret = open(secret_file_path).read()
        else:
            secret = gmvault_utils.make_password()
            fdesc = open(secret_file_path, 'w+')
            fdesc.write(secret)
            fdesc.close()
        
        return secret
    
    @classmethod
    def store_passwd(cls, email, passwd):
        """
        """
        passwd_file = '%s/%s.passwd' % (cls.get_home_dir_path(), email)
    
        fdesc = open(passwd_file, "w+")
        
        cipher       = blowfish.Blowfish(cls.get_secret())
        cipher.initCTR()
    
        fdesc.write(cipher.encryptCTR(passwd))
    
        fdesc.close()
        
    @classmethod
    def store_oauth_credentials(cls, email, token, secret):
        """
        """
        oauth_file = '%s/%s.oauth' % (cls.get_home_dir_path(), email)
    
        fdesc = open(oauth_file, "w+")
        
        fdesc.write(token)
        fdesc.write('::')
        fdesc.write(secret)
    
        fdesc.close()
    
    @classmethod
    def read_password(cls, email):
        """
           Read password credentials
           Look for the defined in env GMVAULT_DIR so by default to ~/.gmvault
           Look for file GMVAULT_DIR/email.passwd
        """
        gmv_dir = cls.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_passwd_file_path = "%s/%s.passwd" % (gmv_dir, email)

        password = None
        if os.path.exists(user_passwd_file_path):
            passwd_file  = open(user_passwd_file_path)
            
            password = passwd_file.read()
            cipher       = blowfish.Blowfish(cls.get_secret())
            cipher.initCTR()
            password     = cipher.decryptCTR(password)

            LOG.debug("password=[%s]" % (password))
        
        return password
    
    @classmethod
    def read_oauth_tok_sec(cls, email):
        """
           Read oauth token secret credential
           Look for the defined in env GMVAULT_DIR so by default to ~/.gmvault
           Look for file GMVAULT_DIR/email.oauth
        """
        gmv_dir = cls.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth" % (gmv_dir, email)

        token  = None
        secret = None
        if os.path.exists(user_oauth_file_path):
            oauth_file  = open(user_oauth_file_path)
            token, secret = oauth_file.read().split('::')
            LOG.debug("token=[%s], secret=[%s]" % (token, secret))
        
        if token: token   = token.strip()
        if secret: secret = secret.strip() 
        
        return token, secret
            
    def get_credential(self, args, test_mode = {'activate': False, 'value' : 'test_password'}):
        """
           Deal with the credentials.
           1) Password
           --passwd passed. If --passwd passed and not password given if no password saved go in interactive mode
           2) XOAuth Token
        """
        
        
        credential = { }
        
        #first check that there is an email
        if not args.get('email', None):
                raise Exception("No email passed, Need to pass an email")
        
        if args['passwd'] == 'empty': 
            # --passwd is here so look if there is a passwd in conf file 
            # or go in interactive mode

            # --passwd try to read password in conf file otherwise go to interactive mode and save it
            passwd = None
            # no interactive and no forced save password so try to read it
            if not args['force_interactive'] and not args['save_passwd']:
                #try to read the password
                passwd = self.read_password(args['email'])
            
            if not passwd: # go to interactive mode
                if not test_mode.get('activate', False):
                    passwd = getpass.getpass('Please enter gmail password for %s and press enter:' % (args['email']))
                else:
                    passwd = test_mode.get('value', 'no_password_given')
                    
                credential = { 'type' : 'passwd', 'value' : passwd}
                
                #store it in dir if asked for --save_passwd
                if args['save_passwd']:
                    self.store_passwd(args['email'], passwd)
                    credential['option'] = 'saved'
            else:
                credential = { 'type' : 'passwd', 'value' : passwd, 'option':'read' }
                               
        elif args['passwd'] == 'not_seen' and args['oauth_token']:
            # get token secret
            # if they are in a file then no need to call get_oauth_tok_sec
            # will have to add 2 legged or 3 legged
            token, secret = self.read_oauth_tok_sec(args['email'])
           
            if not token: 
                token, secret = oauth_utils.get_oauth_tok_sec(args['email'], use_webbrowser = True)
                print('token = %s, secret = %s' % (token,secret) )
                #store newly created token
                self.store_oauth_credentials(args['email'], token, secret)
                
            xoauth_req = oauth_utils.generate_xoauth_req(token, secret, args['email'])

            credential = { 'type' : 'xoauth', 'value' : xoauth_req, 'option':None }
                        
        return credential  
    
    
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
    
    credential = gmvlt.get_credential(args)
    
    gmvlt.run(args, credential)
   
    
if __name__ == '__main__':
    
    bootstrap_run()
    
    sys.exit(0)

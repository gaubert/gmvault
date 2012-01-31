'''
Created on Jan 31, 2012

@author: guillaume.aubert@gmail.com
'''
import socket
import sys
import os
import getpass

import argparse
import log_utils
import imaplib
import blowfish
import oauth_utils
import gmvault_utils
import gmvault

from sandbox  import CmdLineParser

SYNC_HELP_EPILOGUE = """Examples:

a) full synchronisation with email and password login

#> gmvault --email foo.bar@gmail.com --passwd vrysecrtpasswd 

b) full synchronisation for german users that have to use googlemail instead of gmail

#> gmvault --imap-server imap.googlemail.com --email foo.bar@gmail.com --passwd sosecrtpasswd

c) restrict synchronisation with an IMAP request

#> gmvault --imap-request 'Since 1-Nov-2011 Before 10-Nov-2011' --email foo.bar@gmail.com --passwd sosecrtpasswd 

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
        parser = CmdLineParser()
    
        subparsers = parser.add_subparsers(help='commands')
        
        # A sync command
        sync_parser = subparsers.add_parser('sync', formatter_class=argparse.ArgumentDefaultsHelpFormatter, help='synchronize with given gmail account')
        #email argument can be optional so it should be an option
        sync_parser.add_argument('-l', '--email', action='store', dest='email', default='from-config', help='email to sync with')
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
        restore_parser = subparsers.add_parser('restore', help='restore email to a given email account')
        restore_parser.add_argument('-l', '--email', action='store', default='from-config', help='email to sync with')
        
        # restore typ
        restore_parser.add_argument('-t','--type', action='store', default='full-restore', help='type of synchronisation')
        
        restore_parser.add_argument("-i", "--imap-server", metavar = "HOSTNAME", \
                              help="Gmail imap server hostname. (default: imap.gmail.com)",\
                              dest="host", default="imap.gmail.com")
            
        restore_parser.add_argument("-p", "--imap-port", metavar = "PORT", \
                              help="Gmail imap server port. (default: 993)",\
                              dest="port", default=993)
        
        restore_parser.set_defaults(verb='restore')
        
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
    
    print(args)
    
    #credential = gmvlt.get_credential(args)
    
    #gmvlt.run(args, credential)
   
    
if __name__ == '__main__':
    
    import sys
    sys.argv = ['gmvault.py', 'sync']
    
    bootstrap_run()
    
    sys.exit(0)
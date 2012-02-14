'''
Created on Jan 30, 2012

@author: guillaume.aubert@gmail.com
'''

import argparse
import sys

import os
import getpass

import log_utils
import blowfish
import oauth_utils
import gmvault_utils

LOG = log_utils.LoggerFactory.get_logger('cmdline_utils')

class CredentialHelper(object):
    
    @classmethod
    def get_secret(cls):
        """
           Get a secret from secret file or generate it
        """
        secret_file_path = '%s/token.sec' % (gmvault_utils.get_home_dir_path())
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
        passwd_file = '%s/%s.passwd' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = open(passwd_file, "w+")
        
        cipher       = blowfish.Blowfish(cls.get_secret())
        cipher.initCTR()
    
        fdesc.write(cipher.encryptCTR(passwd))
    
        fdesc.close()
        
    @classmethod
    def store_oauth_credentials(cls, email, token, secret):
        """
        """
        oauth_file = '%s/%s.oauth' % (gmvault_utils.get_home_dir_path(), email)
    
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
        gmv_dir = gmvault_utils.get_home_dir_path()
        
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
        gmv_dir = gmvault_utils.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth" % (gmv_dir, email)

        token  = None
        secret = None
        if os.path.exists(user_oauth_file_path):
            LOG.critical("Use oauth credentials from %s." % (user_oauth_file_path))
            
            oauth_file  = open(user_oauth_file_path)
            
            try:
                token, secret = oauth_file.read().split('::')
            except Exception, err:
                LOG.error("Error when reading oauth info from %s" % (user_oauth_file_path))
                
                LOG.exception(err)
                
                LOG.critical("Cannot read oauth credentials from %s. Force oauth credentials renewal." % (user_oauth_file_path))
        
        if token: token   = token.strip()
        if secret: secret = secret.strip() 
        
        return token, secret
            
    @classmethod
    def get_credential(cls, args, test_mode = {'activate': False, 'value' : 'test_password'}):
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
            if not args['save_passwd']:
                #try to read the password
                passwd = cls.read_password(args['email'])
            
            if not passwd: # go to interactive mode
                if not test_mode.get('activate', False):
                    passwd = getpass.getpass('Please enter gmail password for %s and press enter:' % (args['email']))
                else:
                    passwd = test_mode.get('value', 'no_password_given')
                    
                credential = { 'type' : 'passwd', 'value' : passwd}
                
                #store it in dir if asked for --save_passwd
                if args['save_passwd']:
                    cls.store_passwd(args['email'], passwd)
                    credential['option'] = 'saved'
            else:
                credential = { 'type' : 'passwd', 'value' : passwd, 'option':'read' }
                               
        elif args['passwd'] == 'not_seen' and args['oauth']:
            # get token secret
            # if they are in a file then no need to call get_oauth_tok_sec
            # will have to add 2 legged or 3 legged
            LOG.critical("Oauth will be used for authentication.\n")
            
            token, secret = cls.read_oauth_tok_sec(args['email'])
           
            if not token: 
                token, secret = oauth_utils.get_oauth_tok_sec(args['email'], use_webbrowser = True)
                print('token = %s, secret = %s' % (token,secret) )
                #store newly created token
                cls.store_oauth_credentials(args['email'], token, secret)
               
            LOG.debug("token=[%s], secret=[%s]" % (token, secret))
            
            xoauth_req =oauth_utils.generate_xoauth_req(token, secret, args['email'])
            
            LOG.critical("Successfully read oauth credentials.\n")

            credential = { 'type' : 'xoauth', 'value' : xoauth_req, 'option':None }
                        
        return credential

    @classmethod
    def get_xoauth_req_from_email(cls, email):
        """
           This will be used to reconnect after a timeout
        """
        token, secret = cls.read_oauth_tok_sec(email)
        if not token: 
            raise Exception("Error cannot read token, secret from")
        
        xoauth_req =oauth_utils.generate_xoauth_req(token, secret, email)
        
        return xoauth_req
        


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


    
    

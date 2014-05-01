'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2013>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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

 Module handling the xauth authentication.
 Strongly influenced by http://code.google.com/p/googlecl/source/browse/trunk/src/googlecl/service.py
 and xauth part of gyb http://code.google.com/p/got-your-back/source/browse/trunk/gyb.py

'''
import gdata.service
import webbrowser
import random
import time
import atom
import urllib

import os
import getpass

import gmv.log_utils as log_utils
import gmv.blowfish as blowfish
import gmv.gmvault_utils as gmvault_utils

LOG = log_utils.LoggerFactory.get_logger('oauth')


def get_2_legged_oauth_tok_sec():
    '''
       Get 2 legged token and secret
    '''
    tok = raw_input('Enter your domain\'s OAuth consumer key: ')
  
    sec = raw_input('Enter your domain\'s OAuth consumer secret: ')
      
    return tok, sec, "two_legged"
    

def get_oauth_tok_sec(email, use_webbrowser = False, debug=False):
    '''
       Generate token and secret
    '''
    
    scopes = ['https://mail.google.com/', # IMAP/SMTP client access
              'https://www.googleapis.com/auth/userinfo#email'] # Email address access (verify token authorized by correct account
    
    gdata_serv = gdata.service.GDataService()
    gdata_serv.debug = debug
    gdata_serv.source = 'gmvault '
    
    gdata_serv.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1, \
                                       consumer_key = 'anonymous', consumer_secret = 'anonymous')
    
    params = {'xoauth_displayname':'Gmvault - Backup your Gmail account'}
    try:
        request_token = gdata_serv.FetchOAuthRequestToken(scopes=scopes, extra_parameters = params)
    except gdata.service.FetchingOAuthRequestTokenFailed, err:
        if str(err).find('Timestamp') != -1:
            LOG.critical('Is your system clock up to date? See the FAQ http://code.google.com/p/googlecl/wiki/FAQ'\
                         '#Timestamp_too_far_from_current_time\n')
            
        LOG.critical("Received Error: %s.\n" % (err) )
        LOG.critical("=== Exception traceback ===")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
            
        return (None, None)
    
    url_params = {}
    domain = email[email.find('@')+1:]
    if domain.lower() != 'gmail.com' and domain.lower() != 'googlemail.com':
        url_params = {'hd': domain}
    
    auth_url = gdata_serv.GenerateOAuthAuthorizationURL(request_token=request_token, extra_params=url_params)
    
    #message to indicate that a browser will be opened
    raw_input('gmvault will now open a web browser page in order for you to grant gmvault access to your Gmail.\n'\
              'Please make sure you\'re logged into the correct Gmail account (%s) before granting access.\n'\
              'Press ENTER to open the browser. Once you\'ve granted access you can switch back to gmvault.' % (email))
    
    # run web browser otherwise print message with url
    if use_webbrowser:
        try:
            webbrowser.open(str(auth_url))  
        except Exception, err: #pylint: disable-msg=W0703
            LOG.critical("Error: %s.\n" % (err) )
            LOG.critical("=== Exception traceback ===")
            LOG.critical(gmvault_utils.get_exception_traceback())
            LOG.critical("=== End of Exception traceback ===\n")
        
        raw_input("You should now see the web page on your browser now.\n"\
                  "If you don\'t, you can manually open:\n\n%s\n\nOnce you've granted"\
                  " gmvault access, press the Enter key.\n" % (auth_url))
        
    else:
        raw_input('Please log in and/or grant access via your browser at %s '
                  'then hit enter.' % (auth_url))
    
    try:
        final_token = gdata_serv.UpgradeToOAuthAccessToken(request_token)
    except gdata.service.TokenUpgradeFailed:
        LOG.critical('Token upgrade failed! Could not get OAuth access token.\n Did you grant gmvault access in your browser ?')
        LOG.critical("=== Exception traceback ===")
        LOG.critical(gmvault_utils.get_exception_traceback())
        LOG.critical("=== End of Exception traceback ===\n")
        
        return (None, None)

    return (final_token.key, final_token.secret, "normal")

def generate_xoauth_req(a_token, a_secret, email, type):
    """
       generate the xoauth req from a user token and secret.
       Handle two_legged xoauth for admins.
    """
    nonce = str(random.randrange(2**64 - 1))
    timestamp = str(int(time.time()))
    if type == "two_legged": #2 legged oauth
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s' \
                                             % (email, urllib.quote(email)), 'GET')
         
        signature = gdata.gauth.generate_hmac_signature(http_request=request, consumer_key=a_token, consumer_secret=a_secret, \
                                                        timestamp=timestamp, nonce=nonce, version='1.0', next=None)
        return '''GET https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s oauth_consumer_key="%s",oauth_nonce="%s"'''\
               ''',oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_version="1.0"''' \
               % (email, urllib.quote(email), a_token, nonce, urllib.quote(signature), timestamp)
    else:
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/' % email, 'GET')
        signature = gdata.gauth.generate_hmac_signature(
            http_request=request, consumer_key='anonymous', consumer_secret='anonymous', timestamp=timestamp,
            nonce=nonce, version='1.0', next=None, token = a_token, token_secret= a_secret)
        return '''GET https://mail.google.com/mail/b/%s/imap/ oauth_consumer_key="anonymous",oauth_nonce="%s"'''\
               ''',oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_token="%s"'''\
               ''',oauth_version="1.0"''' \
               % (email, nonce, urllib.quote(signature), timestamp, urllib.quote(a_token))




class CredentialHelper(object):
    """
       Helper handling all credentials
    """
    SECRET_FILEPATH = '%s/token.sec' 
    
    @classmethod
    def get_secret_key(cls, a_filepath):
        """
           Get secret key if it is in the file otherwise generate it and save it
        """
        if os.path.exists(a_filepath):
            with open(a_filepath).read() as f:
                secret = f.read()
        else:
            secret = gmvault_utils.make_password()

            fdesc = os.open(a_filepath, os.O_CREAT|os.O_WRONLY, 0600)
            try:
                the_bytes = os.write(fdesc, secret)
            finally:
                os.close(fdesc) #close anyway

            if the_bytes < len(secret):
                raise Exception("Error: Cannot write secret in %s" % a_filepath)

        return secret
    
    @classmethod
    def store_passwd(cls, email, passwd):
        """
           Encrypt and store gmail password
        """
        passwd_file = '%s/%s.passwd' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = os.open(passwd_file, os.O_CREAT|os.O_WRONLY, 0600)
        
        cipher       = blowfish.Blowfish(cls.get_secret_key(cls.SECRET_FILEPATH % (gmvault_utils.get_home_dir_path())))
        cipher.initCTR()
    
        encrypted = cipher.encryptCTR(passwd)
        the_bytes = os.write(fdesc, encrypted)
    
        os.close(fdesc)
        
        if the_bytes < len(encrypted):
            raise Exception("Error: Cannot write password in %s" % (passwd_file))
        
    @classmethod
    def store_oauth_credentials(cls, email, token, secret, type):
        """
           store oauth_credentials
        """
        oauth_file = '%s/%s.oauth' % (gmvault_utils.get_home_dir_path(), email)
    
        fdesc = os.open(oauth_file, os.O_CREAT|os.O_WRONLY, 0600)
        
        os.write(fdesc, token)
        os.write(fdesc, '::')
        os.write(fdesc, secret)
        os.write(fdesc, '::')
        os.write(fdesc, type)
    
        os.close(fdesc)
    
    @classmethod
    def read_password(cls, email):
        """
           Read password credentials
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.passwd
        """
        gmv_dir = gmvault_utils.get_home_dir_path()

        #look for email.passwed in GMV_DIR
        user_passwd_file_path = "%s/%s.passwd" % (gmv_dir, email)

        password = None
        if os.path.exists(user_passwd_file_path):
            with open(user_passwd_file_path) as f:
                password = f.read()
            cipher       = blowfish.Blowfish(cls.get_secret_key(cls.SECRET_FILEPATH % (gmvault_utils.get_home_dir_path())))
            cipher.initCTR()
            password     = cipher.decryptCTR(password)

        return password

    @classmethod
    def read_oauth_tok_sec(cls, email):
        """
           Read oauth token secret credential
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.oauth
        """
        gmv_dir = gmvault_utils.get_home_dir_path()
        
        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth" % (gmv_dir, email)

        token  = None
        secret = None
        type   = None
        if os.path.exists(user_oauth_file_path):
            LOG.critical("Get XOAuth credential from %s.\n" % user_oauth_file_path)

            try:
                with open(user_oauth_file_path) as oauth_file:
                    oauth_result = oauth_file.read()
                if oauth_result:
                    oauth_result = oauth_result.split('::')
                    if len(oauth_result) == 2:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = "normal"
                    elif len(oauth_result) == 3:
                        token  = oauth_result[0]
                        secret = oauth_result[1]
                        type   = oauth_result[2]
            except Exception, _: #pylint: disable-msg=W0703              
                LOG.critical("Cannot read oauth credentials from %s. Force oauth credentials renewal." % user_oauth_file_path)
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")

        if token: token   = token.strip() #pylint: disable-msg=C0321
        if secret: secret = secret.strip()  #pylint: disable-msg=C0321
        if type: type = type.strip()

        return token, secret, type

    @classmethod
    def get_credential(cls, args, test_mode={'activate': False, 'value': 'test_password'}): #pylint: disable-msg=W0102
        """
           Deal with the credentials.
           1) Password
           --passwd passed. If --passwd passed and not password given if no password saved go in interactive mode
           2) XOAuth Token
        """
        credential = {}

        #first check that there is an email
        if not args.get('email', None):
            raise Exception("No email passed, Need to pass an email")
        
        if args['passwd'] in ['empty', 'store', 'renew']: 
            # --passwd is here so look if there is a passwd in conf file 
            # or go in interactive mode
            
            LOG.critical("Authentication performed with Gmail password.\n")
            
            passwd = cls.read_password(args['email'])
            
            #password to be renewed so need an interactive phase to get the new pass
            if not passwd or args['passwd'] in ['renew', 'store']: # go to interactive mode
                if not test_mode.get('activate', False):
                    passwd = getpass.getpass('Please enter gmail password for %s and press ENTER:' % (args['email']))
                else:
                    passwd = test_mode.get('value', 'no_password_given')
                    
                credential = { 'type' : 'passwd', 'value' : passwd}
                
                #store it in dir if asked for --store-passwd or --renew-passwd
                if args['passwd'] in ['renew', 'store']:
                    LOG.critical("Store password for %s in $HOME/.gmvault." % (args['email']))
                    cls.store_passwd(args['email'], passwd)
                    credential['option'] = 'saved'
            else:
                LOG.critical("Use password stored in $HOME/.gmvault dir (Storing your password here is not recommended).")
                credential = { 'type' : 'passwd', 'value' : passwd, 'option':'read' }
                               
        #elif args['passwd'] == 'not_seen' and args['oauth']:
        elif args['passwd'] in ('not_seen', None) and args['oauth'] in (None, 'empty', 'renew', 'not_seen'):
            # get token secret
            # if they are in a file then no need to call get_oauth_tok_sec
            # will have to add 2 legged 
            LOG.critical("Authentication performed with Gmail XOAuth token.\n")
            
            two_legged = args.get('two_legged', False) # 2 legged oauth
            
            token, secret, type = cls.read_oauth_tok_sec(args['email'])
           
            if not token or args['oauth'] == 'renew':
                
                if args['oauth'] == 'renew':
                    LOG.critical("Renew XOAuth token (normal or 2-legged). Initiate interactive session to get it from Gmail.\n")
                else:
                    LOG.critical("Initiate interactive session to get XOAuth normal or 2-legged token from Gmail.\n")
                
                if two_legged:
                    token, secret, type = get_2_legged_oauth_tok_sec()
                else:
                    token, secret, type = get_oauth_tok_sec(args['email'], use_webbrowser = True)
                
                if not token:
                    raise Exception("Cannot get XOAuth token from Gmail. See Gmail error message")
                #store newly created token
                cls.store_oauth_credentials(args['email'], token, secret, type)
               
            xoauth_req = generate_xoauth_req(token, secret, args['email'], type)
            
            LOG.critical("Successfully read oauth credentials.\n")

            credential = { 'type' : 'xoauth', 'value' : xoauth_req, 'option':None }
                        
        return credential

    @classmethod
    def get_xoauth_req_from_email(cls, email):
        """
           This will be used to reconnect after a timeout
        """
        token, secret, type = cls.read_oauth_tok_sec(email)
        if not token: 
            raise Exception("Error cannot read token, secret from")
        
        xoauth_req = generate_xoauth_req(token, secret, email, type)
        
        return xoauth_req

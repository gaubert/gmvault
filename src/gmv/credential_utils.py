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

 Module handling the xauth authentication.
 Strongly influenced by http://code.google.com/p/googlecl/source/browse/trunk/src/googlecl/service.py
 and xauth part of gyb http://code.google.com/p/got-your-back/source/browse/trunk/gyb.py

'''
import webbrowser
import json
import base64
import urllib #for urlencode
import urllib2

import os
import getpass

import gmv.log_utils as log_utils
import gmv.blowfish as blowfish
import gmv.gmvault_utils as gmvault_utils

LOG = log_utils.LoggerFactory.get_logger('credential_utils')

def generate_permission_url():
  """Generates the URL for authorizing access.

  This uses the "OAuth2 for Installed Applications" flow described at
  https://developers.google.com/accounts/docs/OAuth2InstalledApp

  Args:
    client_id: Client ID obtained by registering your app.
    scope: scope for access token, e.g. 'https://mail.google.com'
  Returns:
    A URL that the user should visit in their browser.
  """
  params = {}
  params['client_id']     = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "gmvault_client_id", "1070918343777-0eecradokiu8i77qfo8e3stbi0mkrtog.apps.googleusercontent.com")
  params['redirect_uri']  = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "redirect_uri", 'urn:ietf:wg:oauth:2.0:oob')
  params['scope']         = gmvault_utils.get_conf_defaults().get("GoogleOauth2","scope",'https://mail.google.com/')
  params['response_type'] = 'code'

  account_base_url = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "google_accounts_base_url", 'https://accounts.google.com')

  return '%s/%s?%s' % (account_base_url, 'o/oauth2/auth', gmvault_utils.format_url_params(params))

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
            with open(a_filepath) as f:
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
    def store_oauth2_credentials(cls, email, access_token, refresh_token, validity, type):
        """
           store oauth_credentials
        """
        oauth_file = '%s/%s.oauth2' % (gmvault_utils.get_home_dir_path(), email)

        # Open a file
        fdesc = os.open(oauth_file, os.O_RDWR|os.O_CREAT )

        #write new content
        fobj = os.fdopen(fdesc, "w")

        #empty file
        fobj.truncate()
        fobj.seek(0, os.SEEK_SET)


        the_obj = { "access_token"    : access_token,
                    "refresh_token"   : refresh_token,
                    "validity"        : validity,
                    "access_creation" : gmvault_utils.get_utcnow_epoch(),
                    "type"            : type}

        json.dump(the_obj, fobj)

        fobj.close()

    @classmethod
    def read_oauth2_tok_sec(cls, email):
        """
           Read oauth2 refresh token secret
           Look by default to ~/.gmvault
           Look for file ~/.gmvault/email.oauth2
        """
        gmv_dir = gmvault_utils.get_home_dir_path()

        #look for email.passwed in GMV_DIR
        user_oauth_file_path = "%s/%s.oauth2" % (gmv_dir, email)

        oauth_result = None

        if os.path.exists(user_oauth_file_path):
            LOG.critical("Get OAuth2 credential from %s.\n" % user_oauth_file_path)

            try:
                with open(user_oauth_file_path) as oauth_file:
                    oauth_result = json.load(oauth_file)
            except Exception, _: #pylint: disable-msg=W0703
                LOG.critical("Cannot read oauth credentials from %s. Force oauth credentials renewal." % user_oauth_file_path)
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")

        return oauth_result


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
                               
        # use oauth2
        elif args['passwd'] in ('not_seen', None) and args['oauth2'] in (None, 'empty', 'renew', 'not_seen'):
            # get access token and refresh token
            LOG.critical("Authentication performed with Gmail OAuth2 access token.\n")

            renew = True if args['oauth2'] == 'renew' else False

            #get the oauth2 credential
            credential = cls.get_oauth2_credential(args['email'], renew)

        return credential

    @classmethod
    def _get_oauth2_acc_tok_from_ref_tok(cls, refresh_token):
      """Obtains a new token given a refresh token.

      See https://developers.google.com/accounts/docs/OAuth2InstalledApp#refresh

      Args:
        client_id: Client ID obtained by registering your app.
        client_secret: Client secret obtained by registering your app.
        refresh_token: A previously-obtained refresh token.
      Returns:
        The decoded response from the Google Accounts server, as a dict. Expected
        fields include 'access_token', 'expires_in', and 'refresh_token'.
      """
      params = {}
      params['client_id'] = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "gmvault_client_id", "1070918343777-0eecradokiu8i77qfo8e3stbi0mkrtog.apps.googleusercontent.com")
      params['client_secret'] = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "gmvault_client_secret", "IVkl_pglv5cXzugpmnRNqtT7")
      params['refresh_token'] = refresh_token
      params['grant_type'] = 'refresh_token'

      account_base_url = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "google_accounts_base_url", 'https://accounts.google.com')

      request_url = '%s/%s' % (account_base_url, 'o/oauth2/token')

      try:
        response = urllib2.urlopen(request_url, urllib.urlencode(params)).read()
      except Exception, err: #pylint: disable-msg=W0703
        LOG.critical("Error: Problems when trying to connect to Google oauth2 endpoint: %s.\n" % (request_url))
        raise err

      json_resp = json.loads(response)

      LOG.debug("json_resp = %s" % (json_resp))

      return json_resp['access_token'], "normal"

    @classmethod
    def _get_authorization_tokens(cls, authorization_code):
        """Obtains OAuth access token and refresh token.

        This uses the application portion of the "OAuth2 for Installed Applications"
        flow at https://developers.google.com/accounts/docs/OAuth2InstalledApp#handlingtheresponse

        Args:
        client_id: Client ID obtained by registering your app.
        client_secret: Client secret obtained by registering your app.
        authorization_code: code generated by Google Accounts after user grants
            permission.
        Returns:
        The decoded response from the Google Accounts server, as a dict. Expected
        fields include 'access_token', 'expires_in', and 'refresh_token'.
        """
        params = {}
        params['client_id'] = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "gmvault_client_id", "1070918343777-0eecradokiu8i77qfo8e3stbi0mkrtog.apps.googleusercontent.com")
        params['client_secret'] = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "gmvault_client_secret", "IVkl_pglv5cXzugpmnRNqtT7")
        params['code'] = authorization_code
        params['redirect_uri'] = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "redirect_uri", 'urn:ietf:wg:oauth:2.0:oob')
        params['grant_type'] = 'authorization_code'

        account_base_url = gmvault_utils.get_conf_defaults().get("GoogleOauth2", "google_accounts_base_url", 'https://accounts.google.com')

        request_url = '%s/%s' % (account_base_url, 'o/oauth2/token')

        try:
            response = urllib2.urlopen(request_url, urllib.urlencode(params)).read()
        except Exception, err: #pylint: disable-msg=W0703
            LOG.critical("Error: Problems when trying to connect to Google oauth2 endpoint: %s." % (request_url))
            raise err

        return json.loads(response)

    @classmethod
    def _get_oauth2_tokens(cls, email, use_webbrowser = False, debug=False):
        '''
           Handle the OAUTH2 workflow sequence with either a new request or based on a refresh token
        '''

        #create permission url
        permission_url = generate_permission_url()

        #message to indicate that a browser will be opened
        raw_input('gmvault will now open a web browser page in order for you to grant gmvault access to your Gmail.\n'\
                  'Please make sure you\'re logged into the correct Gmail account (%s) before granting access.\n'\
                  'Press ENTER to open the browser.' % (email))

        # run web browser otherwise print message with url
        if use_webbrowser:
            try:
                webbrowser.open(str(permission_url))
            except Exception, err: #pylint: disable-msg=W0703
                LOG.critical("Error: %s.\n" % (err) )
                LOG.critical("=== Exception traceback ===")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")

            verification_code = raw_input("You should now see the web page on your browser now.\n"\
                      "If you don\'t, you can manually open:\n\n%s\n\nOnce you've granted"\
                      " gmvault access, enter the verification code and press enter:\n" % (permission_url))
        else:
            verification_code = raw_input('Please log in and/or grant access via your browser at %s '
                      'then enter the verification code and press enter:' % (permission_url))

        #request access and refresh token with the obtained verification code
        response = cls._get_authorization_tokens(verification_code)

        LOG.debug("get_authorization_tokens response %s" % (response))

        access_tok  = response['access_token']
        refresh_tok = response['refresh_token']
        validity    = response['expires_in'] #in sec

        return access_tok, refresh_tok, validity, "normal"

    @classmethod
    def _generate_oauth2_auth_string(cls, username, access_token, base64_encode=True):
        """Generates an IMAP OAuth2 authentication string.
        See https://developers.google.com/google-apps/gmail/oauth2_overview
        Args:
        username: the username (email address) of the account to authenticate
        access_token: An OAuth2 access token.
        base64_encode: Whether to base64-encode the output.
        Returns:
        The SASL argument for the OAuth2 mechanism.
        """
        auth_string = 'user=%s\1auth=Bearer %s\1\1' % (username, access_token)
        if base64_encode:
            auth_string = base64.b64encode(auth_string)
        return auth_string

    @classmethod
    def get_oauth2_credential(cls, email, renew_cred = False):
        """
        Used once the connection has been lost. Return an auth_str obtained from a refresh token or
        with the current access token if it is still valid
        :param email: user email used to load refresh token from peristent file
        :return: credential { 'type' : 'oauth2', 'value' : auth_str, 'option':None }
        """
        oauth2_creds = cls.read_oauth2_tok_sec(email)

        #workflow when you connect for the first time or want to renew the oauth2 credentials
        if not oauth2_creds or renew_cred:
                # No refresh token in stored so perform a new request
                if renew_cred:
                    LOG.critical("Renew OAuth2 token (normal). Initiate interactive session to get it from Gmail.\n")
                else:
                    LOG.critical("Initiate interactive session to get OAuth2 token from Gmail.\n")

                #interactive session with default browser initiated
                access_token, refresh_token, validity, type = cls._get_oauth2_tokens(email, use_webbrowser = True)

                if not access_token or not refresh_token:
                    raise Exception("Cannot get OAuth2 access token from Gmail. See Gmail error message")

                #store newly created token
                cls.store_oauth2_credentials(email, access_token, refresh_token, validity, type)
        else:

            # check if the access token is still valid otherwise renew it from the refresh token
            now = gmvault_utils.get_utcnow_epoch() #now time as epoch seconds
            tok_creation = oauth2_creds['access_creation'] #creation time as epoch seconds
            validity     = oauth2_creds['validity']

            LOG.debug("oauth2 creds = %s" % (oauth2_creds['refresh_token']))

            #access token is still valid then use it
            if  now < tok_creation + validity:
                LOG.debug("Access Token is still valid")
                access_token = oauth2_creds['access_token']
            else:
                #expired so request a new access token and store it
                LOG.debug("Access Token is expired. Renew it")
                # get a new access token based on refresh_token
                access_token, type = cls._get_oauth2_acc_tok_from_ref_tok(oauth2_creds['refresh_token'])
                # update stored information
                cls.store_oauth2_credentials(email, access_token, oauth2_creds['refresh_token'], validity, type)

        auth_str = cls._generate_oauth2_auth_string(email, access_token, base64_encode=False)

        LOG.debug("auth_str generated: %s" % (auth_str))
        LOG.debug("Successfully read oauth2 credentials with get_oauth2_credential_from_refresh_token\n")

        return { 'type' : 'oauth2', 'value' : auth_str, 'option':None }

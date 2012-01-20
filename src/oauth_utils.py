'''
Created on Jan 19, 2012

@author: guillaume.aubert@gmail.com

 Module handling the xauth authentication.
 Strongly influenced by http://code.google.com/p/googlecl/source/browse/trunk/src/googlecl/service.py
 and xauth part of gyb http://code.google.com/p/got-your-back/source/browse/trunk/gyb.py

'''
import sys
import gdata.service
import webbrowser
import random
import time
import atom
import urllib

import log_utils

LOG = log_utils.LoggerFactory.get_logger('oauth')

def get_oauth_tok_sec(email, a_webbrowser = None, debug=False):
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
    
    params = {'xoauth_displayname':'gmvault - Backup your Gmail account'}
    try:
        request_token = gdata_serv.FetchOAuthRequestToken(scopes=scopes, extra_parameters = params)
    except gdata.service.FetchingOAuthRequestTokenFailed, err:
        if str(err).find('Timestamp') != -1:
            LOG.critical('Is your system clock up to date? See the FAQ http://code.google.com/p/googlecl/wiki/FAQ'\
                         '#Timestamp_too_far_from_current_time')
        else:
            LOG.error('error %s' % (err))
            #LOG.error(err[0]['body'].strip() + '; Request token retrieval failed!')
        return (None, None)
    
    url_params = {}
    domain = email[email.find('@')+1:]
    if domain.lower() != 'gmail.com' and domain.lower() != 'googlemail.com':
        url_params = {'hd': domain}
    
    auth_url = gdata_serv.GenerateOAuthAuthorizationURL(request_token=request_token, extra_params=url_params)
    
    #message to indicate that a browser will be opened
    raw_input('gmvault will now open a web browser page in order for you to grant gmvault access to your Gmail.'\
              ' Please make sure you\'re logged in to the correct Gmail account before granting access. '\
              'Press enter to open the browser. Once you\'ve granted access you can switch back to gmvault.')
    
    # run web browser otherwise print message with url
    if a_webbrowser:
        try:
            a_webbrowser.open(str(auth_url))  
        except Exception, err:
            LOG.exception(err)
        
        raw_input("You should now see the web page on your browser now. "\
                  "If you don\'t, you can manually open:\n\n%s\n\nOnce you've granted gmvault access, press the Enter key.\n" % (auth_url))
        
    else:
        raw_input('Please log in and/or grant access via your browser at %s '
                  'then hit enter.' % (auth_url))
    
    try:
        final_token = gdata_serv.UpgradeToOAuthAccessToken(request_token)
    except gdata.service.TokenUpgradeFailed:
        print 'Failed to upgrade the token. Did you grant GYB access in your browser?'
        LOG.critical('Token upgrade failed! Could not get OAuth access token.\n Did you grant gmvault access in your browser ?')

        return (None, None)

    return (final_token.key, final_token.secret)

def generate_xoauth(token, secret, email, two_legged=False):
    nonce = str(random.randrange(2**64 - 1))
    timestamp = str(int(time.time()))
    if two_legged:
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s' % (email, urllib.quote(email)), 'GET')
         
        print(str(request))
        signature = gdata.gauth.generate_hmac_signature(http_request=request, consumer_key=token, consumer_secret=secret, \
                                                        timestamp=timestamp, nonce=nonce, version='1.0', next=None)
        return '''GET https://mail.google.com/mail/b/%s/imap/?xoauth_requestor_id=%s oauth_consumer_key="%s",oauth_nonce="%s",oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_version="1.0"''' % (email, urllib.quote(email), token, nonce, urllib.quote(signature), timestamp)
    else:
        request = atom.http_core.HttpRequest('https://mail.google.com/mail/b/%s/imap/' % email, 'GET')
        print(str(request))
        signature = gdata.gauth.generate_hmac_signature(
            http_request=request, consumer_key='anonymous', consumer_secret='anonymous', timestamp=timestamp,
            nonce=nonce, version='1.0', next=None, token=token, token_secret=secret)
        return '''GET https://mail.google.com/mail/b/%s/imap/ oauth_consumer_key="anonymous",oauth_nonce="%s",oauth_signature="%s",oauth_signature_method="HMAC-SHA1",oauth_timestamp="%s",oauth_token="%s",oauth_version="1.0"''' % (email, nonce, urllib.quote(signature), timestamp, urllib.quote(token))

if __name__ == '__main__':
    
    """
algo:
get key and secret
if key and secret in conf take it
otherwise generate them with get_oauth_tok_sec
save secret once you have it (encrypt or not ?)
generate xoauth everytime your connect to imap
do not use atom to create the request (no need to get a fake dependency
"""
    log_utils.LoggerFactory.setup_cli_app_handler(activate_log_file=True, file_path="./gmvault.log") 
    
    token, secret = get_oauth_tok_sec('guillaume.aubert@gmail.com', a_webbrowser = webbrowser)
    print('token = %s, secret = %s' % (token,secret) )
    req = generate_xoauth(token, secret, 'guillaume.aubert@gmail.com')
    
    print(req)
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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

'''
Created on Feb 14, 2012

@author: guillaume.aubert@gmail.com

Experimentation and validation of internal mechanisms
'''

import unittest
import base64
import socket
import imaplib


import gmv.gmvault_utils as gmvault_utils
import gmv.imap_utils as imap_utils


def obfuscate_string(a_str):
    """ use base64 to obfuscate a string """
    return base64.b64encode(a_str)

def deobfuscate_string(a_str):
    """ deobfuscate a string """
    return base64.b64decode(a_str)

def read_password_file(a_path):
    """
       Read log:pass from a file in my home
    """
    with open(a_path) as f:
        line = f.readline()
        login, passwd = line.split(":")

    return deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip())

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestSandbox(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestSandbox, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_login, self.gmvault_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        
        
    def ztest_logger(self):
        """
           Test the logging mechanism
        """
        
        import gmv.log_utils as log_utils
        log_utils.LoggerFactory.setup_cli_app_handler('./gmv.log') 
        
        LOG = log_utils.LoggerFactory.get_logger('gmv') #pylint:disable-msg=C0103
        
        LOG.info("On Info")
        
        LOG.warning("On Warning")
        
        LOG.error("On Error")
        
        LOG.notice("On Notice")
        
        try:
            raise Exception("Exception. This is my exception")
            self.fail("Should never arrive here") #pylint:disable-msg=W0101
        except Exception, err: #pylint:disable-msg=W0101, W0703
            LOG.exception("error,", err)
        
        LOG.critical("On Critical")
        
    def ztest_encrypt_blowfish(self):
        """
           Test encryption with blowfish
        """
        file_path = '../etc/tests/test_few_days_syncer/2384403887202624608.eml.gz'
        
        import gzip
        import gmv.blowfish
        
        #create blowfish cipher
        cipher = gmv.blowfish.Blowfish('VerySeCretKey')
         
        gz_fd = gzip.open(file_path)
        
        content = gz_fd.read()
        
        cipher.initCTR()
        crypted = cipher.encryptCTR(content)
        
        cipher.initCTR()
        decrypted = cipher.decryptCTR(crypted)
        
        self.assertEquals(decrypted, content)
        
    def ztest_regexpr(self):
        """
           regexpr for 
        """
        import re
        the_str = "Subject: Marta Gutierrez commented on her Wall post.\nMessage-ID: <c5b5deee29e373ca42cec75e4ef8384e@www.facebook.com>"
        regexpr = "Subject:\s+(?P<subject>.*)\s+Message-ID:\s+<(?P<msgid>.*)>"
        reg = re.compile(regexpr)
        
        matched = reg.match(the_str)
        if matched:
            print("Matched")
            print("subject=[%s],messageid=[%s]" % (matched.group('subject'), matched.group('msgid')))
            
    def ztest_is_encrypted_regexpr(self):
        """
           Encrypted re
        """
        import re
        the_str ="1384313269332005293.eml.crypt.gz"
        regexpr ="[\w+,\.]+crypt[\w,\.]*"
        
        reg= re.compile(regexpr)
        matched = reg.match(the_str)
        if matched:
            print("\nMatched")
        else:
            print("\nUnmatched")
    
    
    def ztest_memory_error_bug(self):
        """
           Try to push the memory error
        """
        # now read the password
        import sys
        import gmv.gmv_cmd as gmv_cmd
        import email

        with open('/Users/gaubert/gmvault-data/gmvault-db-bug/db/2004-10/1399791159741721320.eml') as f:
            email_body = f.read()
        mail = email.message_from_string(email_body)

        print mail

        sys.argv = ['gmvault.py', 'restore', '--db-dir',
                    '/Users/gaubert/gmvault-data/gmvault-db-bug',
                    'gsync.mtester@gmail.com']

        gmv_cmd.bootstrap_run()

    def ztest_retry_mode(self):
        """
           Test that the decorators are functionning properly
        """
        class MonkeyIMAPFetcher(imap_utils.GIMAPFetcher):
            
            def __init__(self, host, port, login, credential, readonly_folder = True):
                """
                   Constructor
                """
                super(MonkeyIMAPFetcher, self).__init__( host, port, login, credential, readonly_folder)
                self.connect_nb = 0
                
            def connect(self):
                """
                   connect
                """
                self.connect_nb += 1
            
            @imap_utils.retry(3,1,2)   
            def push_email(self, a_body, a_flags, a_internal_time, a_labels):
                """
                   Throw exceptions
                """
                #raise imaplib.IMAP4.error("GIMAPFetcher cannot restore email in %s account." %("myaccount@gmail.com"))
                #raise imaplib.IMAP4.abort("GIMAPFetcher cannot restore email in %s account." %("myaccount@gmail.com"))
                raise socket.error("Error")
                #raise imap_utils.PushEmailError("GIMAPFetcher cannot restore email in %s account." %("myaccount@gmail.com"))
            
        
        imap_fetch = MonkeyIMAPFetcher(host = None, port = None, login = None, credential = None)
        try:
            imap_fetch.push_email(None, None, None, None)
        #except Exception, err:
        except imaplib.IMAP4.error, err:
            self.assertEquals('GIMAPFetcher cannot restore email in myaccount@gmail.com account.', str(err))
        
        self.assertEquals(imap_fetch.connect_nb, 3)
    
    def ztest_os_walk(self):
        """
           test os walk
        """
        import os
        for root, dirs, files in os.walk('/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db/db'):
            print("root: %s, sub-dirs : %s, files = %s" % (root, dirs, files))
    
    def ztest_get_subdir_info(self):
        """
           test get subdir info
        """
        import gmv.gmvault as gmv
        
        storer = gmv.GmailStorer("/Users/gaubert/gmvault-db")
        
        storer.init_sub_chats_dir()
       
        
    
    def ztest_ordered_os_walk(self):
        """
           test ordered os walk
        """
        import gmv.gmvault_utils as gmvu
        
        for vals in gmvu.ordered_dirwalk('/home/aubert/gmvault-db.old/db', a_wildcards="*.meta"):
            print("vals = %s\n" % (vals))
            pass
        
        import os
        for root, dirs, files in os.walk('/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db/db'):
            print("root: %s, sub-dirs : %s, files = %s" % (root, dirs, files))
            
            
    
    
    def ztest_logging(self):
        """
           Test logging
        """
        #gmv_cmd.init_logging()
        import gmv.log_utils as log_utils
        log_utils.LoggerFactory.setup_cli_app_handler(activate_log_file=True, file_path="/tmp/gmvault.log") 
        LOG = log_utils.LoggerFactory.get_logger('gmv')
        LOG.critical("This is critical")
        LOG.info("This is info")
        LOG.error("This is error")
        LOG.debug("This is debug")
        

        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSandbox)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

'''
Created on Nov 8, 2011

@author: guillaume.aubert@eumetcast.int
'''
import sys
import unittest
import base64
import shutil
import os

import ssl
import gmvault
import gmvault_utils
import gmv
import imaplib


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
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestGMVault(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVault, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_login, self.gmvault_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        
    def ztest_cli_bad_server(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imagp.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--email', self.login, '--passwd', 'bar']
    
        gmvaulter = gmv.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, err:
            print("In Error success")
            
    def ztest_cli_bad_passwd(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--email', self.login, '--passwd', 'bar']
    
        gmvaulter = gmv.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, err:
            print("In Error success")
            
    def ztest_cli_bad_login(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--email', 'jjj', '--passwd', 'bar']
    
        gmvaulter = gmv.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, err:
            print("In Error success")
            
    
    
    def ztest_cli_host_error(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault.py', '--sync', '--host', \
                    'imap.gmail.com', '--port', '1452', \
                    '--login', 'foo', '--passwd', 'bar']
    
        gmvaulter = gmv.GMVaultLauncher()
    
        try:
            _ = gmvaulter.parse_args()
        except SystemExit, err:
            self.assertEquals(type(err), type(SystemExit()))
            self.assertEquals(err.code, 2)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
        else:
            self.fail('SystemExit exception expected')

    def ztest_cli_(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 10-Nov-2011', \
                    '--email', 'foo', '--passwd', 'bar']
    
        gmvaulter = gmv.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertFalse(args['verbose'])
            self.assertEquals(args['sync-mode'],'full-sync')
            self.assertEquals(args['email'],'foo')
            self.assertEquals(args['passwd'],'bar')
            self.assertEquals(args['request'], 'Since 1-Nov-2011 Before 10-Nov-2011')
            self.assertEquals(args['oauth-token'], None)
            self.assertEquals(args['host'],'imap.gmail.com')
            self.assertEquals(args['port'], 993)
            self.assertEquals(args['db-dir'],'./gmvault-db')
            
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
    
    def ztest_full_sync_gmv(self):
        """
           full test via the command line
        """
        sys.argv = ['gmvault.py', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', '993', '--imap-request', \
                    'Since 1-Nov-2011 Before 5-Nov-2011', '--email', \
                    self.login, '--passwd', self.passwd]
    
        gmvault_launcher = gmv.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
    
        gmvault_launcher.run(args)
        
        #check all stored gmail ids
        gstorer = gmvault.GmailStorer(args['db-dir'])
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', \
                                1384486067720566818L: '2011-11', \
                                1384313269332005293L: '2011-11', \
                                1384545182050901969L: '2011-11', \
                                1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir(args['db-dir'])
    
    def ztest_delete_sync_gmv(self):
        """
           delete sync via command line
        """
        gmv.init_logging()
        
        #first request to have the extra dirs
        sys.argv = ['gmvault.py', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', '993', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', self.passwd, '--db-dir', '/tmp/new-db-1']
    
        gmvault_launcher = gmv.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
    
        gmvault_launcher.run(args)
        
        #second requests so all files after the 5 should disappear 
        sys.argv = ['gmvault.py', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', '993', '--imap-request', \
                    'Since 1-Nov-2011 Before 5-Nov-2011', '--email', self.login, \
                    '--passwd', self.passwd, '--db-dir', '/tmp/new-db-1', '--db-cleaning', 'yes']
    
        args = gmvault_launcher.parse_args()
        gmvault_launcher.run(args)
    
        #check all stored gmail ids
        gstorer = gmvault.GmailStorer(args['db-dir'])
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', \
                                1384486067720566818L: '2011-11', \
                                1384313269332005293L: '2011-11', \
                                1384545182050901969L: '2011-11', \
                                1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir(args['db-dir'])
        
    def ztest_password_handling(self):
        """
           Test all credentials handling
        """
        gmv.init_logging()
        
        # test 1: enter passwd and go to interactive mode

        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--interactive', '--db-dir', '/tmp/new-db-1']
    
        gmvault_launcher = gmv.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : 'a_password'}) #test_mode needed to avoid calling get_pass
    
        self.assertEquals(credential, {'type': 'passwd', 'value': 'a_password'})
        
        # store passwd and re-read it
        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--save-passwd', '--db-dir', '/tmp/new-db-1']
        
        gmvault_launcher = gmv.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : 'a_new_password'})
        
        self.assertEquals(credential, {'type': 'passwd', 'option': 'saved', 'value': 'a_new_password'})
        
        # now read the password
        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--db-dir', '/tmp/new-db-1']
        
        gmvault_launcher = gmv.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : "don't care"})
        
        self.assertEquals(credential, {'type': 'passwd', 'option': 'read', 'value': 'a_new_password'})
        
    def test_oauth_tok_handling(self):
        """
           test connection with oauth
        """
        gmv.init_logging()
        
        # test 1: enter passwd and go to interactive mode

        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--email', self.login, \
                    '--db-dir', '/tmp/new-db-1']
    
        gmvault_launcher = gmv.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args) #test_mode needed to avoid calling get_pass
    
        gmvault_launcher.run(args, credential)
    
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()
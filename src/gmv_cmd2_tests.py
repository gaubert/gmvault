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
import imaplib
import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils
import gmv.gmv_cmd2 as gmv_cmd


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
        
    def test_cli_sync_email(self):
        """
           Test the cli interface bad option
        """
        
        #with email
        sys.argv = ['gmvault', 'sync', 'foo@bar.com']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
            
        #without email
        print("Test without email")
        sys.argv = ['gmvault', 'sync']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.fail('should go in error')
            
        except SystemExit, err:
            #should go here
            pass
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
            
    def test_cli_sync_credential(self):
        """
           Test the different credential modes
        """
        
        #default to oauth token
        print("default to oauth\n")
        sys.argv = ['gmvault', 'sync', 'foo@bar.com']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            self.assertEquals(args['passwd'],'not_seen')
            self.assertEquals(args['oauth'],'empty')
        
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
            
        print("require oauth\n")
        sys.argv = ['gmvault', 'sync', 'foo@bar.com', '-o']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            self.assertEquals(args['passwd'],'not_seen')
            self.assertEquals(args['oauth'],'empty')
        
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
        
        sys.argv = ['gmvault', 'sync', 'foo@bar.com', '--oauth']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            self.assertEquals(args['passwd'],'not_seen')
            self.assertEquals(args['oauth'],'empty')
        
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
            
        print("Error require password and oauth\n")
        sys.argv = ['gmvault', 'sync', 'foo@bar.com', '-o', '-p']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            self.assertEquals(args['passwd'],'not_seen')
            self.assertEquals(args['oauth'],'empty')
        
        except SystemExit, err:
            pass
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
        
        print("require password\n")
        sys.argv = ['gmvault', 'sync', 'foo@bar.com', '-p']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            self.assertEquals(args['passwd'],'empty')
            self.assertEquals(args['oauth'],'not_seen')
        
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
        
        sys.argv = ['gmvault', 'sync', 'foo@bar.com', '--passwd']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['email'],'foo@bar.com')
            self.assertEquals(args['passwd'],'empty')
            self.assertEquals(args['oauth'],'not_seen')
        
        except SystemExit, err:
            self.fail("SystemExit Exception: %s"  % err)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
            
    
    
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()
'''
Created on Jan 12, 2012

@author: guillaume.aubert@gmail.com
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
                
    def test_restore_on_gmail(self):
        """
           clean db disk
           sync with gmail for few emails
           restore them on gmail test
        """
        
        db_dir = '/tmp/gmail_bk'
        
        #clean db dir
        delete_db_dir(db_dir)
        
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, self.passwd)
        
        #syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        
        syncer.sync_with_gmail_acc('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd)
            
        print("Done \n")
        
    def ztest_restore_labels(self):
        """
           test all kind of labels that can be restored
        """
        
        db_dir = '/tmp/gmail_bk'
        
        #clean db dir
        delete_db_dir(db_dir)
        
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, self.passwd)
        
        #syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 3-Nov-2011")
        
        syncer.sync_with_gmail_acc('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, ["The Beginning", "EUMETSAT", "Very Important", "\\Important", "\\Starred","The End"])
        
        
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()
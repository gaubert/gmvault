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

import sys
import unittest
import base64
import shutil
import os

import ssl
import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils

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
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir=True)


class TestGMVaultValidation(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Validation Tests
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVaultValidation, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
        
        self.default_dir = "/tmp/gmvault-tests"
    
    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_test_login, self.gmvault_test_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
                
    def test_help_msg_spawned_by_def(self):
        """
           spawn python gmv_runner account > help_msg_spawned.txt
           check that res is 0 or 1
        """
        pass
   
    def test_backup_10_emails(self):
        """
           backup 10 emails and check that they are backed
           => spawn a process with the options
           => python gmv_runner.py sync account > checkfile
        """
        pass
    
    def test_restore_and_check(self):
        """
           Restore emails, retrieve them and compare with originals
        """
        db_dir = "/tmp/the_dir"
    
    
    def ztest_restore_on_gmail(self):
        """
           clean db disk
           sync with gmail for few emails
           restore them on gmail test
        """
        
        db_dir = '/tmp/gmail_bk'
        
        #clean db dir
        delete_db_dir(db_dir)
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        search_req    = { 'type' : 'imap', 'req': "Since 1-Nov-2011 Before 3-Nov-2011"}
        
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, credential, read_only_access = False, use_encryption = True)
        
        #syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        # Nov-2007 BigDataset
        syncer.sync(imap_req = search_req)
        
        restorer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.gmvault_login, gs_credential, read_only_access = False)
        restorer.restore()
            
        print("Done \n")    
        
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVaultValidation)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

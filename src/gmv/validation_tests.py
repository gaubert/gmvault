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

import unittest
import base64

import gmv.gmvault as gmvault
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
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir=True)


class TestGMVaultValidation(unittest.TestCase): #pylint:disable=R0904
    """
       Validation Tests
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVaultValidation, self).__init__(stuff)
        
        self.test_login  = None
        self.test_passwd = None 
        
        self.default_dir = "/tmp/gmvault-tests"
    
    def setUp(self): #pylint:disable=C0103
        self.test_login, self.test_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
                
    def test_help_msg_spawned_by_def(self):
        """
           spawn python gmv_runner account > help_msg_spawned.txt
           check that res is 0 or 1
        """
        credential  = { 'type' : 'passwd', 'value': self.test_passwd}
        test_db_dir = "/tmp/gmvault-tests"
        
        restorer = gmvault.GMVaulter(test_db_dir, 'imap.gmail.com', 993, self.test_login, credential, \
                                     read_only_access = False)
        
        restorer.restore() #restore all emails from this essential-db
        
        #need to check that all labels are there for emails in essential
        gmail_ids = restorer.gstorer.get_all_existing_gmail_ids()
        
        for gm_id in gmail_ids:
            #get disk_metadata
            disk_metadata   = restorer.gstorer.unbury_metadata(gm_id)
            
            # get online_metadata 
            online_metadata = restorer.src.fetch(gm_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA) 
            
            #compare metadata
            for key in disk_metadata:
                self.assertEquals(disk_metadata[key], online_metadata[key])
            

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVaultValidation)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

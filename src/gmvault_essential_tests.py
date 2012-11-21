'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <2011-2012>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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
import shutil
import os

import ssl
import gmv.mod_imap as mod_imap
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
    pass_file = open(a_path)
    line = pass_file.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestEssentialGMVault(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestEssentialGMVault, self).__init__(stuff)
        
        self.test_login  = None
        self.test_passwd = None 
    
    def setUp(self): #pylint:disable-msg=C0103
        print("IN SETUP")
        self.test_login, self.test_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')

    def assert_login_is_protected(self):
       """
          Insure that the login is not my personnal mailbox
       """
       if self.test_login != 'gsync.mtester@gmail.com':
          raise Exception("Beware login should be gsync.mtester@gmail.com and it is %s" % (self.test_login)) 

    def clean_mailbox(self):
        """
           Delete all emails, destroy all labels
        """
        credential    = { 'type' : 'passwd', 'value': self.test_passwd }

        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.test_login, credential, readonly_folder = False)

        print("self.test_login = %s" % (self.test_login))

        self.assert_login_is_protected()

        gimap.connect()
        
        gimap.erase_mailbox()
    
    def test_restore(self):
        """
           Test connect error (connect to a wrong port). Too long to check
        """
        credential    = { 'type' : 'passwd', 'value': self.test_passwd }

        #self.clean_mailbox()

		# test restore
        test_db_dir = "/home/gmv/gmvault-essential-db"
        
        restorer = gmvault.GMVaulter(test_db_dir, 'imap.gmail.com', 993, self.test_login, credential, \
                                     read_only_access = False)
        
        #restorer.restore() #restore all emails from this essential-db
        
        #need to check that all labels are there for emails in essential
        restorer.src.select_folder('ALLMAIL')

        imaps_ids = restorer.src.search('ALL')

        for imap_id in imap_ids:

            print("Fetching id %s with request %s" % (gm_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA))
            #get disk_metadata
            disk_metadata   = restorer.gstorer.unbury_metadata(gm_id)
            
            # get online_metadata 
            online_metadata = restorer.src.fetch(gm_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA) 
            
            #compare metadata
            for key in disk_metadata:
                self.assertEquals(disk_metadata[key], online_metadata[key])
        
    def ztest_restore_10_emails(self):
        """
           Restore 10 emails
        """
        gsource      = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gdestination = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, \
                                             readonly_folder = False)
        
        gsource.connect()
        gdestination.connect()
        
        criteria = ['Before 1-Oct-2008']
        #criteria = ['ALL']
        ids = gsource.search(criteria)
        
        #get 30 emails
        for index in range(9, 20):
            
            print("email nb %d\n" % (index))
        
            the_id = ids[index]
             
            source_email = gsource.fetch(the_id, gsource.GET_ALL_INFO)
            
            existing_labels = source_email[the_id][gsource.GMAIL_LABELS]
            
            # get labels
            test_labels = []
            for elem in existing_labels:
                test_labels.append(elem)
                
            dest_id = gdestination.push_email(source_email[the_id][gsource.EMAIL_BODY], \
                                               source_email[the_id][gsource.IMAP_FLAGS] , \
                                               source_email[the_id][gsource.IMAP_INTERNALDATE], test_labels)
            
            #retrieve email from destination email account
            dest_email = gdestination.fetch(dest_id, gsource.GET_ALL_INFO)
            
            #check that it has the same
            # do the checkings
            self.assertEquals(dest_email[dest_id][gsource.IMAP_FLAGS], source_email[the_id][gsource.IMAP_FLAGS])
            self.assertEquals(dest_email[dest_id][gsource.EMAIL_BODY], source_email[the_id][gsource.EMAIL_BODY])
            
            dest_labels = []
            for elem in dest_email[dest_id][gsource.GMAIL_LABELS]:
                if not elem == '\\Important':
                    dest_labels.append(elem)
            
            src_labels = []
            for elem in source_email[the_id][gsource.GMAIL_LABELS]:
                if not elem == '\\Important':
                    src_labels.append(elem)
            
            self.assertEquals(dest_labels, src_labels)         
   
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEssentialGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

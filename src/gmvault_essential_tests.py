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
import gmv.gmvault as gmvault
import gmv.gmvault_utils as gmvault_utils
import gmv.test_utils as test_utils


class TestEssentialGMVault(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestEssentialGMVault, self).__init__(stuff)
        
        self.gsync_login         = None
        self.gsync_passwd        = None 
        self.gmvault_test_login  = None
        self.gmvault_test_passwd = None
    
    def setUp(self): #pylint:disable-msg=C0103
        """setup"""
        self.gsync_login, self.gsync_passwd = test_utils.read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        self.gmvault_test_login, self.gmvault_test_passwd = test_utils.read_password_file('/homespace/gaubert/.ssh/gmvault_test_passwd')
        self.ba_login, self.ba_passwd = test_utils.read_password_file('/homespace/gaubert/.ssh/ba_passwd')

        #xoauth hanlding
        self.ga_login = 'guillaume.aubert@gmail.com'
        self.ga_cred  = test_utils.get_oauth_cred(self.ga_login, '/homespace/gaubert/.ssh/ga_oauth')

    def search_for_email(self, gmvaulter, req):
        """
           search for a particular email
        """
        #need to check that all labels are there for emails in essential
        gmvaulter.src.select_folder('ALLMAIL')

        imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req': req, 'charset': 'utf-8' })
 
        print("imap_ids = %s\n" % (imap_ids))
        
         
    def test_restore_tricky_emails(self):
        """ Test_restore_tricky_emails. Restore emails with some specificities (japanese characters) in the a mailbox """
        gsync_credential    = { 'type' : 'passwd', 'value': self.gsync_passwd }

        extra_labels = [u"My-Extra-Label"]

        test_utils.clean_mailbox(self.gsync_login, gsync_credential)

        # test restore
        test_db_dir = "/homespace/gaubert/gmvault-dbs/essential-dbs"
        #test_db_dir = "/home/gmv/Dev/projects/gmvault-develop/src/test-db"
        #test_db_dir = "/Users/gaubert/Dev/projects/gmvault-develop/src/test-db"
        
        restorer = gmvault.GMVaulter(test_db_dir, 'imap.gmail.com', 993, \
                                     self.gsync_login, gsync_credential, \
                                     read_only_access = False)
        
        restorer.restore(extra_labels = extra_labels) #restore all emails from this essential-db

        test_utils.check_remote_mailbox_identical_to_local(self, restorer, extra_labels)
        
    def test_backup_and_restore(self):
        """ Backup from gmvault_test and restore """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        gmvault_test_credential = { 'type' : 'passwd', 'value': self.gmvault_test_passwd }
        
        test_utils.clean_mailbox(self.gsync_login, gsync_credential)
        
        gmvault_test_db_dir = "/tmp/backup-restore"
        
        backuper = gmvault.GMVaulter(gmvault_test_db_dir, 'imap.gmail.com', 993, \
                                     self.gmvault_test_login, gmvault_test_credential, \
                                     read_only_access = False)
        
        backuper.sync({ 'mode': 'full', 'type': 'imap', 'req': 'ALL' })
        
        #check that we have x emails in the database
        restorer = gmvault.GMVaulter(gmvault_test_db_dir, 'imap.gmail.com', 993, \
                                     self.gsync_login, gsync_credential, \
                                     read_only_access = False)
        
        restorer.restore() #restore all emails from this essential-db

        test_utils.check_remote_mailbox_identical_to_local(self, restorer)

        test_utils.diff_online_mailboxes(backuper, restorer)
 
        gmvault_utils.delete_all_under(gmvault_test_db_dir, delete_top_dir = True)

    def ztest_delete_gsync(self):
        """
           Simply delete gsync
        """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        gmvault_test_credential = { 'type' : 'passwd', 'value': self.gmvault_test_passwd }

        test_utils.clean_mailbox(self.gsync_login, gsync_credential)
       
    def ztest_find_identicals(self):
        """
        """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        
        gmv_dir_a = "/tmp/a-db"
        gmv_a = gmvault.GMVaulter(gmv_dir_a, 'imap.gmail.com', 993, self.gsync_login, gsync_credential, read_only_access = True)
        
        test_utils.find_identical_emails(gmv_a)
         
    def ztest_difference(self):
        """
           
        """
        gsync_credential        = { 'type' : 'passwd', 'value': self.gsync_passwd }
        gmvault_test_credential = { 'type' : 'passwd', 'value': self.gmvault_test_passwd }
        ba_credential           = { 'type' : 'passwd', 'value': self.ba_passwd }

        gmv_dir_a = "/tmp/a-db"
        gmv_dir_b = "/tmp/b-db"

        gmv_a = gmvault.GMVaulter(gmv_dir_a, 'imap.gmail.com', 993, self.gsync_login, gsync_credential, read_only_access = True)
        
        #gmv_a = gmvault.GMVaulter(gmv_dir_a, 'imap.gmail.com', 993, self.gmvault_test_login, gmvault_test_credential, read_only_access = False)
        
        #gmv_b = gmvault.GMVaulter(gmv_dir_b, 'imap.gmail.com', 993, self.gmvault_test_login, gmvault_test_credential, read_only_access = False)

        #gmv_b = gmvault.GMVaulter(gmv_dir_b, 'imap.gmail.com', 993, self.ba_login, ba_credential, read_only_access = True)
        gmv_b = gmvault.GMVaulter(gmv_dir_b, 'imap.gmail.com', 993, self.ga_login, self.ga_cred, read_only_access = True)
        
        test_utils.diff_online_mailboxes(gmv_a, gmv_b)
        
def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEssentialGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

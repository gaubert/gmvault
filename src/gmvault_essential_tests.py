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
import datetime
import imapclient
import gmv.mod_imap as mod_imap
import gmv.gmvault as gmvault
import gmv.gmvault_db as gmvault_db
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

    def search_for_email(self, gmvaulter, req):
        """
           search for a particular email
        """
        #need to check that all labels are there for emails in essential
        gmvaulter.src.select_folder('ALLMAIL')

        imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req': req, 'charset': 'utf-8' })
 
        print("imap_ids = %s\n" % (imap_ids))
        
    def check_remote_mailbox_identical_to_local(self, gmvaulter):
        """
           Check that the remote mailbox is identical to the local one.
           Need a connected gmvaulter
        """
        # get all email data from gmvault-db
        pivot_dir  = None
        gmail_ids  = gmvaulter.gstorer.get_all_existing_gmail_ids(pivot_dir)

        print("gmail_ids = %s\n" % (gmail_ids))
        
        #need to check that all labels are there for emails in essential
        gmvaulter.src.select_folder('ALLMAIL')
        
        # check the number of id on disk 
        imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req' : 'ALL'}) #get everything
        
        self.assertEquals(len(imap_ids), \
                          len(gmail_ids), \
                          "Error. Should have the same number of emails: local nb of emails %d, remote nb of emails %d" % (len(gmail_ids), len(imap_ids)))

        for gm_id in gmail_ids:

            print("Fetching id %s with request %s" % (gm_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA))
            #get disk_metadata
            disk_metadata   = gmvaulter.gstorer.unbury_metadata(gm_id)

            print("disk metadata %s\n" % (disk_metadata))

            date     = disk_metadata['internal_date'].strftime('"%d %b %Y"')
            subject  = disk_metadata.get('subject', None)
            msgid    = disk_metadata.get('msg_id', None)
            received = disk_metadata.get('x_gmail_received', None)

            req = "("
            has_something = False

            #if date:
            #    req += 'HEADER DATE {date}'.format(date=date)
            #    has_something = True

            if subject:
                #split on ' when contained in subject to keep only the first part
                subject = subject.split("'")[0]
                subject = subject.split('"')[0]
                if has_something: #add extra space if it has a date
                    req += ' ' 
                req += 'SUBJECT "{subject}"'.format(subject=subject.strip().encode('utf-8'))
                has_something = True

            if msgid:
                if has_something: #add extra space if it has a date
                    req += ' ' 
                req += 'HEADER MESSAGE-ID {msgid}'.format(msgid=msgid.strip())
                has_something = True
            
            if received:
                if has_something:
                    req += ' '
                    req += 'HEADER X-GMAIL-RECEIVED {received}'.format(received=received.strip())
                    has_something = True
            
            req += ")"

            print("Req = %s\n" % (req))

            imap_ids = gmvaulter.src.search({ 'type' : 'imap', 'req': req, 'charset': 'utf-8'})

            print("imap_ids = %s\n" % (imap_ids))

            if len(imap_ids) != 1:
                self.fail("more than one imap_id (%s) retrieved for request %s" % (imap_ids, req))

            imap_id = imap_ids[0]
            
            # get online_metadata 
            online_metadata = gmvaulter.src.fetch(imap_id, \
                                                  imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA) 

            print("online_metadata = %s\n" % (online_metadata))
            print("disk_metadata = %s\n"   % (disk_metadata))

            header_fields = online_metadata[imap_id]['BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]']
            
            subject, msgid, received = gmvault_db.GmailStorer.parse_header_fields(header_fields)

            #compare metadata
            self.assertEquals(subject, disk_metadata.get('subject', None))
            self.assertEquals(msgid,   disk_metadata.get('msg_id', None))
            self.assertEquals(received, disk_metadata.get('x_gmail_received', None))

            # check internal date it is plus or minus 1 hour
            online_date   = online_metadata[imap_id].get('INTERNALDATE', None) 
            disk_date     = disk_metadata.get('internal_date', None) 

            if online_date != disk_date:
                min_date = disk_date - datetime.timedelta(hours=1)
                max_date = disk_date + datetime.timedelta(hours=1)
                
                if min_date <= online_date <= max_date:
                    print("online_date (%s) and disk_date (%s) differs but within one hour. This is OK (timezone pb) *****" % (online_date, disk_date))
                else:
                    self.fail("online_date (%s) and disk_date (%s) are different" % (online_date, disk_date))

            #check labels
            disk_labels   = disk_metadata.get('labels', None)
            online_labels = imap_utils.decode_labels(online_metadata[imap_id].get('X-GM-LABELS', None)) 

            if not disk_labels: #no disk_labels check that there are no online_labels
                self.assertTrue(not online_labels)

            self.assertEquals(len(disk_labels), len(online_labels))

            for label in disk_labels:
                if label not in online_labels:
                    self.fail("label %s should be in online_labels %s as it is in disk_labels %s" % (label, online_labels, disk_labels))

            # check flags
            disk_flags   = disk_metadata.get('flags', None)
            online_flags = online_metadata[imap_id].get('FLAGS', None) 

            if not disk_flags: #no disk flags
                self.assertTrue(not online_flags)

            self.assertEquals(len(disk_flags), len(online_flags))

            for flag in disk_flags:
                if flag not in online_flags:
                    self.fail("flag %s should be in online_flags %s as it is in disk_flags %s" % (flag, online_flags, disk_flags))        

         
    def test_restore(self):
        """
           Test connect error (connect to a wrong port). Too long to check
        """
        credential    = { 'type' : 'passwd', 'value': self.test_passwd }

        #self.clean_mailbox()

        # test restore
        #test_db_dir = "/homespace/gaubert/gmvault-db"
        #test_db_dir = "/homespace/gaubert/gmvault-dbs/essential-dbs"
        #test_db_dir = "/home/gmv/Dev/projects/gmvault-develop/src/test-db"
        test_db_dir = "/Users/gaubert/Dev/projects/gmvault-develop/src/test-db"
        
        restorer = gmvault.GMVaulter(test_db_dir, 'imap.gmail.com', 993, self.test_login, credential, \
                                     read_only_access = False)
        
        restorer.restore() #restore all emails from this essential-db

        self.check_remote_mailbox_identical_to_local(restorer)
        
def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEssentialGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

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
    with open(a_path) as f:
        line = f.readline()
        login, passwd = line.split(":")

    return deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip())

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
        
    
    def ztest_gmvault_connect_error(self):
        """
           Test connect error (connect to a wrong port). Too long to check
        """

        gimap = imap_utils.GIMAPFetcher('imap.gmafil.com', 80, "badlogin", "badpassword")
        
        try:
            gimap.connect()
        except ssl.SSLError, err:
            
            msg = str(err)
            
            if not msg.startswith('[Errno 8] _ssl.c:') or not msg.endswith('EOF occurred in violation of protocol'):
                self.fail('received %s. Bad error message' % (msg))
        
    def ztest_gmvault_get_capabilities(self):
        """
           Test simple retrieval
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        self.assertEquals(('IMAP4REV1', 'UNSELECT', \
                           'IDLE', 'NAMESPACE', \
                           'QUOTA', 'ID', 'XLIST', \
                           'CHILDREN', 'X-GM-EXT-1', \
                           'XYZZY', 'SASL-IR', 'AUTH=XOAUTH') , gimap.get_capabilities())
    
    def ztest_gmvault_check_gmailness(self):
        """
           Test simple retrieval
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        self.assertEquals( True , gimap.check_gmailness())
    
    def ztest_gmvault_compression(self):
        """
           Test simple retrieval
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        gimap.enable_compression()
        
        self.assertEquals( True , gimap.check_gmailness())
        
        criteria = ['Before 1-Jan-2011']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 33577)
        
    def ztest_created_nested_dirs(self):
        """ Try to create nested dirs """
        client = mod_imap.MonkeyIMAPClient('imap.gmail.com', port = 993, use_uid = True, ssl= True)
        
        client.login(self.gmvault_login, self.gmvault_passwd)
        
        folders_info = client.list_folders()
        
        print(folders_info)
        
        folders = [ the_dir for (_, _, the_dir) in folders_info ]
        
        print('folders %s\n' %(folders))
        the_dir = 'ECMWF-Archive'
        #dir = 'test'
        if the_dir not in folders:
            res = client.create_folder(dir)
            print(res)
        
        folders = [ the_dir for (_, _, dir) in folders_info ]
        
        print('folders %s\n' %(folders))
        the_dir = 'ECMWF-Archive/ecmwf-simdat'
        #dir = 'test/test-1'
        if the_dir not in folders:
            res = client.create_folder(the_dir)
            print(res)
    
    def zztest_create_gmail_labels_upper_case(self):
        """
           validate the label creation at the imap fetcher level.
           Use upper case
        """
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, gs_credential)
        
        gimap.connect()
        
        
        print("\nCreate labels.\n")
        
        labels_to_create = ['0','A','a', 'B/C', 'B/C/d', 'B/C/d/e', 'c/d']
        
        existing_folders = set()
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        print("folders = %s\n" % (existing_folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in existing_folders) )   
            
        labels_to_create = ['0','A','a', 'B/C', 'B/C/d', 'B/C/d/e', 'c/d', 'diablo3', 'blizzard', 'blizzard/diablo']
        #labels_to_create = ['B/c', u'[Imap]/Trash', u'[Imap]/Sent', 'a', 'A', 'e/f/g', 'b/c/d', ]
        
        existing_folders = set()
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        print("folders = %s\n" % (existing_folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in existing_folders) )   
        
        print("Delete labels\n")
        
        gimap.delete_gmail_labels(labels_to_create)
        
        #get existing directories (or label parts)
        folders = [ directory.lower() for (_, _, directory) in gimap.get_all_folders() ]
        
        for label in labels_to_create: #check that they have been deleted
            self.assertFalse( (label.lower() in folders) )
    
    def zztest_create_gmail_labels_android(self):
        """
           Handle labels with [Imap]
        """
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, gs_credential)
        
        gimap.connect()
        
        print("\nCreate labels.\n")
        
        labels_to_create = [u'[IMAP]/Trash', u'[IMAP]/Sent']
        
        existing_folders = set()
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        #get existing directories (or label parts)
        #print("xlist folders = %s\n" % (gimap.get_all_folders()) )
        
        #folders = [ directory.lower() for (flags, delim, directory) in gimap.server.list_folders() ]
        folders = [ directory.lower() for directory in existing_folders ]
        
        print("folders = %s\n" % (folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in folders) )   
            
        # second creation
        labels_to_create = [u'[RETEST]', u'[RETEST]/test', u'[RETEST]/Trash', u'[IMAP]/Trash', u'[IMAP]/Draft', u'[IMAP]/Sent', u'[IMAP]']
        
        existing_folders = gimap.create_gmail_labels(labels_to_create, existing_folders)
        
        folders = [ directory.lower() for directory in existing_folders ]
        
        print("folders = %s" % (folders))
        for label in labels_to_create:
            self.assertTrue( (label.lower() in folders) )  
            
        #it isn't possible to delete the [IMAP]/Sent, [IMAP]/Draft [IMAP]/Trash labels
        # I give up and do not delete them in the test
        labels_to_delete = [u'[RETEST]', u'[RETEST]/test', u'[RETEST]/Trash'] 
        
        print("Delete labels\n")
        
        # delete them
        gimap.delete_gmail_labels(labels_to_delete)
        
        #get existing directories (or label parts)
        folders = [ directory.lower() for (_, _, directory) in gimap.get_all_folders() ]
        
        for label in labels_to_delete: #check that they have been deleted
            self.assertFalse( (label.lower() in folders) )
            
        
        
    def ztest_gmvault_simple_search(self):
        """
           search all emails before 01.01.2005
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Jan-2011']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 33577)
        
    def ztest_retrieve_gmail_ids(self):
        """
           Get all uid before Sep 2004
           Retrieve all GMAIL IDs 
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Oct-2004']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        res = gimap.fetch(ids, [gimap.GMAIL_ID])
        
        self.assertEquals(res, {27362: {'X-GM-MSGID': 1147537963432096749L, 'SEQ': 14535}, 27363: {'X-GM-MSGID': 1147537994018957026L, 'SEQ': 14536}})
        
    def ztest_retrieve_all_params(self):
        """
           Get all params for a uid
           Retrieve all parts for one email
        """
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Oct-2004']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 2)
        
        res = gimap.fetch(ids[0], [gimap.GMAIL_ID, gimap.EMAIL_BODY, gimap.GMAIL_THREAD_ID, gimap.GMAIL_LABELS])
        
        self.assertEquals(res[ids[0]][gimap.GMAIL_ID], 1147537963432096749L)
        
        self.assertEquals(res[ids[0]][gimap.EMAIL_BODY], \
                          'Message-ID: <6999505.1094377483218.JavaMail.wwwadm@chewbacca.ecmwf.int>\r\nDate: Sun, 5 Sep 2004 09:44:43 +0000 (GMT)\r\nFrom: Guillaume.Aubert@ecmwf.int\r\nReply-To: Guillaume.Aubert@ecmwf.int\r\nTo: aubert_guillaume@yahoo.fr\r\nSubject: Fwd: [Flickr] Guillaume Aubert wants you to see their photos\r\nMime-Version: 1.0\r\nContent-Type: text/plain; charset=us-ascii\r\nContent-Transfer-Encoding: 7bit\r\nX-Mailer: jwma\r\nStatus: RO\r\nX-Status: \r\nX-Keywords:                 \r\nX-UID: 1\r\n\r\n\r\n') #pylint:disable-msg=C0301
        
    def ztest_gmvault_retrieve_email_store_and_read(self): #pylint:disable-msg=C0103
        """
           Retrieve an email store it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        the_id = ids[124]
        
        res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
        
        gm_id = gstorer.bury_email(res[the_id])
        
        metadata, data = gstorer.unbury_email(gm_id)
        
        self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
        self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
        self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
        
        labels = []
        for label in res[the_id][gimap.GMAIL_LABELS]:
            labels.append(label)
            
        self.assertEquals(labels, metadata['labels'])
    
    def ztest_gmvault_compress_retrieve_email_store_and_read(self): #pylint:disable-msg=C0103
        """
           Activate compression and retrieve an email store it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        gimap.enable_compression()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        the_id = ids[124]
        
        res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
        
        gm_id = gstorer.bury_email(res[the_id])
        
        metadata, data = gstorer.unbury_email(gm_id)
        
        self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
        self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
        self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
        
        labels = []
        for label in res[the_id][gimap.GMAIL_LABELS]:
            labels.append(label)
            
        self.assertEquals(labels, metadata['labels'])
    
    def ztest_gmvault_retrieve_multiple_emails_store_and_read(self): #pylint:disable-msg=C0103
        """
           Retrieve emails store them it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        #get 30 emails
        for index in range(9, 40):
        
            print("retrieve email index %d\n" % (index))
            the_id = ids[index]
            
            res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
            
            gm_id = gstorer.bury_email(res[the_id])
            
            print("restore email index %d\n" % (index))
            metadata, data = gstorer.unbury_email(gm_id)
            
            self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
            self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
            self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
            
            labels = []
            for label in res[the_id][gimap.GMAIL_LABELS]:
                labels.append(label)
                
            self.assertEquals(labels, metadata['labels'])
        
    def ztest_gmvault_store_gzip_email_and_read(self): #pylint:disable-msg=C0103
        """
           Retrieve emails store them it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        gimap   = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        #get 30 emails
        for index in range(9, 20):
        
            print("retrieve email index %d\n" % (index))
            the_id = ids[index]
            
            res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
            
            gm_id = gstorer.bury_email(res[the_id], compress = True)
            
            print("restore email index %d\n" % (index))
            metadata, data = gstorer.unbury_email(gm_id)
            
            self.assertEquals(res[the_id][gimap.GMAIL_ID], metadata['gm_id'])
            self.assertEquals(res[the_id][gimap.EMAIL_BODY], data)
            self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], metadata['thread_ids'])
            
            labels = []
            for label in res[the_id][gimap.GMAIL_LABELS]:
                labels.append(label)
                
            self.assertEquals(labels, metadata['labels'])
            
    def ztest_restore_one_email(self):
        """
           get one email from one account and restore it
        """
        gsource      = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gdestination = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, readonly_folder = False)
        
        gsource.connect()
        gdestination.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gsource.search(criteria)
        
        the_id = ids[0]
        
        source_email = gsource.fetch(the_id, gsource.GET_ALL_INFO)
        
        existing_labels = source_email[the_id][gsource.GMAIL_LABELS]
        
        test_labels = []
        for elem in existing_labels:
            test_labels.append(elem)
            
        #source_email[the_id][gsource.IMAP_INTERNALDATE] = source_email[the_id][gsource.IMAP_INTERNALDATE].replace(tzinfo= gmvault_utils.UTC_TZ)
            
        dest_id = gdestination.push_email(source_email[the_id][gsource.EMAIL_BODY], \
                                           source_email[the_id][gsource.IMAP_FLAGS] , \
                                           source_email[the_id][gsource.IMAP_INTERNALDATE], test_labels)
        
        dest_email = gdestination.fetch(dest_id, gsource.GET_ALL_INFO)
        
        # do the checkings
        self.assertEquals(dest_email[dest_id][gsource.IMAP_FLAGS], source_email[the_id][gsource.IMAP_FLAGS])
        self.assertEquals(dest_email[dest_id][gsource.EMAIL_BODY], source_email[the_id][gsource.EMAIL_BODY])
        self.assertEquals(dest_email[dest_id][gsource.GMAIL_LABELS], source_email[the_id][gsource.GMAIL_LABELS])
            
        #should be ok to be checked
        self.assertEquals(dest_email[dest_id][gsource.IMAP_INTERNALDATE], source_email[the_id][gsource.IMAP_INTERNALDATE])
        
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
        
    def ztest_few_days_syncer(self):
        """
           Test with the Syncer object
        """
        syncer = gmvault.GMVaulter('/tmp/gmail_bk', 'imap.gmail.com', 993, self.login, self.passwd)
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        
        storage_dir = "%s/%s" % ('/tmp/gmail_bk/db', '2011-11')
        
        gstorer = gmvault.GmailStorer('/tmp/gmail_bk')
        
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384313269332005293)
        
        self.assertEquals(metadata['gm_id'], 1384313269332005293)
        
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384403887202624608)
        
        self.assertEquals(metadata['gm_id'], 1384403887202624608)
            
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384486067720566818)
        
        self.assertEquals(metadata['gm_id'], 1384486067720566818)
        
    def ztest_few_days_syncer_with_deletion(self): #pylint:disable-msg=C0103
        """
           check that there was a deletion
        """
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        #copy test email in dest dir
        storage_dir = "%s/db/%s" % (db_dir, '2011-11')
        
        gmvault_utils.makedirs(storage_dir)
        
        shutil.copyfile('../etc/tests/test_few_days_syncer/2384403887202624608.eml.gz','%s/2384403887202624608.eml.gz' % (storage_dir))
        shutil.copyfile('../etc/tests/test_few_days_syncer/2384403887202624608.meta','%s/2384403887202624608.meta' % (storage_dir))
        
        syncer = gmvault.GMVaulter('/tmp/gmail_bk', 'imap.gmail.com', 993, self.login, self.passwd)
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 2-Nov-2011", db_cleaning = True)
        
        self.assertFalse(os.path.exists('%s/2384403887202624608.eml.gz' % (storage_dir)))
        self.assertFalse(os.path.exists('%s/2384403887202624608.meta' % (storage_dir)))
        self.assertTrue(os.path.exists('%s/1384313269332005293.meta' % (storage_dir)))
        self.assertTrue(os.path.exists('%s/1384313269332005293.eml.gz' % (storage_dir)))
            
    def ztest_encrypt_restore_on_gmail(self):
        """
           Doesn't work to be fixed
           clean db disk
           sync with gmail for few emails
           restore them on gmail test
        """
        
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        search_req    = { 'type' : 'imap', 'req': "Since 1-Nov-2011 Before 3-Nov-2011"}
        
        use_encryption = True
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, credential, read_only_access = True, use_encryption = use_encryption)
        
        syncer.sync(imap_req = search_req)
        
        # check that the email can be read
        gstorer = gmvault.GmailStorer('/tmp/gmail_bk', use_encryption)
        
        metadata = gmvault.GMVaulter.check_email_on_disk(gstorer, 1384313269332005293)
        
        self.assertEquals(metadata['gm_id'], 1384313269332005293)
        
        email_meta, email_data = gstorer.unbury_email(1384313269332005293)
        
        self.assertTrue(email_data.startswith("Delivered-To: guillaume.aubert@gmail.com"))
        
        #print("Email Data = \n%s\n" % (email_data))
            
        print("Done \n")
        
    def ztest_fix_bug_search_broken_gm_id_and_quarantine(self):
        """
           Search with a gm_id and quarantine it
        """
        db_dir = '/tmp/gmail_bk'
        
        #clean db dir
        delete_db_dir(db_dir)
        
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        gs_credential = { 'type' : 'passwd', 'value': self.gmvault_passwd}
        gstorer = gmvault.GmailStorer(db_dir)
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, credential)
        
        gimap.connect()
       
        criteria = { 'type': 'imap', 'req' :['X-GM-MSGID 1254269417797093924']} #broken one
        #criteria = ['X-GM-MSGID 1254267782370534098']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        for the_id in ids:
            res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
          
            gm_id = gstorer.bury_email(res[the_id], compress = True)
            
            syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.gmvault_login, gs_credential)
        
            syncer.restore()
        
        
        #check that the file has been quarantine
        quarantine_dir = '%s/quarantine' %(db_dir)
        
        self.assertTrue(os.path.exists('%s/1254269417797093924.eml.gz' % (quarantine_dir)))
        self.assertTrue(os.path.exists('%s/1254269417797093924.meta' % (quarantine_dir)))
                
    def ztest_fix_bug(self):
        """
           bug with uid 142221L => empty email returned by gmail
        """
        db_dir = '/tmp/gmail_bk'
        credential = { 'type' : 'passwd', 'value': self.passwd}
        syncer = gmvault.GMVaulter(db_dir, 'imap.gmail.com', 993, self.login, credential, 'verySecRetKeY')
        
        syncer._create_update_sync([142221L], compress = True)
        
    def test_check_flags(self):
        """
           Check flags 
        """
        credential    = { 'type' : 'passwd', 'value': self.passwd}
        #print("credential %s\n" % (credential))
        gimap = imap_utils.GIMAPFetcher('imap.gmail.com', 993, self.login, credential)
        
        gimap.connect()
       
        imap_ids  = [155182]
        gmail_id = 1405877259414135030

        imap_ids = [155070]
        
        #res = gimap.fetch(imap_ids, [gimap.GMAIL_ID, gimap.IMAP_FLAGS])
        res = gimap.fetch(imap_ids, gimap.GET_ALL_BUT_DATA)
        
        print(res)
        
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

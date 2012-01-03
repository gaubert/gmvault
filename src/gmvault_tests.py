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
    f = open(a_path)
    line = f.readline()
    (login, passwd) = line.split(":")
    
    return (deobfuscate_string(login.strip()), deobfuscate_string(passwd.strip()))

def delete_db_dir(a_db_dir):
    """
       delete the db directory
    """
    gmvault_utils.delete_all_under(a_db_dir, delete_top_dir = True)


class TestGMVault(unittest.TestCase):

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVault, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 
    
    def setUp(self):
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        
        self.gmvault_login, self.gmvault_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        
    
    def ztest_gmvault_connect_error(self):
        """
           Test connect error (connect to a wrong port). Too long to check
        """

        gimap = gmvault.GIMAPFetcher('imap.gmafil.com', 80, "badlogin", "badpassword")
        
        try:
            gimap.connect()
        except ssl.SSLError, err:
            self.assertEquals(str(err), '[Errno 1] _ssl.c:480: error:140770FC:SSL routines:SSL23_GET_SERVER_HELLO:unknown protocol')
    
    def ztest_gmvault_get_capabilities(self):
        """
           Test simple retrieval
        """
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        self.assertEquals(('IMAP4REV1', 'UNSELECT', 'IDLE', 'NAMESPACE', 'QUOTA', 'ID', 'XLIST', 'CHILDREN', 'X-GM-EXT-1', 'XYZZY', 'SASL-IR', 'AUTH=XOAUTH') , gimap.get_capabilities())
    
    def ztest_gmvault_check_gmailness(self):
        """
           Test simple retrieval
        """
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        self.assertEquals( True , gimap.check_gmailness())
    
    def ztest_gmvault_compression(self):
        """
           Test simple retrieval
        """
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
        
        gimap.enable_compression()
        
        self.assertEquals( True , gimap.check_gmailness())
        
        criteria = ['Before 1-Jan-2011']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 33629)
        
    def ztest_created_nested_dirs(self):
        """ Try to create nested dirs """
        client = gmvault.MonkeyIMAPClient('imap.gmail.com', port = 993, use_uid = True, ssl= True)
        
        client.login(self.gmvault_login, self.gmvault_passwd)
        
        #res = client.xlist_folders()
        
        #print(res)
        
        folders_info = client.list_folders()
        
        print(folders_info)
        
        folders = [ dir for (i, parent, dir) in folders_info ]
        
        print('folders %s\n' %(folders))
        dir = 'ECMWF-Archive'
        #dir = 'test'
        if dir not in folders:
            res = client.create_folder(dir)
            print(res)
        
        folders = [ dir for (i, parent, dir) in folders_info ]
        
        print('folders %s\n' %(folders))
        dir = 'ECMWF-Archive/ecmwf-simdat'
        #dir = 'test/test-1'
        if dir not in folders:
            res = client.create_folder(dir)
            print(res)
    
    def test_create_gmail_labels(self):
        """
           validate the label creation at the imap fetcher level
        """
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd)
        
        gimap.connect()
        
        labels_to_create = ['a','b/c', 'e/f/g', 'b/c/d']
        
        gimap.create_gmail_labels(labels_to_create)
        
        #get existing directories (or label parts)
        folders = [ directory for (_, _, directory) in gimap.get_all_folders() ]
        
        for label in labels_to_create:
            self.assertTrue( (label in folders) )   
        
        gimap.delete_gmail_labels(labels_to_create)
        
        #get existing directories (or label parts)
        folders = [ directory for (_, _, directory) in gimap.get_all_folders() ]
        
        for label in labels_to_create: #check that they have been deleted
            self.assertFalse( (label in folders) )
            
        
        
    def ztest_gmvault_simple_search(self):
        """
           search all emails before 01.01.2005
        """
        has_ssl = True
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Jan-2011']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 33629)
        
    def ztest_gmvault_retrieve_gmail_ids(self):
        """
           Get all uid before Sep 2004
           Retrieve all GMAIL IDs 
        """
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Oct-2004']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        res = gimap.fetch(ids, [gimap.GMAIL_ID])
        
        self.assertEquals(res, {27362: {'X-GM-MSGID': 1147537963432096749L, 'SEQ': 14535}, 27363: {'X-GM-MSGID': 1147537994018957026L, 'SEQ': 14536}})
        
    def ztest_gmvault_retrieve_all_params(self):
        """
           Get all params for a uid
           Retrieve all parts for one email
        """
        gimap = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gimap.connect()
       
        criteria = ['Before 1-Oct-2004']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        self.assertEquals(len(ids), 2)
        
        res = gimap.fetch(ids[0], [gimap.GMAIL_ID, gimap.EMAIL_BODY, gimap.GMAIL_THREAD_ID, gimap.GMAIL_LABELS])
        
        self.assertEquals(res[ids[0]][gimap.GMAIL_ID], 1147537963432096749L)
        
        self.assertEquals(res[ids[0]][gimap.EMAIL_BODY],'Message-ID: <6999505.1094377483218.JavaMail.wwwadm@chewbacca.ecmwf.int>\r\nDate: Sun, 5 Sep 2004 09:44:43 +0000 (GMT)\r\nFrom: Guillaume.Aubert@ecmwf.int\r\nReply-To: Guillaume.Aubert@ecmwf.int\r\nTo: aubert_guillaume@yahoo.fr\r\nSubject: Fwd: [Flickr] Guillaume Aubert wants you to see their photos\r\nMime-Version: 1.0\r\nContent-Type: text/plain; charset=us-ascii\r\nContent-Transfer-Encoding: 7bit\r\nX-Mailer: jwma\r\nStatus: RO\r\nX-Status: \r\nX-Keywords:                 \r\nX-UID: 1\r\n\r\n\r\n')
        
    def ztest_gmvault_retrieve_email_store_and_read(self):
        """
           Retrieve an email store it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        
        gimap   = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        the_id = ids[124]
        
        res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
        
        gm_id = gstorer.bury_email(res[the_id])
        
        j_results = gstorer.unbury_email(gm_id)
        
        self.assertEquals(res[the_id][gimap.GMAIL_ID], j_results['id'])
        self.assertEquals(res[the_id][gimap.EMAIL_BODY], j_results['email'])
        self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], j_results['thread_ids'])
        
        labels = []
        for label in res[the_id][gimap.GMAIL_LABELS]:
            labels.append(label)
            
        self.assertEquals(labels, j_results['labels'])
    
    def ztest_gmvault_compress_retrieve_email_store_and_read(self):
        """
           Activate compression and retrieve an email store it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        
        gimap   = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
        gstorer = gmvault.GmailStorer(storage_dir)
        
        gimap.connect()
        
        gimap.enable_compression()
        
        criteria = ['Before 1-Oct-2006']
        #criteria = ['ALL']
        ids = gimap.search(criteria)
        
        the_id = ids[124]
        
        res          = gimap.fetch(the_id, gimap.GET_ALL_INFO)
        
        gm_id = gstorer.bury_email(res[the_id])
        
        j_results = gstorer.unbury_email(gm_id)
        
        self.assertEquals(res[the_id][gimap.GMAIL_ID], j_results['id'])
        self.assertEquals(res[the_id][gimap.EMAIL_BODY], j_results['email'])
        self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], j_results['thread_ids'])
        
        labels = []
        for label in res[the_id][gimap.GMAIL_LABELS]:
            labels.append(label)
            
        self.assertEquals(labels, j_results['labels'])
    
    def ztest_gmvault_retrieve_multiple_emails_store_and_read(self):
        """
           Retrieve emails store them it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        gimap   = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
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
            j_results = gstorer.unbury_email(gm_id)
            
            self.assertEquals(res[the_id][gimap.GMAIL_ID], j_results['id'])
            self.assertEquals(res[the_id][gimap.EMAIL_BODY], j_results['email'])
            self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], j_results['thread_ids'])
            
            labels = []
            for label in res[the_id][gimap.GMAIL_LABELS]:
                labels.append(label)
                
            self.assertEquals(labels, j_results['labels'])
        
    def ztest_gmvault_store_gzip_email_and_read(self):
        """
           Retrieve emails store them it on disk and read it
        """
        storage_dir = '/tmp/gmail_bk'
        gmvault_utils.delete_all_under(storage_dir)
        gimap   = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        
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
            j_results = gstorer.unbury_email(gm_id)
            
            self.assertEquals(res[the_id][gimap.GMAIL_ID], j_results['id'])
            self.assertEquals(res[the_id][gimap.EMAIL_BODY], j_results['email'])
            self.assertEquals(res[the_id][gimap.GMAIL_THREAD_ID], j_results['thread_ids'])
            
            labels = []
            for label in res[the_id][gimap.GMAIL_LABELS]:
                labels.append(label)
                
            self.assertEquals(labels, j_results['labels'])
        
    def ztest_restore_one_email(self):
        """
           get one email from one account and restore it
        """
        gsource      = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gdestination = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, readonly_folder = False)
        
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
            
        dest_id = gdestination.push_email(source_email[the_id][gsource.EMAIL_BODY],\
                                           source_email[the_id][gsource.IMAP_FLAGS] , \
                                           source_email[the_id][gsource.IMAP_INTERNALDATE], test_labels)
        
        dest_email = gdestination.fetch(dest_id, gsource.GET_ALL_INFO)
        
        # do the checkings
        self.assertEquals(dest_email[dest_id][gsource.IMAP_FLAGS], source_email[the_id][gsource.IMAP_FLAGS])
        self.assertEquals(dest_email[dest_id][gsource.EMAIL_BODY], source_email[the_id][gsource.EMAIL_BODY])
        self.assertEquals(dest_email[dest_id][gsource.GMAIL_LABELS], source_email[the_id][gsource.GMAIL_LABELS])
            
        #should be ok to be checked
        #self.assertEquals(dest_email[dest_id][gsource.IMAP_INTERNALDATE], source_email[the_id][gsource.IMAP_INTERNALDATE])
        
    def ztest_restore_10_emails(self):
        """
           Restore 10 emails
        """
        read_only_folder = False
        gsource      = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.login, self.passwd)
        gdestination = gmvault.GIMAPFetcher('imap.gmail.com', 993, self.gmvault_login, self.gmvault_passwd, readonly_folder = False)
        
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
            self.assertEquals(dest_email[dest_id][gsource.GMAIL_LABELS], source_email[the_id][gsource.GMAIL_LABELS])
        
    def ztest_few_days_syncer(self):
        """
           Test with the Syncer object
        """
        syncer = gmvault.GMVaulter('/tmp/gmail_bk', 'imap.gmail.com', 993, self.login, self.passwd)
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 4-Nov-2011")
        
        storage_dir = "%s/%s" % ('/tmp/gmail_bk', '2011-11')
        
        gs, metadata = gmvault.GMVaulter.check_email_on_disk(storage_dir, 1384313269332005293)
        
        self.assertEquals(metadata['id'], 1384313269332005293)
        
        gs, metadata = gmvault.GMVaulter.check_email_on_disk(storage_dir, 1384403887202624608)
        
        self.assertEquals(metadata['id'], 1384403887202624608)
            
        gs, metadata = gmvault.GMVaulter.check_email_on_disk(storage_dir, 1384486067720566818)
        
        self.assertEquals(metadata['id'], 1384486067720566818)
        
    def ztest_few_days_syncer_with_deletion(self):
        """
           check that there was a deletion
        """
        #copy test email in dest dir
        storage_dir = "%s/%s" % ('/tmp/gmail_bk', '2011-11')
        
        shutil.copyfile('../etc/tests/test_few_days_syncer/2384403887202624608.eml.gz','%s/2384403887202624608.eml.gz' % (storage_dir))
        shutil.copyfile('../etc/tests/test_few_days_syncer/2384403887202624608.meta','%s/2384403887202624608.meta' % (storage_dir))
        
        syncer = gmvault.GMVaulter('/tmp/gmail_bk', 'imap.gmail.com', 993, self.login, self.passwd)
        
        syncer.sync(imap_req = "Since 1-Nov-2011 Before 2-Nov-2011")
        
        self.assertFalse(os.path.exists('%s/2384403887202624608.eml.gz' % (storage_dir)))
        self.assertFalse(os.path.exists('%s/2384403887202624608.meta' % (storage_dir)))
        self.assertTrue(os.path.exists('%s/1384313269332005293.meta' % (storage_dir)))
        self.assertTrue(os.path.exists('%s/1384313269332005293.eml.gz' % (storage_dir)))

    def ztest_cli_host_error(self):
        """
           Test the cli interface bad option
        """
        import sys
        sys.argv = ['gmvault.py', '--sync','--host', 'imap.gmail.com', '--port', '1452', '--login', 'foo', '--passwd', 'bar']
    
        gmvault = gmv.GMVaultLauncher()
    
        try:
            args = gmvault.parse_args()
        except SystemExit, e:
            self.assertEquals(type(e), type(SystemExit()))
            self.assertEquals(e.code, 2)
        except Exception, e:
            self.fail('unexpected exception: %s' % e)
        else:
            self.fail('SystemExit exception expected')

    def ztest_cli_(self):
        """
           Test the cli interface bad option
        """
        import sys
        sys.argv = ['gmvault','--imap-server', 'imap.gmail.com', '--imap-port', 993, '--imap-request', 'Since 1-Nov-2011 Before 10-Nov-2011', '--email', 'foo', '--passwd', 'bar']
    
        gmvault = gmv.GMVaultLauncher()
    
        try:
            args = gmvault.parse_args()
            
            self.assertFalse(args['verbose'])
            self.assertEquals(args['sync-mode'],'full-sync')
            self.assertEquals(args['email'],'foo')
            self.assertEquals(args['passwd'],'bar')
            self.assertEquals(args['request'], 'Since 1-Nov-2011 Before 10-Nov-2011')
            self.assertEquals(args['oauth-token'],None)
            self.assertEquals(args['host'],'imap.gmail.com')
            self.assertEquals(args['port'], 993)
            self.assertEquals(args['db-dir'],'./gmvault-db')
            
            print(args)
            
        except SystemExit, e:
            self.fail("SystemExit Exception: %s"  % e)
        except Exception, e:
            self.fail('unexpected exception: %s' % e)
    
    def ztest_full_sync_gmv(self):
        """
           full test via the command line
        """
        import sys
        sys.argv = ['gmvault.py','--imap-server', 'imap.gmail.com', '--imap-port', '993', '--imap-request', 'Since 1-Nov-2011 Before 5-Nov-2011', '--email', self.login, '--passwd', self.passwd]
    
        gmvaultLauncher = gmv.GMVaultLauncher()
        
        args = gmvaultLauncher.parse_args()
    
        gmvaultLauncher.run(args)
        
        #check all stored gmail ids
        gstorer = gmvault.GmailStorer(args['db-dir'])
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', 1384486067720566818L: '2011-11', 1384313269332005293L: '2011-11', 1384545182050901969L: '2011-11', 1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir(args['db-dir'])
    
    def ztest_delete_sync_gmv(self):
        """
           delete sync via command line
        """
        gmv.init_logging()
        
        import sys
        #first request to have the extra dirs
        sys.argv = ['gmvault.py','--imap-server', 'imap.gmail.com', '--imap-port', '993', '--imap-request', 'Since 1-Nov-2011 Before 7-Nov-2011', '--email', self.login, \
                    '--passwd', self.passwd, '--db-dir', '/tmp/new-db-1']
    
        gmvaultLauncher = gmv.GMVaultLauncher()
        
        args = gmvaultLauncher.parse_args()
    
        gmvaultLauncher.run(args)
        
        #second requests so all files after the 5 should disappear 
        sys.argv = ['gmvault.py','--imap-server', 'imap.gmail.com', '--imap-port', '993', '--imap-request', 'Since 1-Nov-2011 Before 5-Nov-2011', '--email', self.login, \
                    '--passwd', self.passwd, '--db-dir', '/tmp/new-db-1', '--db-cleaning', 'yes']
    
        args = gmvaultLauncher.parse_args()
        gmvaultLauncher.run(args)
    
        #check all stored gmail ids
        gstorer = gmvault.GmailStorer(args['db-dir'])
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', 1384486067720566818L: '2011-11', 1384313269332005293L: '2011-11', 1384545182050901969L: '2011-11', 1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir(args['db-dir'])
        
    def ztest_logger(self):
        """
        """
        
        import log_utils
        log_utils.LoggerFactory.setup_cli_app_handler('./gmv.log') 
        
        LOG = log_utils.LoggerFactory.get_logger('gmv')
        
        LOG.info("On Info")
        
        LOG.warning("On Warning")
        
        LOG.error("On Error")
        
        LOG.notice("On Notice")
        
        try:
           raise Exception("Exception. This is my exception")
        except Exception, e:
            LOG.exception("eeror,", e)
            pass
        
        LOG.critical("On Critical")
        
        
            
        
        
        

def tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVault)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()
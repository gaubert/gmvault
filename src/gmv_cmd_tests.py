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
import imaplib
import gmv.gmvault as gmvault
import gmv.gmvault_db as gmvault_db
import gmv.gmvault_utils as gmvault_utils
import gmv.gmv_cmd as gmv_cmd
import gmv.credential_utils as credential_utils


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


class TestGMVCMD(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestGMVCMD, self).__init__(stuff)
        
        self.login  = None
        self.passwd = None
        
        self.gmvault_login  = None
        self.gmvault_passwd = None 

    def setUp(self): #pylint:disable-msg=C0103
        self.login, self.passwd = read_password_file('/homespace/gaubert/.ssh/passwd')
        #self.login, self.passwd = read_password_file('/home/gmv/.ssh/passwd')
        #self.login, self.passwd = read_password_file('H:/.ssh/passwd')

        self.gsync_login, self.gsync_passwd = read_password_file('/homespace/gaubert/.ssh/gsync_passwd')
        #self.gsync_login, self.gsync_passwd = read_password_file('/home/gmv/.ssh/gsync_passwd')
        #self.gsync_login, self.gsync_passwd = read_password_file('H:/.ssh/gsync_passwd')

    def ztest_commandline_args(self):
        """
           Test commandline args
        """
        gmv_cmd.init_logging()
        
        # test 1: default
        sys.argv = ['gmvault.py', 'sync', self.login]
        
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'full')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'ALL', 'type': 'imap'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'%s/gmvault-db' % (os.environ['HOME']))
            
        
        # test 2: do imap search
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-r', 'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--db-dir','/tmp/new-db-1', self.login]
        
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'Since 1-Nov-2011 Before 4-Nov-2011', 'type': 'imap'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        
        # test 2: do gmail search
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', self.login]
        
        #do same as in bootstrap
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        
        #test3 emails only
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', \
                    '--emails-only', self.login]
        
        #with emails only
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['emails_only'], True)
        self.assertEquals(args['chats_only'], False)
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        
        #test chats only
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', \
                    '--chats-only', self.login]
        
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['chats_only'], True)
        self.assertEquals(args['emails_only'], False)
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], True)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        self.assertEquals(args['ownership_control'], True)
        self.assertEquals(args['compression'], True)
        self.assertEquals(args['debug'], False)
        self.assertEquals(args['restart'], False)
 
 
        #test5 chats only
        sys.argv = ['gmvault.py', 'sync','-t', 'custom',
                    '-g', 'subject:Chandeleur bis', \
                    '--db-dir','/tmp/new-db-1', \
                    '--check-db', 'no', '--resume', '--debug',\
                    '--no-compression', self.login]
        
        #with emails only
        gmvlt = gmv_cmd.GMVaultLauncher()
    
        args = gmvlt.parse_args()
        
        #check args
        self.assertEquals(args['chats_only'], False)
        self.assertEquals(args['emails_only'], False)
        self.assertEquals(args['command'],  'sync')
        self.assertEquals(args['type'],     'custom')
        self.assertEquals(args['email'],    self.login)
        self.assertEquals(args['passwd'],   'not_seen')
        self.assertEquals(args['oauth'],    'empty')
        self.assertEquals(args['request'], {'req': 'subject:Chandeleur bis', 'type': 'gmail'})
        self.assertEquals(args['host'],'imap.gmail.com')
        self.assertEquals(args['port'], 993)
        self.assertEquals(args['db-cleaning'], False)
        self.assertEquals(args['db-dir'],'/tmp/new-db-1')
        self.assertEquals(args['compression'], False)
        self.assertEquals(args['debug'], True)
        self.assertEquals(args['restart'], True)
        
        
    def zztest_cli_bad_server(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', 'sync',  '--server', 'imagp.gmail.com', \
                    '--port', '993', '--imap-req', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    self.login]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, _:
            print("In Error success")
            
    def ztest_cli_bad_passwd(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', '--imap-server', 'imap.gmail.com', \
                    '--imap-port', 993, '--imap-request', \
                    'Since 1-Nov-2011 Before 4-Nov-2011', \
                    '--email', self.login, '--passwd', 'bar']
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
        
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
                    '--passwd', ]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
        
        args = gmvaulter.parse_args()
    
        try:
    
            gmvaulter.run(args)
        
        except SystemExit, err:
            print("In Error success")
            
    
    
    def zztest_cli_host_error(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault.py', 'sync', '--host', \
                    'imap.gmail.com', '--port', '1452', \
                    self.login]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            _ = gmvaulter.parse_args()
        except SystemExit, err:
            self.assertEquals(type(err), type(SystemExit()))
            self.assertEquals(err.code, 2)
        except Exception, err:
            self.fail('unexpected exception: %s' % err)
        else:
            self.fail('SystemExit exception expected')

    def zztest_cli_(self):
        """
           Test the cli interface bad option
        """
        sys.argv = ['gmvault', 'sync', '--server', 'imap.gmail.com', \
                    '--port', '993', '--imap-req', \
                    'Since 1-Nov-2011 Before 10-Nov-2011', \
                    '--passwd', self.login]
    
        gmvaulter = gmv_cmd.GMVaultLauncher()
    
        try:
            args = gmvaulter.parse_args()
            
            self.assertEquals(args['command'],'sync')
            self.assertEquals(args['type'],'full')
            self.assertEquals(args['email'], self.login)
            self.assertEquals(args['passwd'],'empty')
            self.assertEquals(args['request'], {'req': 'Since 1-Nov-2011 Before 10-Nov-2011', 'type': 'imap'})
            self.assertEquals(args['oauth'], 'not_seen')
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
    
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
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
        gmv_cmd.init_logging()
        
        # test 1: enter passwd and go to interactive mode

        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--interactive', '--db-dir', '/tmp/new-db-1']
    
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : 'a_password'}) #test_mode needed to avoid calling get_pass
    
        self.assertEquals(credential, {'type': 'passwd', 'value': 'a_password'})
        
        # store passwd and re-read it
        sys.argv = ['gmvault.py', '--imap-request', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--email', self.login, \
                    '--passwd', '--save-passwd', '--db-dir', '/tmp/new-db-1']
        
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : 'a_new_password'})
        
        self.assertEquals(credential, {'type': 'passwd', 'option': 'saved', 'value': 'a_new_password'})
        
        # now read the password
        sys.argv = ['gmvault.py', 'sync', '--imap-req', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '-t', 'custom', \
                    '--passwd', '--db-dir', '/tmp/new-db-1', self.login]
        
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = gmvault_launcher.get_credential(args, test_mode = {'activate': True, 'value' : "don't care"})
        
        self.assertEquals(credential, {'type': 'passwd', 'option': 'read', 'value': 'a_new_password'})
    
    
    def ztest_double_login(self):
        """
           double login
        """
        # now read the password
        sys.argv = ['gmvault.py', 'sync', '--db-dir', '/tmp/new-db-1', self.login]
        
        gmvault_launcher = gmv_cmd.GMVaultLauncher()
        
        args = gmvault_launcher.parse_args()
        
        credential = credential_utils.CredentialHelper.get_credential(args)
        
        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential)
        
        print("First connection \n")
        syncer.src.connect()
        
        import time
        time.sleep(60*10)
        
        print("Connection 10 min later")
        syncer.src.connect()

    def ztest_oauth2_login(self):
        """
           oauth2 login test
        """
        # now read the password
        sys.argv = ['gmvault.py', 'sync', '--db-dir', '/tmp/new-db-1', self.login]

        gmvault_launcher = gmv_cmd.GMVaultLauncher()

        args = gmvault_launcher.parse_args()

        credential = credential_utils.CredentialHelper.get_credential(args)

        print("CREDENTIALS:%s" % (credential))

        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential)

        print("First connection \n")
        syncer.src.connect()

        #syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
        #                               args['email'], credential)

        #print("First connection \n")
        #syncer.src.connect()

        #import time
        #time.sleep(60*10)

        #print("Connection 10 min later")
        #syncer.src.connect()

    def test_oauth2_reconnect(self):
        """
           oauth2 login test
        """
        # now read the password
        sys.argv = ['gmvault.py', 'sync', '--db-dir', '/tmp/new-db-1', self.login]

        gmvault_launcher = gmv_cmd.GMVaultLauncher()

        args = gmvault_launcher.parse_args()

        credential = credential_utils.CredentialHelper.get_credential(args)

        print("CREDENTIALS:%s" % (credential))

        syncer = gmvault.GMVaulter(args['db-dir'], args['host'], args['port'], \
                                       args['email'], credential)

        print("First connection \n")

        syncer.src.connect()

        print("Sleep 1 sec and connect again")
        import time
        time.sleep(1)

        syncer.src.connect()

        print("Sleep 1 sec and reconnect again")
        time.sleep(1)

        syncer.src.reconnect()

    def ztest_debug_restore(self):
        """
           double login
        """
        # now read the password
        sys.argv = ['gmvault.py', 'restore', '--db-dir', '/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db', 'gsync.mtester@gmail.com']
        
        gmv_cmd.bootstrap_run()
    
    def ztest_restore_with_labels(self):
        """
           Test restore with labels
        """
        
        sys.argv = ['gmvault.py', 'restore', '--restart', '--db-dir', '/Users/gaubert/Dev/projects/gmvault/src/gmv/gmvault-db', 'gsync.mtester@gmail.com']
        
        gmv_cmd.bootstrap_run()
        
    
    def ztest_quick_sync_with_labels(self):
        """
           Test quick sync
           --renew-passwd
        """
        sys.argv = ['gmvault.py', 'sync', self.login]
        
        gmv_cmd.bootstrap_run()
        
    def ztest_simple_get_and_restore(self):
        """
           get few emails and restore them
        """
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        print("Synchronize\n")
        
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '-r', 'Since 1-Nov-2011 Before 3-Nov-2011', '--db-dir', db_dir, 'guillaume.aubert@gmail.com']

        gmv_cmd.bootstrap_run()
        
        print("Restore\n")
        
        sys.argv = ['gmvault.py', 'restore', '--db-dir', db_dir, 'gsync.mtester@gmail.com']

        gmv_cmd.bootstrap_run()
        
    def ztest_simple_get_encrypt_and_restore(self):
        """
           get few emails and restore them
        """
        db_dir = '/tmp/gmail_bk'
        #clean db dir
        delete_db_dir(db_dir)
        
        print("Synchronize\n")
        
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '--encrypt','-r', 'Since 1-Nov-2011 Before 3-Nov-2011', '--db-dir', db_dir, 'guillaume.aubert@gmail.com']

        gmv_cmd.bootstrap_run()
        
        print("Restore\n")
        
        sys.argv = ['gmvault.py', 'restore', '--db-dir', db_dir, 'gsync.mtester@gmail.com']

        gmv_cmd.bootstrap_run()
        
    def ztest_delete_sync_gmv(self):
        """
           delete sync via command line
        """
        delete_db_dir('/tmp/new-db-1')
        
        #first request to have the extra dirs
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '-r', \
                    'Since 1-Nov-2011 Before 7-Nov-2011', \
                    '--db-dir', '/tmp/new-db-1', 'guillaume.aubert@gmail.com']
        
        #check all stored gmail ids
        gstorer = gmvault_db.GmailStorer('/tmp/new-db-1')
        
        gmv_cmd.bootstrap_run()
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 9)
        
        delete_db_dir('/tmp/new-db-1')
        
        #second requests so all files after the 5 should disappear 
        sys.argv = ['gmvault.py', 'sync', '-t', 'custom', '-r', \
                    'Since 1-Nov-2011 Before 5-Nov-2011', \
                    '--db-dir', '/tmp/new-db-1', '-c', 'yes', 'guillaume.aubert@gmail.com']
    
        gmv_cmd.bootstrap_run()
    
        gstorer = gmvault_db.GmailStorer('/tmp/new-db-1')
        
        ids = gstorer.get_all_existing_gmail_ids()
        
        self.assertEquals(len(ids), 5)
        
        self.assertEquals(ids, {1384403887202624608L: '2011-11', \
                                1384486067720566818L: '2011-11', \
                                1384313269332005293L: '2011-11', \
                                1384545182050901969L: '2011-11', \
                                1384578279292583731L: '2011-11'})
        
        #clean db dir
        delete_db_dir('/tmp/new-db-1')
               

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGMVCMD)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()

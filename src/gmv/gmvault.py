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
import json
import gzip
import re
import datetime
import os
import time
import itertools
import imaplib
import fnmatch
import shutil

import blowfish
import log_utils

import collections_utils
import gmvault_utils
import imap_utils
import credential_utils



LOG = log_utils.LoggerFactory.get_logger('gmvault')
            
class GmailStorer(object): #pylint:disable=R0902
    '''
       Store emails on disk
    ''' 
    DATA_FNAME     = "%s/%s.eml"
    METADATA_FNAME = "%s/%s.meta"
    CHAT_GM_LABEL  = "gmvault-chats"
    
    ID_K         = 'gm_id'
    EMAIL_K      = 'email'
    THREAD_IDS_K = 'thread_ids'
    LABELS_K     = 'labels'
    INT_DATE_K   = 'internal_date'
    FLAGS_K      = 'flags'
    SUBJECT_K    = 'subject'
    MSGID_K      = 'msg_id'
    
    HFIELDS_PATTERN = "[M,m][E,e][S,s][S,s][a,A][G,g][E,e]-[I,i][D,d]:\s+<(?P<msgid>.*)>\s+[S,s][U,u][b,B][J,j][E,e][C,c][T,t]:\s+(?P<subject>.*)\s*"
    HFIELDS_RE      = re.compile(HFIELDS_PATTERN)
    
    ENCRYPTED_PATTERN = "[\w+,\.]+crypt[\w,\.]*"
    ENCRYPTED_RE      = re.compile(ENCRYPTED_PATTERN)
    
    
    DB_AREA                    = 'db'
    QUARANTINE_AREA            = 'quarantine'
    CHATS_AREA                 = 'chats'
    SUB_CHAT_AREA              = 'chats/%s'
    INFO_AREA                  = '.info'  # contains metadata concerning the database
    ENCRYPTION_KEY_FILENAME    = '.storage_key.sec'
    OLD_EMAIL_OWNER            = '.email_account.info' #deprecated
    EMAIL_OWNER                = '.owner_account.info'
    GMVAULTDB_VERSION          = '.gmvault_db_version.info'   
    
    def __init__(self, a_storage_dir, encrypt_data = False):
        """
           Store on disks
           args:
              a_storage_dir: Storage directory
              a_use_encryption: Encryption key. If there then encrypt
        """
        self._top_dir = a_storage_dir
        
        self._db_dir          = '%s/%s' % (a_storage_dir, GmailStorer.DB_AREA)
        self._quarantine_dir  = '%s/%s' % (a_storage_dir, GmailStorer.QUARANTINE_AREA)
        self._info_dir        = '%s/%s' % (a_storage_dir, GmailStorer.INFO_AREA)
        self._chats_dir       = '%s/%s' % (self._db_dir, GmailStorer.CHATS_AREA)
        
        self._sub_chats_dir   = None
        self._sub_chats_inc   = -1
        self._sub_chats_nb    = -1
        
        self._limit_per_chat_dir = gmvault_utils.get_conf_defaults().getint("General", "limit_per_chat_dir", 1500)
        
        #make dirs
        if not os.path.exists(self._db_dir):
            LOG.critical("No Storage DB in %s. Create it.\n" % (a_storage_dir))
        
        gmvault_utils.makedirs(self._db_dir)
        gmvault_utils.makedirs(self._chats_dir)
        gmvault_utils.makedirs(self._quarantine_dir)
        gmvault_utils.makedirs(self._info_dir)
        
        self.fsystem_info_cache = {}
        
        self._encrypt_data   = encrypt_data
        self._encryption_key = None
        self._cipher         = None
        
        #add version if it is needed to migrate gmvault-db in the future
        self._create_gmvault_db_version()
        
        
    def _init_sub_chats_dir(self):
        """
           get info from existing sub chats
        """
        nb_to_dir = {}
        
        LOG.debug("LIMIT_PER_CHAT_DIR = %s" % (self._limit_per_chat_dir) )
        
        if os.path.exists(self._chats_dir):
            dirs = os.listdir(self._chats_dir)
            for the_dir in dirs:
                the_split = the_dir.split("-")
                if len(the_split) != 2:
                    raise Exception("Should get 2 elements in %s" % (the_split))
                
                nb_to_dir[int(the_split[1])] = the_dir
                
            
            if len(nb_to_dir) == 0:
                # no sub dir yet. Set it up
                self._sub_chats_nb  = 0
                self._sub_chats_inc = 1
                self._sub_chats_dir = self.SUB_CHAT_AREA % ("subchats-%s" % (self._sub_chats_inc))
                gmvault_utils.makedirs("%s/%s" % (self._db_dir, self._sub_chats_dir))
            
            # treat when more than limit chats in max dir 
            # treat when no dirs
            # add limit  as attribute limit_per_dir = 2000
            else:
                the_max = max(nb_to_dir)
                files = os.listdir("%s/%s" % (self._chats_dir, nb_to_dir[the_max]))
                self._sub_chats_nb  = len(files)/2
                self._sub_chats_inc = the_max
                self._sub_chats_dir = self.SUB_CHAT_AREA % nb_to_dir[the_max] 
            
        
    def get_sub_chats_dir(self):
        """
           Get sub_chats_dir
        """
        if self._sub_chats_inc == -1:
            self._init_sub_chats_dir()
         
        if self._sub_chats_nb >= self._limit_per_chat_dir:
            self._sub_chats_inc += 1
            
            self._sub_chats_nb  = 1 
            
            self._sub_chats_dir = self.SUB_CHAT_AREA % ("subchats-%s" % (self._sub_chats_inc))
            gmvault_utils.makedirs('%s/%s' % (self._db_dir, self._sub_chats_dir))
            
            return self._sub_chats_dir
        else:
            self._sub_chats_nb += 1
            return self._sub_chats_dir
    
        
    
    def _create_gmvault_db_version(self):
        """
           Create the Gmvault database version if it doesn't already exist
        """
        version_file = '%s/%s' % (self._info_dir, self.GMVAULTDB_VERSION)
        if not os.path.exists(version_file):
            the_fd = open(version_file, "w+")
            the_fd.write(gmvault_utils.GMVAULT_VERSION)
            the_fd.close()
    
    def store_db_owner(self, email_owner):
        """
           Store the email owner in .info dir. This is used to avoid synchronizing multiple email accounts in gmvault-db.
           Always wipe out completly the file
        """
        owners = self.get_db_owners()
        
        if email_owner not in owners:
            owners.append(email_owner)
            the_fd = open('%s/%s' % (self._info_dir, self.EMAIL_OWNER), "w+")
            json.dump(owners, the_fd, ensure_ascii = False)
            the_fd.flush()
            the_fd.close()
        
    
    def get_db_owners(self):
        """
           Get the email owner for the gmvault-db. Because except in particular cases, the db will be only linked to one meail.
        """
        fname = '%s/%s' % (self._info_dir, self.EMAIL_OWNER)
        if os.path.exists(fname):    
            the_fd = open(fname)
            list_of_owners = json.load(the_fd)
            the_fd.close()
            return list_of_owners
        
        return []
   
    def get_info_dir(self):
        """
           Return the info dir of gmvault-db
        """ 
        return self._info_dir
        
    def get_encryption_cipher(self):
        """
           Return the cipher to encrypt an decrypt.
           If the secret key doesn't exist, it will be generated.
        """
        if not self._cipher:
            if not self._encryption_key:
                self._encryption_key = credential_utils.CredentialHelper.get_secret_key('%s/%s' % (self._info_dir, self.ENCRYPTION_KEY_FILENAME))
            
            #create blowfish cipher if data needs to be encrypted
            self._cipher = blowfish.Blowfish(self._encryption_key)
        
        return self._cipher
        
    @classmethod
    def get_encryption_key_path(cls, a_root_dir):
        """
           Return the path of the encryption key.
           This is used to print that information to the user
        """
        return  '%s/%s/%s' % (a_root_dir, cls.INFO_AREA, cls.ENCRYPTION_KEY_FILENAME)
    
    @classmethod
    def get_encryption_key(cls, a_info_dir):
        """
           Return or generate the encryption key if it doesn't exist
        """
        return credential_utils.CredentialHelper.get_secret_key('%s/%s' % (a_info_dir, cls.ENCRYPTION_KEY_FILENAME))
    
    @classmethod
    def parse_header_fields(cls, header_fields):
        """
           extract subject and message ids from the given header fields 
        """
        matched = GmailStorer.HFIELDS_RE.match(header_fields)
        if matched:
            return (matched.group('subject'), matched.group('msgid'))
        else:
            return None, None
    
    def get_all_chats_gmail_ids(self):
        """
           Get only chats dirs 
        """
        # first create a normal dir and sort it below with an OrderedDict
        # beware orderedDict preserve order by insertion and not by key order
        gmail_ids = {}
        
        chat_dir = '%s/%s' % (self._db_dir, self.CHATS_AREA)
        if os.path.exists(chat_dir):
            the_iter = gmvault_utils.ordered_dirwalk(chat_dir, "*.meta")
        
            #get all ids
            for filepath in the_iter:
                directory, fname = os.path.split(filepath)
                gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)

            #sort by key 
            #used own orderedDict to be compliant with version 2.5
            gmail_ids = collections_utils.OrderedDict(sorted(gmail_ids.items(), key=lambda t: t[0]))
        
        return gmail_ids
        
        
    def get_all_existing_gmail_ids(self, pivot_dir = None, ignore_sub_dir = ['chats']): #pylint:disable=W0102
        """
           get all existing gmail_ids from the database within the passed month 
           and all posterior months
        """
        # first create a normal dir and sort it below with an OrderedDict
        # beware orderedDict preserve order by insertion and not by key order
        gmail_ids = {}
        
        if pivot_dir == None:
            #the_iter = gmvault_utils.dirwalk(self._db_dir, "*.meta")
            the_iter = gmvault_utils.ordered_dirwalk(self._db_dir, "*.meta", ignore_sub_dir)
        else:
            
            # get all yy-mm dirs to list
            dirs = gmvault_utils.get_all_directories_posterior_to(pivot_dir, gmvault_utils.get_all_dirs_under(self._db_dir, ignore_sub_dir))
            
            #create all iterators and chain them to keep the same interface
            #iter_dirs = [gmvault_utils.dirwalk('%s/%s' % (self._db_dir, the_dir), "*.meta") for the_dir in dirs]
            iter_dirs = [gmvault_utils.ordered_dirwalk('%s/%s' % (self._db_dir, the_dir), "*.meta", ignore_sub_dir) for the_dir in dirs]
            
            the_iter = itertools.chain.from_iterable(iter_dirs)
        
        #get all ids
        for filepath in the_iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)

        #sort by key 
        #used own orderedDict to be compliant with version 2.5
        gmail_ids = collections_utils.OrderedDict(sorted(gmail_ids.items(), key=lambda t: t[0]))
        
        return gmail_ids
    
    def bury_chat_metadata(self, email_info, local_dir = None):
        """
           Like bury metadata but with an extra label gmvault-chat
        """
        extra_labels = [GmailStorer.CHAT_GM_LABEL]
        return self.bury_metadata(email_info, local_dir, extra_labels)
    
    def bury_metadata(self, email_info, local_dir = None, extra_labels = []): #pylint:disable=W0102
        """
            Store metadata info in .meta file
            Arguments:
             email_info: metadata info
             local_dir : intermdiary dir (month dir)
        """
        if local_dir:
            the_dir = '%s/%s' % (self._db_dir, local_dir)
            gmvault_utils.makedirs(the_dir)
        else:
            the_dir = self._db_dir
         
        meta_path = self.METADATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID])
       
        meta_desc = open(meta_path, 'w')
        
        # parse header fields to extract subject and msgid
        subject, msgid = self.parse_header_fields(email_info[imap_utils.GIMAPFetcher.IMAP_HEADER_FIELDS_KEY])
        
        # need to convert labels that are number as string
        # come from imap_lib when label is a number
        labels = [ str(elem) for elem in  email_info[imap_utils.GIMAPFetcher.GMAIL_LABELS] ]
        
        labels.extend(extra_labels) #add extra labels
        
        #create json structure for metadata
        meta_obj = { 
                     self.ID_K         : email_info[imap_utils.GIMAPFetcher.GMAIL_ID],
                     self.LABELS_K     : labels,
                     self.FLAGS_K      : email_info[imap_utils.GIMAPFetcher.IMAP_FLAGS],
                     self.THREAD_IDS_K : email_info[imap_utils.GIMAPFetcher.GMAIL_THREAD_ID],
                     self.INT_DATE_K   : gmvault_utils.datetime2e(email_info[imap_utils.GIMAPFetcher.IMAP_INTERNALDATE]),
                     self.FLAGS_K      : email_info[imap_utils.GIMAPFetcher.IMAP_FLAGS],
                     self.SUBJECT_K    : subject,
                     self.MSGID_K      : msgid
                   }
        
        json.dump(meta_obj, meta_desc, ensure_ascii = False)
        
        meta_desc.flush()
        meta_desc.close()
         
        return email_info[imap_utils.GIMAPFetcher.GMAIL_ID]
    
    def bury_chat(self, chat_info, local_dir = None, compress = False):   
        """
            Like bury email but with a special label: gmvault-chats
            Arguments:
            chat_info: the chat content
            local_dir: intermediary dir
            compress : if compress is True, use gzip compression
        """
        extra_labels = ['gmvault-chats']
        
        return self.bury_email(chat_info, local_dir, compress, extra_labels)
        
    def bury_email(self, email_info, local_dir = None, compress = False, extra_labels = []): #pylint:disable=W0102
        """
           store all email info in 2 files (.meta and .eml files)
           Arguments:
             email_info: the email content
             local_dir : intermdiary dir (month dir)
             compress  : if compress is True, use gzip compression
        """
        
        if local_dir:
            the_dir = '%s/%s' % (self._db_dir, local_dir)
            gmvault_utils.makedirs(the_dir)
        else:
            the_dir = self._db_dir
        
        data_path = self.DATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID])
        
        # if the data has to be encrypted
        if self._encrypt_data:
            data_path = '%s.crypt' % (data_path)
        
        if compress:
            data_path = '%s.gz' % (data_path)
            data_desc = gzip.open(data_path, 'wb')
        else:
            data_desc = open(data_path, 'wb')
            
        if self._encrypt_data:
            # need to be done for every encryption
            cipher = self.get_encryption_cipher()
            cipher.initCTR()
            data_desc.write(cipher.encryptCTR(email_info[imap_utils.GIMAPFetcher.EMAIL_BODY]))
        else:
            data_desc.write(email_info[imap_utils.GIMAPFetcher.EMAIL_BODY])
            
        # parse header fields to extract subject and msgid
        subject, msgid = self.parse_header_fields(email_info[imap_utils.GIMAPFetcher.IMAP_HEADER_FIELDS_KEY])
        
        # need to convert labels that are number as string
        # come from imap_lib when label is a number
        labels = [ str(elem) for elem in  email_info[imap_utils.GIMAPFetcher.GMAIL_LABELS] ]
        
        labels.extend(extra_labels) #add extra labels
        
        #create json structure for metadata
        meta_obj = { 
                     self.ID_K         : email_info[imap_utils.GIMAPFetcher.GMAIL_ID],
                     self.LABELS_K     : labels,
                     self.FLAGS_K      : email_info[imap_utils.GIMAPFetcher.IMAP_FLAGS],
                     self.THREAD_IDS_K : email_info[imap_utils.GIMAPFetcher.GMAIL_THREAD_ID],
                     self.INT_DATE_K   : gmvault_utils.datetime2e(email_info[imap_utils.GIMAPFetcher.IMAP_INTERNALDATE]),
                     self.SUBJECT_K    : subject,
                     self.MSGID_K      : msgid
                   }
        
        meta_desc = open(self.METADATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID]), 'w')
        
        json.dump(meta_obj, meta_desc, ensure_ascii = False)
        
        meta_desc.flush()
        meta_desc.close()
        
        data_desc.flush()
        data_desc.close()
        
        return email_info[imap_utils.GIMAPFetcher.GMAIL_ID]
    
    def get_directory_from_id(self, a_id, a_local_dir = None):
        """
           If a_local_dir (yy_mm dir) is passed, check that metadata file exists and return dir
           Return the directory path if id located.
           Return None if not found
        """
        filename = '%s.meta' % (a_id)
        
        #local_dir can be passed to avoid scanning the filesystem (because of WIN7 fs weaknesses)
        if a_local_dir:
            the_dir = '%s/%s' % (self._db_dir, a_local_dir)
            if os.path.exists(self.METADATA_FNAME % (the_dir, a_id)):
                return the_dir
            else:
                return None
        
        # first look in cache
        for the_dir in self.fsystem_info_cache:
            if filename in self.fsystem_info_cache[the_dir]:
                return the_dir
        
        #walk the filesystem
        for the_dir, _, files in os.walk(os.path.abspath(self._db_dir)):
            self.fsystem_info_cache[the_dir] = files
            for filename in fnmatch.filter(files, filename):
                return the_dir
        
        return None
    
    def _get_data_file_from_id(self, a_dir, a_id):
        """
           Return data file from the id
        """
        data_p = self.DATA_FNAME % (a_dir, a_id)
        
        # check if encrypted and compressed or not
        if os.path.exists('%s.crypt.gz' % (data_p)):
            data_fd = gzip.open('%s.crypt.gz' % (data_p), 'r')
        elif os.path.exists('%s.gz' % (data_p)):
            data_fd = gzip.open('%s.gz' % (data_p), 'r')
        elif os.path.exists('%s.crypt' % (data_p)):
            data_fd = open('%s.crypt' % (data_p), 'r')
        else:
            data_fd = open(data_p)
        
        return data_fd
    
    def _get_metadata_file_from_id(self, a_dir, a_id):
        """
           metadata file
        """
        meta_p = self.METADATA_FNAME % (a_dir, a_id)
       
        return open(meta_p)
    
    def quarantine_email(self, a_id):
        """
           Quarantine the email
        """
        #get the dir where the email is stored
        the_dir = self.get_directory_from_id(a_id)
        
        data = self.DATA_FNAME % (the_dir, a_id)
        
        # check if encrypted and compressed or not
        if os.path.exists('%s.crypt.gz' % (data)):
            data = '%s.crypt.gz' % (data)
        elif os.path.exists('%s.gz' % (data)):
            data = '%s.gz' % (data)
        elif os.path.exists('%s.crypt' % (data)):
            data = '%s.crypt' % (data)
        
        meta = self.METADATA_FNAME % (the_dir, a_id)

        #remove files if already quarantined
        q_data_path = os.path.join(self._quarantine_dir, os.path.basename(data))
        q_meta_path = os.path.join(self._quarantine_dir, os.path.basename(meta))

        if os.path.exists(q_data_path):
            os.remove(q_data_path)        
        
        if os.path.exists(q_meta_path):
            os.remove(q_meta_path)

        shutil.move(data, self._quarantine_dir)
        shutil.move(meta, self._quarantine_dir)
        
    def email_encrypted(self, a_email_fn):
        """
           True is filename contains .crypt otherwise False
        """
        basename = os.path.basename(a_email_fn)
        if self.ENCRYPTED_RE.match(basename):
            return True
        else:
            return False
        
    def unbury_email(self, a_id):
        """
           Restore email info from info stored on disk
           Return a tuple (meta, data)
        """
        the_dir = self.get_directory_from_id(a_id)
        
        data_fd = self._get_data_file_from_id(the_dir, a_id)
        
        if self.email_encrypted(data_fd.name):
            LOG.debug("Restore encrypted email %s" % (a_id))
            # need to be done for every encryption
            cipher = self.get_encryption_cipher()
            cipher.initCTR()
            data = cipher.decryptCTR(data_fd.read())
        else:
            data = data_fd.read()
        
        return (self.unbury_metadata(a_id, the_dir), data)
    
    def unbury_metadata(self, a_id, a_id_dir = None):
        """
           Get metadata info from DB
        """
        if not a_id_dir:
            a_id_dir = self.get_directory_from_id(a_id)
        
        meta_fd = self._get_metadata_file_from_id(a_id_dir, a_id)
    
        metadata = json.load(meta_fd)
        
        metadata[self.INT_DATE_K] =  gmvault_utils.e2datetime(metadata[self.INT_DATE_K])
        
        # force convertion of labels as string because IMAPClient
        # returns a num when the label is a number (ie. '00000')
        metadata[self.LABELS_K] = [ str(elem) for elem in  metadata[self.LABELS_K] ]
        
        return metadata
    
    def delete_emails(self, emails_info, msg_type):
        """
           Delete all emails and metadata with ids
        """
        if msg_type == 'email':
            db_dir = self._db_dir
        else:
            db_dir = self._chats_dir
        
        for (a_id, date_dir) in emails_info:
            
            the_dir = '%s/%s' % (db_dir, date_dir)
            
            data_p      = self.DATA_FNAME % (the_dir, a_id)
            comp_data_p = '%s.gz' % (data_p)
            cryp_comp_data_p = '%s.crypt.gz' % (data_p)
            
            metadata_p  = self.METADATA_FNAME % (the_dir, a_id)
            
            #delete files if they exists
            if os.path.exists(data_p):
                os.remove(data_p)
            elif os.path.exists(comp_data_p):
                os.remove(comp_data_p)
            elif os.path.exists(cryp_comp_data_p):
                os.remove(comp_data_p)   
            
            if os.path.exists(metadata_p):
                os.remove(metadata_p)
   
class GMVaulter(object):
    """
       Main object operating over gmail
    """ 
    NB_GRP_OF_ITEMS         = 1400
    EMAIL_RESTORE_PROGRESS  = 'email_last_id.restore'
    CHAT_RESTORE_PROGRESS   = 'chat_last_id.restore'
    EMAIL_SYNC_PROGRESS     = 'email_last_id.sync'
    CHAT_SYNC_PROGRESS      = 'chat_last_id.sync'
    
    OP_EMAIL_RESTORE = "EM_RESTORE"
    OP_EMAIL_SYNC    = "EM_SYNC"
    OP_CHAT_RESTORE  = "CH_RESTORE"
    OP_CHAT_SYNC    = "CH_SYNC"
    
    OP_TO_FILENAME = { OP_EMAIL_RESTORE : EMAIL_RESTORE_PROGRESS,
                       OP_EMAIL_SYNC    : EMAIL_SYNC_PROGRESS,
                       OP_CHAT_RESTORE  : CHAT_RESTORE_PROGRESS,
                       OP_CHAT_SYNC     : CHAT_SYNC_PROGRESS
                     }
    
    
    def __init__(self, db_root_dir, host, port, login, credential, read_only_access = True, use_encryption = False): #pylint:disable-msg=R0913
        """
           constructor
        """   
        self.db_root_dir = db_root_dir
        
        #create dir if it doesn't exist
        gmvault_utils.makedirs(self.db_root_dir)
        
        #keep track of login email
        self.login = login
            
        # create source and try to connect
        self.src = imap_utils.GIMAPFetcher(host, port, login, credential, readonly_folder = read_only_access)
        
        self.src.connect()
        
        self.use_encryption = use_encryption
        
        #to report gmail imap problems
        self.error_report = { 'empty' : [] ,
                              'cannot_be_fetched'  : [],
                              'emails_in_quarantine' : [],
                              'reconnections' : 0}
        
        #instantiate gstorer
        self.gstorer =  GmailStorer(self.db_root_dir, self.use_encryption)
        
        #timer used to mesure time spent in the different values
        self.timer = gmvault_utils.Timer()
        
    @classmethod
    def get_imap_request_btw_2_dates(cls, begin_date, end_date):
        """
           Return the imap request for those 2 dates
        """
        imap_req = 'Since %s Before %s' % (gmvault_utils.datetime2imapdate(begin_date), gmvault_utils.datetime2imapdate(end_date))
        
        return imap_req
    
    def get_error_report(self):
        """
           Return the error report
        """
        the_str = "\n================================================================\n"\
              "Number of reconnections: %d.\nNumber of emails quarantined: %d.\n" \
              "Number of emails that could not be fetched: %d.\n" \
              "Number of emails that were returned empty by gmail: %d\n================================================================" \
              % (self.error_report['reconnections'], \
                 len(self.error_report['emails_in_quarantine']), \
                 len(self.error_report['cannot_be_fetched']), \
                 len(self.error_report['empty'])
                )
        
        return the_str
        
    def _sync_between(self, begin_date, end_date, storage_dir, compress = True):
        """
           sync between 2 dates
        """
        #create storer
        gstorer = GmailStorer(storage_dir, self.use_encryption)
        
        #search before the next month
        imap_req = self.get_imap_request_btw_2_dates(begin_date, end_date)
        
        ids = self.src.search(imap_req)
                              
        #loop over all ids, get email store email
        for the_id in ids:
            
            #retrieve email from destination email account
            data      = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_ALL_INFO)
            
            file_path = gstorer.bury_email(data[the_id], compress = compress)
            
            LOG.critical("Stored email %d in %s" %(the_id, file_path))
        
    @classmethod
    def _get_next_date(cls, a_current_date, start_month_beginning = False):
        """
           return the next date necessary to build the imap req
        """
        if start_month_beginning:
            dummy_date   = a_current_date.replace(day=1)
        else:
            dummy_date   = a_current_date
            
        # the next date = current date + 1 month
        return dummy_date + datetime.timedelta(days=31)
        
    @classmethod
    def check_email_on_disk(cls, a_gstorer, a_id, a_dir = None):
        """
           Factory method to create the object if it exists
        """
        try:
            a_dir = a_gstorer.get_directory_from_id(a_id, a_dir)
           
            if a_dir:
                return a_gstorer.unbury_metadata(a_id, a_dir) 
            
        except ValueError, json_error:
            LOG.exception("Cannot read file %s. Try to fetch the data again" % ('%s.meta' % (a_id)), json_error )
        
        return None
    
    @classmethod
    def _metadata_needs_update(cls, curr_metadata, new_metadata, chat_metadata = False):
        """
           Needs update
        """
        if curr_metadata[GmailStorer.ID_K] != new_metadata['X-GM-MSGID']:
            raise Exception("Gmail id has changed for %s" % (curr_metadata['id']))
                
        #check flags   
        prev_set = set(new_metadata['FLAGS'])    
        
        for flag in curr_metadata['flags']:
            if flag not in prev_set:
                return True
            else:
                prev_set.remove(flag)
        
        if len(prev_set) > 0:
            return True
        
        #check labels
        prev_labels = set(new_metadata['X-GM-LABELS'])
        
        if chat_metadata: #add gmvault-chats labels
            prev_labels.add(GmailStorer.CHAT_GM_LABEL)
            
        
        for label in curr_metadata['labels']:
            if label not in prev_labels:
                return True
            else:
                prev_labels.remove(label)
        
        if len(prev_labels) > 0:
            return True
        
        return False
    
    
    def _check_email_db_ownership(self, ownership_control):
        """
           Check email database ownership.
           If ownership control activated then fail if a new additional owner is added.
           Else if no ownership control allow one more user and save it in the list of owners
           
           Return the number of owner this will be used to activate or not the db clean.
           Activating a db cleaning on a multiownership db would be a catastrophy as it would delete all
           the emails from the others users.
        """
        #check that the gmvault-db is not associated with another user
        db_owners = self.gstorer.get_db_owners()
        if ownership_control:
            if len(db_owners) > 0 and self.login not in db_owners: #db owner should not be different unless bypass activated
                raise Exception("The email database %s is already associated with one or many logins: %s."\
                                " Use option (-m, --multiple-db-owner) if you want to link it with %s" \
                                % (self.db_root_dir, ", ".join(db_owners), self.login))
        else:
            if len(db_owners) == 0:
                LOG.critical("Establish %s as the owner of the Gmvault db %s." % (self.login, self.db_root_dir))  
            elif len(db_owners) > 0 and self.login not in db_owners:
                LOG.critical("The email database %s is hosting emails from %s. It will now also store emails from %s" \
                             % (self.db_root_dir, ", ".join(db_owners), self.login))
                
        #try to save db_owner in the list of owners
        self.gstorer.store_db_owner(self.login)
    
    def _sync_chats(self, imap_req, compress, restart):
        """
           backup the chat messages
        """
        exception_not_launched = True
        
        LOG.debug("Before selection")
        chat_dir = self.src.find_and_select_chats_folder()
        LOG.debug("Selection is finished")

        if chat_dir:
            #imap_ids = self.src.search({ 'type': 'imap', 'req': 'ALL' })
            imap_ids = self.src.search(imap_req)
            
            # check if there is a restart
            if restart:
                LOG.critical("Restart mode activated. Need to find information in Gmail, be patient ...")
                imap_ids = self.get_gmails_ids_left_to_sync(self.OP_CHAT_SYNC, imap_ids)
            
            total_nb_chats_to_process = len(imap_ids) # total number of emails to get
            
            LOG.critical("%d chat messages to be fetched." % (total_nb_chats_to_process))
            
            nb_chats_processed = 0
    
            try:
                #loop over all ids, get email store email
                for the_id in imap_ids:
                    try:
                        
                        gid = None
                        
                        LOG.debug("\nProcess imap chat id %s" % ( the_id ))
                        
                        #get everything but data
                        new_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA )
                        
                        if new_data.get(the_id, None):
                            
                            gid = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                            
                            the_dir      = self.gstorer.get_sub_chats_dir()
                            
                            LOG.critical("Process chat num %d (imap_id:%s) into %s." % (nb_chats_processed, the_id, the_dir))
                        
                            #pass the dir and the ID
                            curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                           new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                           the_dir)
                            
                            #if on disk check that the data is not different
                            if curr_metadata:
                                
                                if self._metadata_needs_update(curr_metadata, new_data[the_id], chat_metadata = True):
                                    
                                    LOG.debug("Chat with imap id %s and gmail id %s has changed. Updated it." % (the_id, gid))
                                    
                                    #restore everything at the moment
                                    gid  = self.gstorer.bury_chat_metadata(new_data[the_id], local_dir = the_dir)
                                    
                                    #update local index id gid => index per directory to be thought out
                                else:
                                    LOG.debug("The metadata for chat %s already exists and is identical to the one on GMail." % (gid))
                            else:  
                                
                                #get the data
                                email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                                
                                new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                                
                                # store data on disk within year month dir 
                                gid  = self.gstorer.bury_chat(new_data[the_id], local_dir = the_dir, compress = compress)
                                
                                #update local index id gid => index per directory to be thought out
                                LOG.debug("Create and store chat with imap id %s, gmail id %s." % (the_id, gid))   
                            
                        else:
                            # case when gmail IMAP server returns OK without any data whatsoever
                            # eg. imap uid 142221L ignore it
                            self.error_report['empty'].append((the_id, None))
                        
                        nb_chats_processed += 1    
                        
                        #indicate every 50 messages the number of messages left to process
                        left_emails = (total_nb_chats_to_process - nb_chats_processed)
                        
                        if (nb_chats_processed % 50) == 0 and (left_emails > 0):
                            elapsed = self.timer.elapsed() #elapsed time in seconds
                            LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                         (nb_chats_processed,  self.timer.seconds_to_human_time(elapsed), \
                                          left_emails, \
                                          self.timer.estimate_time_left(nb_chats_processed, elapsed, left_emails)))
                        
                        # save id every 10 restored emails
                        if (nb_chats_processed % 10) == 0:
                            if gid:
                                self.save_lastid(self.OP_CHAT_SYNC, gid)
                        
                    except imaplib.IMAP4.abort, _:
                        # imap abort error 
                        # ignore it 
                        # will have to do something with these ignored messages
                        LOG.critical("Error while fetching message with imap id %s." % (the_id))
                        LOG.critical("\n=== Exception traceback ===\n")
                        LOG.critical(gmvault_utils.get_exception_traceback())
                        LOG.critical("=== End of Exception traceback ===\n")
                        try:
                            #try to get the gmail_id
                            curr = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
                        except Exception, _: #pylint:disable-msg=W0703
                            curr = None
                            LOG.critical("Error when trying to get gmail id for message with imap id %s." % (the_id))
                            LOG.critical("Disconnect, wait for 20 sec then reconnect.")
                            self.src.disconnect()
                            #could not fetch the gm_id so disconnect and sleep
                            #sleep 10 sec
                            time.sleep(10)
                            LOG.critical("Reconnecting ...")
                            self.src.connect()
                            
                        if curr:
                            gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                        else:
                            gmail_id = None
                            
                        #add ignored id
                        self.error_report['cannot_be_fetched'].append((the_id, gmail_id))
                        
                        LOG.critical("Forced to ignore message with imap id %s, (gmail id %s)." % (the_id, (gmail_id if gmail_id else "cannot be read")))
                        
                    except imaplib.IMAP4.error, error:
                        # check if this is a cannot be fetched error 
                        # I do not like to do string guessing within an exception but I do not have any choice here
                        LOG.critical("Error while fetching message with imap id %s." % (the_id))
                        LOG.critical("\n=== Exception traceback ===\n")
                        LOG.critical(gmvault_utils.get_exception_traceback())
                        LOG.critical("=== End of Exception traceback ===\n")
                         
                        #quarantine emails that have raised an abort error
                        if str(error).find("'Some messages could not be FETCHed (Failure)'") >= 0:
                            try:
                                #try to get the gmail_id
                                LOG.critical("One more attempt. Trying to fetch the Gmail ID for %s" % (the_id) )
                                curr = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
                            except Exception, _: #pylint:disable-msg=W0703
                                curr = None
                            
                            if curr:
                                gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                            else:
                                gmail_id = None
                            
                            #add ignored id
                            self.error_report['cannot_be_fetched'].append((the_id, gmail_id))
                            
                            LOG.critical("Ignore message with imap id %s, (gmail id %s)" % (the_id, (gmail_id if gmail_id else "cannot be read")))
                        
                        else:
                            raise error #rethrow error
            finally:
                self.src.select_all_mail_folder() #always reselect all mail folder
        else:
            imap_ids = []    
        return imap_ids
    
    
    def _sync_emails(self, imap_req, compress, restart):
        """
           First part of the double pass strategy: 
           - create and update emails in db
           
        """
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # check if there is a restart
        if restart:
            LOG.critical("Restart mode activated for emails. Need to find information in Gmail, be patient ...")
            imap_ids = self.get_gmails_ids_left_to_sync(self.OP_EMAIL_SYNC, imap_ids)
        
        total_nb_emails_to_process = len(imap_ids) # total number of emails to get
        
        LOG.critical("%d emails to be fetched." % (total_nb_emails_to_process))
        
        nb_emails_processed = 0
        
        for the_id in imap_ids:
            
            try:
                
                gid = None
                
                LOG.debug("\nProcess imap id %s" % ( the_id ))
                
                #get everything but data
                new_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_ALL_BUT_DATA )
                
                if new_data.get(the_id, None):
                    
                    gid = new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                    
                    the_dir      = gmvault_utils.get_ym_from_datetime(new_data[the_id][imap_utils.GIMAPFetcher.IMAP_INTERNALDATE])
                    
                    LOG.critical("Process email num %d (imap_id:%s) from %s." % (nb_emails_processed, the_id, the_dir))
                
                    #pass the dir and the ID
                    curr_metadata = GMVaulter.check_email_on_disk( self.gstorer , \
                                                                   new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                   the_dir)
                    
                    #if on disk check that the data is not different
                    if curr_metadata:
                        
                        LOG.debug("metadata for %s already exists. Check if different." % (gid))
                        
                        if self._metadata_needs_update(curr_metadata, new_data[the_id]):
                            
                            LOG.debug("Chat with imap id %s and gmail id %s has changed. Updated it." % (the_id, gid))
                            
                            #restore everything at the moment
                            gid  = self.gstorer.bury_metadata(new_data[the_id], local_dir = the_dir)
                            
                            #update local index id gid => index per directory to be thought out
                        else:
                            LOG.debug("On disk metadata for %s is up to date." % (gid))
                    else:  
                        
                        #get the data
                        email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                        
                        new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                        
                        # store data on disk within year month dir 
                        gid  = self.gstorer.bury_email(new_data[the_id], local_dir = the_dir, compress = compress)
                        
                        #update local index id gid => index per directory to be thought out
                        LOG.debug("Create and store email with imap id %s, gmail id %s." % (the_id, gid))   
                    
                else:
                    # case when gmail IMAP server returns OK without any data whatsoever
                    # eg. imap uid 142221L ignore it
                    self.error_report['empty'].append((the_id, None))
                
                nb_emails_processed += 1
                
                #indicate every 50 messages the number of messages left to process
                left_emails = (total_nb_emails_to_process - nb_emails_processed)
                
                if (nb_emails_processed % 50) == 0 and (left_emails > 0):
                    elapsed = self.timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                 (nb_emails_processed,  \
                                  self.timer.seconds_to_human_time(elapsed), left_emails, \
                                  self.timer.estimate_time_left(nb_emails_processed, elapsed, left_emails)))
                
                # save id every 10 restored emails
                if (nb_emails_processed % 10) == 0:
                    if gid:
                        self.save_lastid(self.OP_EMAIL_SYNC, gid)
                
            except imaplib.IMAP4.abort, _:
                # imap abort error 
                # ignore it 
                # will have to do something with these ignored messages
                LOG.critical("Error while fetching message with imap id %s." % (the_id))
                LOG.critical("\n=== Exception traceback ===\n")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")
                try:
                    #try to get the gmail_id
                    curr = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
                except Exception, _: #pylint:disable-msg=W0703
                    curr = None
                    LOG.critical("Error when trying to get gmail id for message with imap id %s." % (the_id))
                    LOG.critical("Disconnect, wait for 20 sec then reconnect.")
                    self.src.disconnect()
                    #could not fetch the gm_id so disconnect and sleep
                    #sleep 20 sec
                    time.sleep(20)
                    LOG.critical("Reconnecting ...")
                    self.src.connect()
                    
                if curr:
                    gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                else:
                    gmail_id = None
                    
                #add ignored id
                self.error_report['cannot_be_fetched'].append((the_id, gmail_id))
                
                LOG.critical("Forced to ignore message with imap id %s, (gmail id %s)." % (the_id, (gmail_id if gmail_id else "cannot be read")))
                
            except imaplib.IMAP4.error, error:
                # check if this is a cannot be fetched error 
                # I do not like to do string guessing within an exception but I do not have any choice here
                LOG.critical("Error while fetching message with imap id %s." % (the_id))
                LOG.critical("\n=== Exception traceback ===\n")
                LOG.critical(gmvault_utils.get_exception_traceback())
                LOG.critical("=== End of Exception traceback ===\n")
                 
                #quarantine emails that have raised an abort error
                if str(error).find("'Some messages could not be FETCHed (Failure)'") >= 0:
                    try:
                        #try to get the gmail_id
                        LOG.critical("One more attempt. Trying to fetch the Gmail ID for %s" % (the_id) )
                        curr = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID) 
                    except Exception, _: #pylint:disable-msg=W0703
                        curr = None
                    
                    if curr:
                        gmail_id = curr[the_id][imap_utils.GIMAPFetcher.GMAIL_ID]
                    else:
                        gmail_id = None
                    
                    #add ignored id
                    self.error_report['cannot_be_fetched'].append((the_id, gmail_id))
                    
                    LOG.critical("Ignore message with imap id %s, (gmail id %s)" % (the_id, (gmail_id if gmail_id else "cannot be read")))
                
                else:
                    raise error #rethrow error
        return imap_ids
    
    def sync(self, imap_req = imap_utils.GIMAPFetcher.IMAP_ALL, compress_on_disk = True, db_cleaning = False, ownership_checking = True, \
            restart = False, emails_only = False, chats_only = False):
        """
           sync mode 
        """
        #check ownership to have one email per db unless user wants different
        #save the owner if new
        self._check_email_db_ownership(ownership_checking)
                
        if not compress_on_disk:
            LOG.critical("Disable compression when storing emails.")
            
        if self.use_encryption:
            LOG.critical("Encryption activated. All emails will be encrypted before to be stored.")
            LOG.critical("Please take care of the encryption key stored in (%s) or all"\
                         " your stored emails will become unreadable." % (GmailStorer.get_encryption_key_path(self.db_root_dir)))
        
        self.timer.start() #start syncing emails
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails synchronization.\n")
            self._sync_emails(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("Skip emails synchronization.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats synchronization.\n")
            self._sync_chats(imap_req, compress = compress_on_disk, restart = restart)
        else:
            LOG.critical("\nSkip chats synchronization.\n")
        
        #delete supress emails from DB since last sync
        if len(self.gstorer.get_db_owners()) <= 1:
            self.check_clean_db(db_cleaning)
        else:
            LOG.critical("Deactivate database cleaning on a multi-owners Gmvault db.")
        
        LOG.critical("Synchronisation operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
        
        return self.error_report

    
    def _delete_sync(self, imap_ids, db_gmail_ids, db_gmail_ids_info, msg_type):
        """
           Delete emails from the database if necessary
           imap_ids      : all remote imap_ids to check
           db_gmail_ids_info : info read from metadata
           msg_type : email or chat
        """
        
        # optimize nb of items
        nb_items = self.NB_GRP_OF_ITEMS if len(imap_ids) >= self.NB_GRP_OF_ITEMS else len(imap_ids)
        
        LOG.critical("Call Gmail to check the stored %ss against the Gmail %ss ids and see which ones have been deleted.\n\n"\
                     "Might take few minutes ...\n" % (msg_type, msg_type)) 
         
        #calculate the list elements to delete
        #query nb_items items in one query to minimise number of imap queries
        for group_imap_id in itertools.izip_longest(fillvalue=None, *[iter(imap_ids)]*nb_items):
            
            # if None in list remove it
            if None in group_imap_id: 
                group_imap_id = [ im_id for im_id in group_imap_id if im_id != None ]
            
            #LOG.debug("Interrogate Gmail Server for %s" % (str(group_imap_id)))
            data = self.src.fetch(group_imap_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID)
            
            # syntax for 2.7 set comprehension { data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data }
            # need to create a list for 2.6
            db_gmail_ids.difference_update([data[key][imap_utils.GIMAPFetcher.GMAIL_ID] for key in data ])
            
            if len(db_gmail_ids) == 0:
                break
        
        LOG.critical("Will delete %s %s(s) from gmvault db.\n" % (len(db_gmail_ids), msg_type) )
        for gm_id in db_gmail_ids:
            LOG.critical("gm_id %s not in the Gmail server. Delete it." % (gm_id))
            self.gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])], msg_type)
        
    def get_gmails_ids_left_to_sync(self, op_type, imap_ids):
        """
           Get the ids that still needs to be sync
           Return a list of ids
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen, send the error to the software developers." % (op_type))
        
        
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id.sync file %s doesn't exist.\nSync the full list of backed up emails." %(filepath))
            return imap_ids
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        
        new_gmail_ids = imap_ids
        
        try:
            #get imap_id from stored gmail_id
            dummy = self.src.search({'type':'imap', 'req':'X-GM-MSGID %s' % (last_id)})
            
            imap_id = dummy[0]
            last_id_index = imap_ids.index(imap_id)
            LOG.critical("Restart from gmail id %s (imap id %s)." % (last_id, imap_id))
            new_gmail_ids = imap_ids[last_id_index:]   
        except Exception, _: #ignore any exception and try to get all ids in case of problems. pylint:disable=W0703
            #element not in keys return current set of keys
            LOG.critical("Error: Cannot restore from last restore gmail id. It is not in Gmail."\
                         " Sync the complete list of gmail ids requested from Gmail.")
        
        return new_gmail_ids
        
    def check_clean_db(self, db_cleaning):
        """
           Check and clean the database (remove file that are not anymore in Gmail
        """
        owners = self.gstorer.get_db_owners()
        if not db_cleaning: #decouple the 2 conditions for activating cleaning
            LOG.debug("db_cleaning is off so ignore removing deleted emails from disk.")
            return
        elif len(owners) > 1:
            LOG.critical("Gmvault db hosting emails from different accounts: %s.\nCannot activate database cleaning." % (", ".join(owners)))
            return
        else:
            LOG.critical("Look for emails/chats that are in the Gmvault db but not in Gmail servers anymore.\n")
            
            #get gmail_ids from db
            LOG.critical("Read all gmail ids from the Gmvault db. It might take a bit of time ...\n")
            
            timer = gmvault_utils.Timer() # needed for enhancing the user information
            timer.start()
            
            db_gmail_ids_info = self.gstorer.get_all_existing_gmail_ids()
        
            LOG.critical("Found %s email(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
        
            #create a set of keys
            db_gmail_ids = set(db_gmail_ids_info.keys())
            
            # get all imap ids in All Mail
            imap_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL)
            
            LOG.debug("Got %s emails imap_id(s) from the Gmail Server." % (len(imap_ids)))
            
            #delete supress emails from DB since last sync
            self._delete_sync(imap_ids, db_gmail_ids, db_gmail_ids_info, 'email')
            
            # get all chats ids
            try:
                
                db_gmail_ids_info = self.gstorer.get_all_chats_gmail_ids()
                
                LOG.critical("Found %s chat(s) in the Gmvault db.\n" % (len(db_gmail_ids_info)) )
                
                chat_dir = self.src.find_and_select_chats_folder()

                if chat_dir:
                    chat_ids = self.src.search(imap_utils.GIMAPFetcher.IMAP_ALL)
                    db_chat_ids = set(db_gmail_ids_info.keys())
                
                    LOG.debug("Got %s chat imap_ids from the Gmail Server." % (len(chat_ids)))
            
                    #delete supress emails from DB since last sync
                    self._delete_sync(chat_ids, db_chat_ids, db_gmail_ids_info , 'chat')
                else:
                    LOG.critical("Chats IMAP Directory not visible on Gmail. Ignore deletion of chats.")
                
            finally:
                self.src.select_all_mail_folder()
            
            LOG.critical("\nDeletion checkup done in %s." % (timer.elapsed_human_time()))
            
    
    def remote_sync(self):
        """
           Sync with a remote source (IMAP mirror or cloud storage area)
        """
        #sync remotely 
        pass
        
    
    def save_lastid(self, op_type, gm_id):
        """
           Save the passed gmid in last_id.restore
           For the moment reopen the file every time
        """
        
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen, send the error to the software developers." % (op_type))
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)  
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)  
        
        the_fd = open(filepath, 'w')
        
        json.dump({
                    'last_id' : gm_id  
                  }, the_fd)
        
        the_fd.close()
        
    def get_gmails_ids_left_to_restore(self, op_type, db_gmail_ids_info):
        """
           Get the ids that still needs to be restored
           Return a dict key = gm_id, val = directory
        """
        filename = self.OP_TO_FILENAME.get(op_type, None)
        
        if not filename:
            raise Exception("Bad Operation (%s) in save_last_id. This should not happen, send the error to the software developers." % (op_type))
        
        
        #filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, filename)
        filepath = '%s/%s_%s' % (self.gstorer.get_info_dir(), self.login, filename)
        
        if not os.path.exists(filepath):
            LOG.critical("last_id restore file %s doesn't exist.\nRestore the full list of backed up emails." %(filepath))
            return db_gmail_ids_info
        
        json_obj = json.load(open(filepath, 'r'))
        
        last_id = json_obj['last_id']
        
        last_id_index = -1
        try:
            keys = db_gmail_ids_info.keys()
            last_id_index = keys.index(last_id)
            LOG.critical("Restart from gmail id %s." % (last_id))
        except ValueError, _:
            #element not in keys return current set of keys
            LOG.error("Cannot restore from last restore gmail id. It is not in the disk database.")
        
        new_gmail_ids_info = collections_utils.OrderedDict()
        if last_id_index != -1:
            for key in db_gmail_ids_info.keys()[last_id_index+1:]:
                new_gmail_ids_info[key] =  db_gmail_ids_info[key]
        else:
            new_gmail_ids_info = db_gmail_ids_info    
            
        return new_gmail_ids_info 
           
    def restore(self, pivot_dir = None, extra_labels = [], restart = False, emails_only = False, chats_only = False): #pylint:disable=W0102
        """
           Restore emails in a gmail account
        """
        self.timer.start() #start restoring
        
        if not chats_only:
            # backup emails
            LOG.critical("Start emails restoration.\n")
            
            if pivot_dir:
                LOG.critical("Quick mode activated. Will only restore all emails since %s.\n" % (pivot_dir))
            
            self.restore_emails(pivot_dir, extra_labels, restart)
        else:
            LOG.critical("Skip emails restoration.\n")
        
        if not emails_only:
            # backup chats
            LOG.critical("Start chats restoration.\n")
            self.restore_chats(extra_labels, restart)
        else:
            LOG.critical("Skip chats restoration.\n")
        
        LOG.critical("Restore operation performed in %s.\n" \
                     % (self.timer.seconds_to_human_time(self.timer.elapsed())))
       
    def common_restore(self, the_type, db_gmail_ids_info, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           common_restore 
        """
        if the_type == "chats":
            msg = "chats"
            op  = self.OP_CHAT_RESTORE
        elif the_type == "emails":
            msg = "emails"
            op  = self.OP_EMAIL_RESTORE
        
        LOG.critical("Restore %s in gmail account %s." % (msg, self.login) ) 
        
        LOG.critical("Read %s info from %s gmvault-db." % (msg, self.db_root_dir))
        
        LOG.critical("Total number of %s to restore %s." % (msg, len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(op, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all %s id left to restore. Still %s %s to do.\n" % (msg, total_nb_emails_to_restore, msg) )
        
        existing_labels = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored = 0 #to count nb of emails restored
        timer = gmvault_utils.Timer() # needed for enhancing the user information
        timer.start()
        
        for gm_id in db_gmail_ids_info:
            
            LOG.critical("Restore %s with id %s." % (msg, gm_id))
            
            email_meta, email_data = self.unbury_email(gm_id)
            
            LOG.debug("Unburied %s with id %s." % (msg, gm_id))
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[self.gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in existing_labels]
            
            #create the non existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for %s with id %s." % (msg, gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
            
            try:
                #restore email
                self.src.push_email(email_data, \
                                    email_meta[self.gstorer.FLAGS_K] , \
                                    email_meta[self.gstorer.INT_DATE_K], \
                                    labels)
                
                LOG.debug("Pushed %s with id %s." % (msg, gm_id))
                
                nb_emails_restored += 1
                
                #indicate every 10 messages the number of messages left to process
                left_emails = (total_nb_emails_to_restore - nb_emails_restored)
                
                if (nb_emails_restored % 50) == 0 and (left_emails > 0): 
                    elapsed = timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d %s in %s. %d left to be restored (time estimate %s).==\n" % \
                                 (nb_emails_restored, msg, timer.seconds_to_human_time(elapsed), \
                                  left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_restored % 10) == 0:
                    self.save_lastid(self.OP_CHAT_RESTORE, gm_id)
                    
            except imaplib.IMAP4.abort, abort:
                
                # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                if str(abort).find("=> Gmvault ssl socket error: EOF") >= 0:
                    LOG.critical("Quarantine %s with gm id %s from %s. "\
                                 "GMAIL IMAP cannot restore it: err={%s}" % (msg, gm_id, db_gmail_ids_info[gm_id], str(abort)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise abort
        
            except imaplib.IMAP4.error, err:
                
                LOG.error("Catched IMAP Error %s" % (str(err)))
                LOG.exception(err)
                
                #When the email cannot be read from Database because it was empty when returned by gmail imap
                #quarantine it.
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine %s with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (msg, gm_id, db_gmail_ids_info[gm_id], str(err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise err
            except imap_utils.PushEmailError, p_err:
                LOG.error("Catch the following exception %s" % (str(p_err)))
                LOG.exception(p_err)
                
                if p_err.quarantined():
                    LOG.critical("Quarantine %s with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (msg, gm_id, db_gmail_ids_info[gm_id], str(p_err)))
                    self.gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise p_err          
            except Exception, err:
                LOG.error("Catch the following exception %s" % (str(err)))
                LOG.exception(err)
                raise err
            
            
        return self.error_report 
        
    def restore_chats(self, extra_labels = [], restart = False): #pylint:disable=W0102
        """
           restore chats
        """
        LOG.critical("Restore chats in gmail account %s." % (self.login) ) 
                
        #crack email database
        gstorer = GmailStorer(self.db_root_dir, self.use_encryption)
        
        LOG.critical("Read chats info from %s gmvault-db." % (self.db_root_dir))
        
        #for the restore (save last_restored_id in .gmvault/last_restored_id
        
        #get gmail_ids from db
        db_gmail_ids_info = gstorer.get_all_chats_gmail_ids()
        
        LOG.critical("Total number of chats to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_CHAT_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all chats id left to restore. Still %s chats to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored = 0 #to count nb of emails restored
        timer = gmvault_utils.Timer() # needed for enhancing the user information
        timer.start()
        
        for gm_id in db_gmail_ids_info:
            
            LOG.critical("Restore chat with id %s." % (gm_id))
            
            email_meta, email_data = gstorer.unbury_email(gm_id)
            
            LOG.debug("Unburied chat with id %s." % (gm_id))
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in existing_labels]
            
            #create the non existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for chat with id %s." % (gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
            
            try:
                #restore email
                self.src.push_email(email_data, \
                                    email_meta[gstorer.FLAGS_K] , \
                                    email_meta[gstorer.INT_DATE_K], \
                                    labels)
                
                LOG.debug("Pushed chat with id %s." % (gm_id))
                
                nb_emails_restored += 1
                
                #indicate every 10 messages the number of messages left to process
                left_emails = (total_nb_emails_to_restore - nb_emails_restored)
                
                if (nb_emails_restored % 50) == 0 and (left_emails > 0): 
                    elapsed = timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d chats in %s. %d left to be restored (time estimate %s).==\n" % \
                                 (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                                  left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_restored % 10) == 0:
                    self.save_lastid(self.OP_CHAT_RESTORE, gm_id)
                    
            except imaplib.IMAP4.abort, abort:
                
                # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                if str(abort).find("=> Gmvault ssl socket error: EOF") >= 0:
                    LOG.critical("Quarantine email with gm id %s from %s. "\
                                 "GMAIL IMAP cannot restore it: err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(abort)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise abort
        
            except imaplib.IMAP4.error, err:
                
                LOG.error("Catched IMAP Error %s" % (str(err)))
                LOG.exception(err)
                
                #When the email cannot be read from Database because it was empty when returned by gmail imap
                #quarantine it.
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(err)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise err
            except imap_utils.PushEmailError, p_err:
                LOG.error("Catch the following exception %s" % (str(p_err)))
                LOG.exception(p_err)
                
                if p_err.quarantined():
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(p_err)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise p_err          
            except Exception, err:
                LOG.error("Catch the following exception %s" % (str(err)))
                LOG.exception(err)
                raise err
            
            
        return self.error_report
        
        
    def restore_emails(self, pivot_dir = None, extra_labels = [], restart = False):
        """
           restore emails in a gmail account
        """
        LOG.critical("Restore emails in gmail account %s." % (self.login) ) 
        
        #crack email database
        gstorer = GmailStorer(self.db_root_dir, self.use_encryption)
        
        LOG.critical("Read email info from %s gmvault-db." % (self.db_root_dir))
        
        #get gmail_ids from db
        db_gmail_ids_info = gstorer.get_all_existing_gmail_ids(pivot_dir)
        
        LOG.critical("Total number of elements to restore %s." % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(self.OP_EMAIL_RESTORE, db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all emails id left to restore. Still %s emails to do.\n" % (total_nb_emails_to_restore) )
        
        existing_labels = set() #set of existing labels to not call create_gmail_labels all the time
        nb_emails_restored = 0 #to count nb of emails restored
        
        timer = gmvault_utils.Timer() # local timer for restore emails
        timer.start()
        
        for gm_id in db_gmail_ids_info:
            
            LOG.critical("Restore email with id %s." % (gm_id))
            
            email_meta, email_data = gstorer.unbury_email(gm_id)
            
            LOG.debug("Unburied email with id %s." % (gm_id))
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in existing_labels]
            
            #create the non existing labels
            if len(labels_to_create) > 0:
                LOG.debug("Labels creation tentative for email with id %s." % (gm_id))
                existing_labels = self.src.create_gmail_labels(labels_to_create, existing_labels)
            
            try:
                #restore email
                self.src.push_email(email_data, \
                                    email_meta[gstorer.FLAGS_K] , \
                                    email_meta[gstorer.INT_DATE_K], \
                                    labels)
                
                LOG.debug("Pushed email with id %s." % (gm_id))
                
                nb_emails_restored += 1
                
                #indicate every 10 messages the number of messages left to process
                left_emails = (total_nb_emails_to_restore - nb_emails_restored)
                
                if (nb_emails_restored % 50) == 0 and (left_emails > 0): 
                    elapsed = timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d emails in %s. %d left to be restored "\
                                 "(time estimate %s).==\n" % \
                                 (nb_emails_restored, timer.seconds_to_human_time(elapsed), \
                                  left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_restored % 10) == 0:
                    self.save_lastid(self.OP_EMAIL_RESTORE, gm_id)
                    
            except imaplib.IMAP4.abort, abort:
                
                # if this is a Gmvault SSL Socket error quarantine the email and continue the restore
                if str(abort).find("=> Gmvault ssl socket error: EOF") >= 0:
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(abort)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id)
                    LOG.critical("Disconnecting and reconnecting to restart cleanly.")
                    self.src.reconnect() #reconnect
                else:
                    raise abort
        
            except imaplib.IMAP4.error, err:
                
                LOG.error("Catched IMAP Error %s" % (str(err)))
                LOG.exception(err)
                
                #When the email cannot be read from Database because it was empty when returned by gmail imap
                #quarantine it.
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(err)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise err
            except imap_utils.PushEmailError, p_err:
                LOG.error("Catch the following exception %s" % (str(p_err)))
                LOG.exception(p_err)
                
                if p_err.quarantined():
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it:"\
                                 " err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(p_err)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise p_err          
            except Exception, err:
                LOG.error("Catch the following exception %s" % (str(err)))
                LOG.exception(err)
                raise err
            
            
        return self.error_report
            
            
        
    

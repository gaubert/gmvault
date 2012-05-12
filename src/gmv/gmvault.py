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
            
class GmailStorer(object):
    '''
       Store emails on disk
    ''' 
    DATA_FNAME     = "%s/%s.eml"
    METADATA_FNAME = "%s/%s.meta"
    
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
    INFO_AREA                  = '.info'  # contains metadata concerning the database
    ENCRYPTION_KEY_FILENAME    = '.storage_key.sec'
    EMAIL_OWNER                = '.email_account.info'
        
    
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
        
        #make dirs
        if not os.path.exists(self._db_dir):
            LOG.critical("No Storage DB in %s. Create it.\n" % (a_storage_dir))
        
        gmvault_utils.makedirs(self._db_dir)
        gmvault_utils.makedirs(self._quarantine_dir)
        gmvault_utils.makedirs(self._info_dir)
        
        self.fsystem_info_cache = {}
        
        self._encrypt_data   = encrypt_data
        self._encryption_key = None
        self._cipher         = None
        
    
    def store_db_owner(self, email_owner):
        """
           Store the email owner in .info dir. This is used to avoid synchronizing multiple email accounts in gmvault-db.
           Always wipe out completly the file
        """
        fd = open('%s/%s' % (self._info_dir, self.EMAIL_OWNER), "w+")
        fd.write(email_owner)
        fd.close() 
        
    
    def get_db_owner(self):
        """
           Get the email owner for the gmvault-db. Because except in particular cases, the db will be only linked to one meail.
        """
        fname = '%s/%s' % (self._info_dir, self.EMAIL_OWNER)
        if os.path.exists(fname):    
            return open(fname).read()
        
        return None
           
    
            
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
         
    def get_all_existing_gmail_ids(self, pivot_dir = None):
        """
           get all existing gmail_ids from the database within the passed month 
           and all posterior months
        """
        gmail_ids = collections_utils.OrderedDict() #orderedDict compatible for version 2.5
        
        if pivot_dir == None:
            the_iter = gmvault_utils.dirwalk(self._db_dir, "*.meta")
        else:
            
            # get all yy-mm dirs to list
            dirs = gmvault_utils.get_all_directories_posterior_to(pivot_dir, gmvault_utils.get_all_dirs_under(self._db_dir))
            
            #create all iterators and chain them to keep the same interface
            iter_dirs = [gmvault_utils.dirwalk('%s/%s' % (self._db_dir, the_dir), "*.meta") for the_dir in dirs]
            
            the_iter = itertools.chain.from_iterable(iter_dirs)
        
        #get all ids
        for filepath in the_iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)
            
        return gmail_ids
    
    def bury_metadata(self, email_info, local_dir = None):
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
        subject, msgid = self.parse_header_fields(email_info[imap_utils.GIMAPFetcher.IMAP_HEADER_FIELDS])
        
        # need to convert labels that are number as string
        # come from imap_lib when label is a number
        labels = [ str(elem) for elem in  email_info[imap_utils.GIMAPFetcher.GMAIL_LABELS] ]
        
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
    
        
    def bury_email(self, email_info, local_dir = None, compress = False):
        """
           store all email info in 2 files (.meta and .eml files)
           Arguments:
             email_info: info
             local_dir : intermdiary dir (month dir)
             compress  : If compress is True, use gzip compression
        """
        
        if local_dir:
            the_dir = '%s/%s' % (self._db_dir, local_dir)
            gmvault_utils.makedirs(the_dir)
        else:
            the_dir = self._db_dir
        
        
        meta_path = self.METADATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID])
        data_path = self.DATA_FNAME % (the_dir, email_info[imap_utils.GIMAPFetcher.GMAIL_ID])
        
        # if the data has to be encrypted
        if self._encrypt_data:
            data_path = '%s.crypt' % (data_path)
        
        if compress:
            data_path = '%s.gz' % (data_path)
            data_desc = gzip.open(data_path, 'wb')
        else:
            data_desc = open(data_path, 'wb')
            
        meta_desc = open(meta_path, 'w')
        
        if self._encrypt_data:
            # need to be done for every encryption
            cipher = self.get_encryption_cipher()
            cipher.initCTR()
            data_desc.write(cipher.encryptCTR(email_info[imap_utils.GIMAPFetcher.EMAIL_BODY]))
        else:
            data_desc.write(email_info[imap_utils.GIMAPFetcher.EMAIL_BODY])
            
        # parse header fields to extract subject and msgid
        subject, msgid = self.parse_header_fields(email_info[imap_utils.GIMAPFetcher.IMAP_HEADER_FIELDS])
        
        # need to convert labels that are number as string
        # come from imap_lib when label is a number
        labels = [ str(elem) for elem in  email_info[imap_utils.GIMAPFetcher.GMAIL_LABELS] ]
        
        
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
        
        # force convertion of labels as string because imap_lib or Gmail Imap
        # returns a num when the label is a number (ie. '00000')
        metadata[self.LABELS_K] = [ str(elem) for elem in  metadata[self.LABELS_K] ]
        
        return metadata
    
    def delete_emails(self, emails_info):
        """
           Delete all emails and metadata with ids
        """
        for (a_id, date_dir) in emails_info:
            
            the_dir = '%s/%s' % (self._db_dir, date_dir)
            
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
    NB_GRP_OF_ITEMS  = 100
    RESTORE_PROGRESS = 'last_id.restore'
    SYNC_PROGRESS     = 'last_id.sync'
    
    OP_RESTORE = "RESTORE"
    OP_SYNC    = "SYNC"
    
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
        
        # enable compression if possible
        #self.src.enable_compression() 
        
        self.use_encryption = use_encryption
        
        #to report gmail imap problems
        self.error_report = { 'empty' : [] ,
                              'cannot_be_fetched'  : [],
                              'emails_in_quarantine' : [],
                              'reconnections' : 0}
        
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
        the_str = "\n================================================================\nNumber of reconnections: %d.\nNumber of emails quarantined: %d.\n" \
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
    def _metadata_needs_update(cls, curr_metadata, new_metadata):
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
        for label in curr_metadata['labels']:
            if label not in prev_labels:
                return True
            else:
                prev_labels.remove(label)
        
        if len(prev_labels) > 0:
            return True
        
        return False
    
    
    def _check_email_db_ownership(self, gstorer, ownership_control):
        """
           Check email database ownership.
        """
        #check that the gmvault-db is not associated with another user
        db_owner = gstorer.get_db_owner()
        if ownership_control:
            if db_owner and (db_owner != self.login): #db owner should not be different unless bypass activated
                raise Exception("The email database %s is already associated with %s. Use option (-m, --multiple-db-owner) if you want to link it with %s" \
                                % (self.db_root_dir, db_owner, self.login))
        else:
            if db_owner:
                LOG.critical("The email database %s is hosting email from %s. It will now also store emails from %s" \
                             % (self.db_root_dir, db_owner, self.login))
            else:
                LOG.critical("The email database %s can host emails from multiple email accounts." % (self.db_root_dir))
    
    def _create_update_sync(self, imap_ids, compress, ownership_control = True ):
        """
           First part of the double pass strategy: 
           create and update emails in db
        """
        gstorer =  GmailStorer(self.db_root_dir, self.use_encryption)
        
        #check ownership 
        self._check_email_db_ownership(gstorer, ownership_control)
            
        #save db_owner for next time
        gstorer.store_db_owner(self.login)
        
        total_nb_emails_to_process = len(imap_ids) # total number of emails to get
        
        LOG.critical("%d emails to be fetched." % (total_nb_emails_to_process))
        
        nb_emails_processed = 0
        timer = gmvault_utils.Timer() # needed for enhancing the user information
        timer.start()
        
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
                    curr_metadata = GMVaulter.check_email_on_disk( gstorer , \
                                                                   new_data[the_id][imap_utils.GIMAPFetcher.GMAIL_ID], \
                                                                   the_dir)
                    
                    #if on disk check that the data is not different
                    if curr_metadata:
                        
                        LOG.debug("metadata for %s already exists. Check if different." % (gid))
                        
                        if self._metadata_needs_update(curr_metadata, new_data[the_id]):
                            #restore everything at the moment
                            gid  = gstorer.bury_metadata(new_data[the_id], local_dir = the_dir)
                            
                            LOG.debug("update email with imap id %s and gmail id %s." % (the_id, gid))
                            
                            #update local index id gid => index per directory to be thought out
                    else:  
                        
                        #get the data
                        email_data = self.src.fetch(the_id, imap_utils.GIMAPFetcher.GET_DATA_ONLY )
                        
                        new_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY] = email_data[the_id][imap_utils.GIMAPFetcher.EMAIL_BODY]
                        
                        # store data on disk within year month dir 
                        gid  = gstorer.bury_email(new_data[the_id], local_dir = the_dir, compress = compress)
                        
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
                    elapsed = timer.elapsed() #elapsed time in seconds
                    LOG.critical("\n== Processed %d emails in %s. %d left to be stored (time estimate %s).==\n" % \
                                 (nb_emails_processed,  timer.seconds_to_human_time(elapsed), left_emails, timer.estimate_time_left(nb_emails_processed, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_processed % 20) == 0:
                    if gid:
                        self.save_lastid(self.OP_SYNC, gid)
                
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
                    raise Exception("Error")
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
    
    def _delete_sync(self, imap_ids, db_cleaning):
        """
           Delete emails from the database if necessary
           imap_ids      : all remote imap_ids to check
           delete_dry_run: True to simulate everything but the deletion
        """ 
        if db_cleaning:
            gstorer = GmailStorer(self.db_root_dir)
            
            LOG.critical("Check if emails need to be disk cleaned.")
            
            #get gmail_ids from db
            db_gmail_ids_info = gstorer.get_all_existing_gmail_ids()
            
            LOG.critical("got all existing ids from disk nb of ids to check: %s" % (len(db_gmail_ids_info)) )
            
            #create a set of keys
            db_gmail_ids = set(db_gmail_ids_info.keys())
            
            # optimize nb of items
            nb_items = self.NB_GRP_OF_ITEMS if len(db_gmail_ids) >= self.NB_GRP_OF_ITEMS else len(db_gmail_ids)
            
            #calculate the list elements to delete
            #query nb_items items in one query to minimise number of imap queries
            for group_imap_id in itertools.izip_longest(fillvalue=None, *[iter(imap_ids)]*nb_items):
                
                # if None in list remove it
                if None in group_imap_id: 
                    group_imap_id = [ im_id for im_id in group_imap_id if im_id != None ]
                
                data = self.src.fetch(group_imap_id, imap_utils.GIMAPFetcher.GET_GMAIL_ID)
                
                imap_gmail_ids = set()
                
                for key in data:
                    imap_gmail_ids.add(data[key][imap_utils.GIMAPFetcher.GMAIL_ID])
                
                db_gmail_ids -= imap_gmail_ids
                
                #quit loop if db set is already empty
                if len(db_gmail_ids) == 0:
                    break
    
            LOG.critical("Will delete %s email(s) from disk db" % (len(db_gmail_ids)) )
            for gm_id in db_gmail_ids:
                LOG.critical("gm_id %s not in imap. Delete it" % (gm_id))
                gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])])
        else:
            LOG.debug("db_cleaning is off so ignore removing deleted emails from disk.")
        
    def get_gmails_ids_left_to_sync(self, imap_ids):
        """
           Get the ids that still needs to be sync
           Return a list of ids
        """
        
        filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, self.SYNC_PROGRESS)
        
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
        except Exception, _: #ignore any exception and try to get all ids in case of problems.
            #element not in keys return current set of keys
            LOG.critical("Error: Cannot restore from last restore gmail id. It is not in Gmail. Sync the complete list of gmail ids requested from Gmail.")
        
        return new_gmail_ids
    
    def sync(self, imap_req = imap_utils.GIMAPFetcher.IMAP_ALL, compress_on_disk = True, db_cleaning = False, ownership_checking = True, restart = False):
        """
           sync mode 
        """
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # check if there is a restart
        if restart:
            LOG.critical("Restart mode activated. Need to find information in Gmail, be patient.")
            imap_ids = self.get_gmails_ids_left_to_sync(imap_ids)
        
        if not compress_on_disk:
            LOG.critical("Disable compression when storing emails.")
        
        
        # create new emails in db and update existing emails
        self._create_update_sync(imap_ids, compress = compress_on_disk, ownership_control = ownership_checking)
        
        #delete supress emails from DB since last sync
        self._delete_sync(imap_ids, db_cleaning)
        
        return self.error_report
    
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
        
        
        if op_type == self.OP_RESTORE:
            filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, self.RESTORE_PROGRESS)
        elif op_type == self.OP_SYNC:
            filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, self.SYNC_PROGRESS)
        else:
            raise Exception("Bad Operation in save_restore_last_id. This should not happen, send the error to the software developers.")
        
        
        fd = open(filepath, 'w')
        
        json.dump({
                    'last_id' : gm_id  
                  }, fd)
        
        fd.close()
        
    def get_gmails_ids_left_to_restore(self, db_gmail_ids_info):
        """
           Get the ids that still needs to be restored
           Return a dict key = gm_id, val = directory
        """
        
        filepath = '%s/%s_%s' % (gmvault_utils.get_home_dir_path(), self.login, self.RESTORE_PROGRESS)
        
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
           
    def restore(self, pivot_dir = None, extra_labels = [], restart = False):
        """
           Test method to restore emails in gmail 
        """
        LOG.critical("Restore emails in gmail account %s." % (self.login) ) 
        
        #crack email database
        gstorer = GmailStorer(self.db_root_dir, self.use_encryption)
        
        LOG.critical("Read email info from %s gmvault-db." % (self.db_root_dir))
        
        #for the restore (save last_restored_id in .gmvault/last_restored_id
        
        #get gmail_ids from db
        db_gmail_ids_info = gstorer.get_all_existing_gmail_ids(pivot_dir)
        
        LOG.critical("Total number of elements to restore %s" % (len(db_gmail_ids_info.keys())))
        
        if restart:
            db_gmail_ids_info = self.get_gmails_ids_left_to_restore(db_gmail_ids_info)
        
        total_nb_emails_to_restore = len(db_gmail_ids_info)
        LOG.critical("Got all emails id left to restore. Still %s emails to do.\n" % (total_nb_emails_to_restore) )
        
        seen_labels = set() #set of seen labels to not call create_gmail_labels all the time
        nb_emails_restored= 0 #to count nb of emails restored
        timer = gmvault_utils.Timer() # needed for enhancing the user information
        timer.start()
        
        for gm_id in db_gmail_ids_info:
            
            LOG.critical("Restore email with id %s." % (gm_id))
            
            email_meta, email_data = gstorer.unbury_email(gm_id)
            
            LOG.debug("Unburied email with id %s." % (gm_id))
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in seen_labels]
            
            #create the non existing labels
            self.src.create_gmail_labels(labels_to_create)
            
            LOG.debug("Created labels %s for email with id %s." % (labels_to_create, gm_id))
            
            #update seen labels
            seen_labels.update(set(labels_to_create))
            
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
                    LOG.critical("\n== Processed %d emails in %s. %d left to be restored (time estimate %s).==\n" % \
                                 (nb_emails_restored, timer.seconds_to_human_time(elapsed), left_emails, timer.estimate_time_left(nb_emails_restored, elapsed, left_emails)))
                
                # save id every 20 restored emails
                if (nb_emails_restored % 20) == 0:
                    self.save_lastid(self.OP_RESTORE, gm_id)
        
            except imaplib.IMAP4.error, err:
                
                LOG.error("Catched IMAP Error %s" % (str(err)))
                LOG.exception(err)
                
                #When the email cannot be read from Database because it was empty when returned by gmail imap
                #quarantine it.
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it: err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(err)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise err
            except imap_utils.PushEmailError, p_err:
                LOG.error("Catch the following exception %s" % (str(p_err)))
                LOG.exception(p_err)
                
                if p_err.quarantined():
                    LOG.critical("Quarantine email with gm id %s from %s. GMAIL IMAP cannot restore it: err={%s}" % (gm_id, db_gmail_ids_info[gm_id], str(p_err)))
                    gstorer.quarantine_email(gm_id)
                    self.error_report['emails_in_quarantine'].append(gm_id) 
                else:
                    raise p_err          
            except Exception, err:
                LOG.error("Catch the following exception %s" % (str(err)))
                LOG.exception(err)
                raise err
            
            
        return self.error_report
            
            
        
    

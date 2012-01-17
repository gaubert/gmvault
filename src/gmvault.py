'''
Created on Nov 16, 2011

@author: guillaume.aubert@gmail.com
'''
import json
import gzip
import re
import datetime
import os
import itertools
import imaplib
import functools
import fnmatch
import shutil

import blowfish
import log_utils
import gmvault_utils as gmvault_utils
import mod_imap as mimap



LOG = log_utils.LoggerFactory.get_logger('gmvault')




#retry decorator with nb of tries
def retry(a_nb_tries = 3):
    def inner_retry(fn):
        def wrapper(*args, **kwargs):
            nb_tries = 0
            while True:
                try:
                    
                    return fn(*args, **kwargs)
                    
                except imaplib.IMAP4.error, err:
                    
                    LOG.debug("error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    LOG.critical("Cannot reach the gmail server. Wait 3 seconds and retrying")
                    
                    # add 3 sec of wait
                    
                    # go in retry mode if less than 3 tries
                    if nb_tries < a_nb_tries and err.message.startswith('fetch failed:') :
                        nb_tries += 1
                    else:
                        #cascade error
                        raise err
            
        return functools.wraps(fn)(wrapper)
    return inner_retry

class GIMAPFetcher(object): #pylint:disable-msg=R0902
    '''
    IMAP Class reading the information
    '''
    GMAIL_EXTENSION   = 'X-GM-EXT-1'  # GMAIL capability
    GMAIL_ALL         = '[Gmail]/All Mail' #GMAIL All Mail mailbox
    GOOGLE_MAIL_ALL   = '[Google Mail]/All Mail' #Google Mail All Mail mailbox for Germany
    GMAIL_ID          = 'X-GM-MSGID' #GMAIL ID attribute
    GMAIL_THREAD_ID   = 'X-GM-THRID'
    GMAIL_LABELS      = 'X-GM-LABELS'
    
    IMAP_INTERNALDATE = 'INTERNALDATE'
    IMAP_FLAGS        = 'FLAGS'
    IMAP_ALL          = 'ALL'
    
    EMAIL_BODY        = 'BODY[]'
    
    GMAIL_SPECIAL_DIRS = ['\\Inbox', '\\Starred', '\\Sent', '\\Draft', '\\Important']
    
    #to be removed
    EMAIL_BODY_OLD        = 'RFC822' #set msg as seen
    IMAP_BODY_PEEK     = 'BODY.PEEK[]' #get body without setting msg as seen
    
    IMAP_HEADER_FIELDS = 'BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT)]'
    
    #GET_IM_UID_RE
    APPENDUID         = '^[APPENDUID [0-9]* ([0-9]*)] \(Success\)$'
    
    APPENDUID_RE      = re.compile(APPENDUID)
    
    GET_ALL_INFO      = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, IMAP_BODY_PEEK, IMAP_FLAGS, IMAP_HEADER_FIELDS]

    GET_ALL_BUT_DATA  = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, IMAP_FLAGS, IMAP_BODY_PEEK, IMAP_HEADER_FIELDS]
    
    GET_DATA_ONLY     = [GMAIL_ID, IMAP_BODY_PEEK]
 
    GET_GMAIL_ID      = [ GMAIL_ID ]
    
    GET_GMAIL_ID_DATE = [ GMAIL_ID,  IMAP_INTERNALDATE]

    def __init__(self, host, port, login, password, readonly_folder = True): #pylint:disable-msg=R0913
        '''
            Constructor
        '''
        self.host             = host
        self.port             = port
        self.login            = login
        self.password         = password
        self.ssl              = True
        self.use_uid          = True
        self.readonly_folder  = readonly_folder
        self._all_mail_folder = None
        self.server           = None
    
    def connect(self, go_to_all_folder = True):
        """
           connect to the IMAP server
        """
        self.server = mimap.MonkeyIMAPClient(self.host, port = self.port, use_uid= self.use_uid, ssl= self.ssl)
        
        self.server.login(self.login, self.password)
        
        # check gmailness
        self.check_gmailness()
        
        self._all_mail_folder = None
        
        #find the all mail folder
        self.find_all_mail_folder()
        
        # set to GMAIL_ALL dir by default and in readonly
        if go_to_all_folder:
            self.server.select_folder(self._all_mail_folder, readonly = self.readonly_folder)
    
    def enable_compression(self):
        """
           Try to enable the compression
        """
        self.server.enable_compression()
    
    def find_all_mail_folder(self):
        """
           depending on your account the all mail folder can be named 
           [GMAIL]/ALL Mail or [GoogleMail]/All Mail.
           Find and set the right one
        """
        
        folders = self.server.list_folders()
        the_dir = None
        for (_, _, the_dir) in folders:
            if the_dir == GIMAPFetcher.GMAIL_ALL:
                self._all_mail_folder = GIMAPFetcher.GMAIL_ALL
                break
            elif the_dir == GIMAPFetcher.GOOGLE_MAIL_ALL:
                self._all_mail_folder = GIMAPFetcher.GOOGLE_MAIL_ALL
                break
        
        if the_dir == None:
            #Error
            raise Exception("Cannot find global dir %s or %s. Are you sure it is a GMail account" % \
                            (GIMAPFetcher.GMAIL_ALL, GIMAPFetcher.GOOGLE_MAIL_ALL))
    
    def get_all_folders(self): 
        """
           Return all folders mainly for debuging purposes
        """
        return self.server.list_folders()
        
    def get_capabilities(self):
        """
           return the server capabilities
        """
        if not self.server:
            raise Exception("GIMAPFetcher not connect to the GMAIL server")
        
        return self.server.capabilities()
    
    def check_gmailness(self):
        """
           Check that the server is a gmail server
        """
        if not GIMAPFetcher.GMAIL_EXTENSION in self.get_capabilities():
            raise Exception("GIMAPFetcher is not connect to a IMAP GMAIL server. Please check host (%s) and port (%s)" % (self.host, self.port))
        
        return True
    
    def search(self, a_criteria):
        """
           Return all found ids corresponding to the search
        """
        return self.server.search(a_criteria)
    
    @retry(3) # add a retry 3 times
    def fetch(self, a_ids, a_attributes):
        """
           Return all attributes associated to each message
        """
        return self.server.fetch(a_ids, a_attributes)
                
    
    @classmethod
    def _build_labels_str(cls, a_labels):
        """
           Create IMAP label string from list of given labels
           a_labels: List of labels
        """
        # add GMAIL LABELS
        labels_str = None
        if a_labels and len(a_labels) > 0:
            labels_str = '('
            for label in a_labels:
                if label.find(' ') >=0 :
                    labels_str += '\"%s\" ' % (label)
                else:
                    labels_str += '%s ' % (label)
            
            labels_str = '%s%s' % (labels_str[:-1],')')
        
        return labels_str
    
    @classmethod
    def _get_dir_from_labels(cls, label):
        """
           Get the dirs to create from the labels
           
           label: label name with / in it
        """
        
        dirs = []
        
        i = 0
        for lab in label.split('/'):
            
            if i == 0:
                dirs.append(lab)
            else:
                dirs.append('%s/%s' % (dirs[i-1], lab))
            
            i += 1
        
        return dirs
    
    def create_gmail_labels(self, labels):
        """
           Create folders and subfolders on Gmail in order
           to recreate the label hierarchy before to upload emails
           Note that adding labels with +X-GM-LABELS create only nested labels
           but not nested ones. This is why this trick must be used to 
           recreate the label hierarchy
           
           labels: list of labels to create
           
        """
        for lab in labels:
           
            #get existing directories (or label parts)
            folders = [ directory for (_, _, directory) in self.server.list_folders() ]
            
            labs = self._get_dir_from_labels(lab)
            
            for directory in labs:
                if (directory not in folders) and (directory not in self.GMAIL_SPECIAL_DIRS):
                    if self.server.create_folder(directory) != 'Success':
                        raise Exception("Cannot create label %s: the directory %s cannot be created." % (lab, directory))
                    
    
    def delete_gmail_labels(self, labels):
        """
           Delete passed labels
        """
        for label in labels:
            
            labs = self._get_dir_from_labels(label)
            
            for directory in reversed(labs):
                if self.server.folder_exists(directory): #call server exists each time
                    self.server.delete_folder(directory)
                    
            
    def push_email(self, a_body, a_flags, a_internal_time, a_labels):
        """
           Push a complete email body 
        """
        #protection against myself
        if self.login == 'guillaume.aubert@gmail.com':
            raise Exception("Cannot push to this account")
        
        res = self.server.append(self._all_mail_folder, a_body, a_flags, a_internal_time)
        
        # check res otherwise Exception
        if '(Success)' not in res:
            raise Exception("GIMAPFetcher cannot restore email in %s account." %(self.login))
        
        result_uid = int(GIMAPFetcher.APPENDUID_RE.search(res).group(1))
        
        labels_str = self._build_labels_str(a_labels)
        
        if labels_str:  
            #has labels so update email  
            ret_code, data = self.server._imap.uid('STORE', result_uid, '+X-GM-LABELS', labels_str)
            #response = self.server._store(result_uid, '+X-GM-LABELS', labels_str)
            #print(response)
        
            # check if it is ok otherwise exception
            if ret_code != 'OK':
                raise Exception("Cannot add Labels %s to email with uid %d. Error:%s" % (labels_str, result_uid, data))
        
        return result_uid
    
    def fetch_with_gmid(self, a_gm_id):
        """
           fetch an email with it gmailID
        """
        pass
            
class GmailStorer(object):
    '''
       Store emails
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
    
    HFIELDS_PATTERN = "Message-ID:\s+<(?P<msgid>.*)>\s+Subject:\s+(?P<subject>.*)\s*"
    HFIELDS_RE      = re.compile(HFIELDS_PATTERN)
    
    DB_AREA         = 'db'
    QUARANTINE_AREA = 'quarantine'
        
    
    def __init__(self, a_storage_dir, a_encrypt_key = None):
        """
           Store on disks
           args:
              a_storage_dir: Storage directory
              a_encrypt_key: Encryption key. If there then encrypt
        """
        self._top_dir = a_storage_dir
        
        self._db_dir          = '%s/%s' % (a_storage_dir, GmailStorer.DB_AREA)
        self._quarantine_dir  = '%s/%s' % (a_storage_dir, GmailStorer.QUARANTINE_AREA)
        
        #make dirs
        gmvault_utils.makedirs(self._db_dir)
        gmvault_utils.makedirs(self._quarantine_dir)
        
        if a_encrypt_key:
            #create blowfish cipher
            self._cipher = blowfish.Blowfish(a_encrypt_key)
            #init cipher
            self._cipher.initCTR()
        else:
            self._cipher = None
    
    def parse_header_fields(self, header_fields):
        """
           extract subject and message ids from the given header fields 
        """
        
        matched = GmailStorer.HFIELDS_RE.match(header_fields)
        if matched:
            return (matched.group('subject'), matched.group('msgid'))
        else:
            return None, None
    
    def get_all_existing_gmail_ids(self):
        """
           get all existing gmail_ids from the database
        """
        gmail_ids = {}
        the_iter = gmvault_utils.dirwalk(self._db_dir, "*.meta")
        
        for filepath in the_iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)
    
        return gmail_ids
        
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
        
        
        meta_path = self.METADATA_FNAME % (the_dir, email_info[GIMAPFetcher.GMAIL_ID])
        data_path = self.DATA_FNAME % (the_dir, email_info[GIMAPFetcher.GMAIL_ID])
        
        # manage filename for the cipher
        if self._cipher:
            data_path = '%s.crypt' % (data_path)
        
        if compress:
            data_path = '%s.gz' % (data_path)
            data_desc = gzip.open(data_path, 'wb')
        else:
            data_desc = open(data_path, 'wb')
            
        meta_desc = open(meta_path, 'w')
        
        if self._cipher:
            data_desc.write(self._cipher.encryptCTR(email_info[GIMAPFetcher.IMAP_HEADER_FIELDS]))
        else:
            data_desc.write(email_info[GIMAPFetcher.EMAIL_BODY])
            
        # parse header fields to extract subject and msgid
        subject, msgid = self.parse_header_fields(email_info[GIMAPFetcher.IMAP_HEADER_FIELDS])
        
        #create json structure for metadata
        meta_obj = { 
                     self.ID_K         : email_info[GIMAPFetcher.GMAIL_ID],
                     self.LABELS_K     : email_info[GIMAPFetcher.GMAIL_LABELS],
                     self.FLAGS_K      : email_info[GIMAPFetcher.IMAP_FLAGS],
                     self.THREAD_IDS_K : email_info[GIMAPFetcher.GMAIL_THREAD_ID],
                     self.INT_DATE_K   : gmvault_utils.datetime2e(email_info[GIMAPFetcher.IMAP_INTERNALDATE]),
                     self.FLAGS_K      : email_info[GIMAPFetcher.IMAP_FLAGS],
                     self.SUBJECT_K    : subject,
                     self.MSGID_K      : msgid
                   }
        
        json.dump(meta_obj, meta_desc, ensure_ascii = False)
        
        meta_desc.flush()
        meta_desc.close()
        
        data_desc.flush()
        data_desc.close()
        
        return email_info[GIMAPFetcher.GMAIL_ID]
    
    def _get_directory_from_id(self, a_id):
        """
           Return the directory path if id located.
           Return None if not found
        """
        filename = '%s.meta' % (a_id)
        for dirs, subdirs, files in os.walk(os.path.abspath(self._db_dir)):
            for filename in fnmatch.filter(files, filename):
                return dirs
        
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
           Quarantine the 
        """
        #get the dir where the email is stored
        the_dir = self._get_directory_from_id(a_id)
        
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
    
    def unbury_email(self, a_id):
        """
           Restore email info from info stored on disk
           Return a tuple (meta, data)
        """
        the_dir = self._get_directory_from_id(a_id)
        
        data_fd = self._get_data_file_from_id(the_dir, a_id)
        
        if self._cipher:
            data = self._cipher.decryptCTR(data_fd.read())
        else:
            data = data_fd.read()
        
        return (self.unbury_metadata(a_id, the_dir), data)
    
    def unbury_metadata(self, a_id, a_id_dir = None):
        """
           Get metadata info from DB
        """
        if not a_id_dir:
            a_id_dir = self._get_directory_from_id(a_id)
        
        meta_fd = self._get_metadata_file_from_id(a_id_dir, a_id)
        
        metadata = json.load(meta_fd)
        
        metadata[self.INT_DATE_K] =  gmvault_utils.e2datetime(metadata[self.INT_DATE_K])
        
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
            elif os.path.exists(crypt_comp_data_p):
                os.remove(comp_data_p)   
            elif os.path.exists(metadata_p):
                os.remove(metadata_p)
   
class GMVaulter(object):
    """
       Main object operating over gmail
    """ 
    NB_GRP_OF_ITEMS = 100
    
    def __init__(self, db_root_dir, host, port, login, passwd, encrypt_key = None): #pylint:disable-msg=R0913
        """
           constructor
        """   
        self.db_root_dir = db_root_dir
        
        #create dir if it doesn't exist
        gmvault_utils.makedirs(self.db_root_dir)
            
        # create source and try to connect
        self.src = GIMAPFetcher(host, port, login, passwd)
        
        self.src.connect()
        
        # enable compression if possible
        self.src.enable_compression() 
        
        self.encrypt_key = encrypt_key
        
    def _sync_between(self, begin_date, end_date, storage_dir, compress = True):
        """
           sync between 2 dates
        """
        #for the moment compress = False
        #compress = False
        
        #create storer
        gstorer = GmailStorer(storage_dir, a_encrypt_key = self.encrypt_key)
        
        #search before the next month
        imap_req = 'Before %s' % (gmvault_utils.datetime2imapdate(end_date))
        
        ids = self.src.search(imap_req)
                              
        #loop over all ids, get email store email
        for the_id in ids:
            
            #retrieve email from destination email account
            data      = self.src.fetch(the_id, GIMAPFetcher.GET_ALL_INFO)
            
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
    def check_email_on_disk(cls, a_gstorer, a_id):
        """
           Factory method to create the object if it exists
        """
        try:
            the_dir = a_gstorer._get_directory_from_id(a_id)
            if the_dir:
                return a_gstorer.unbury_metadata(a_id, the_dir) 
        except ValueError, json_error:
            LOG.exception("Cannot read file %s. Try to fetch the data again" % ('%s/%s.meta' % (a_storage_dir, a_id)), json_error )
        
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
    
    def _create_update_sync(self, imap_ids, compress):
        """
           First part of the double pass strategy: 
           create and update emails in db
        """
        ignored_ids = [] # ids that cannot be retrieved on gmail for a buggy reason
        
        gstorer =  GmailStorer(self.db_root_dir, self.encrypt_key)
        
        for the_id in imap_ids:
            
            try:
                LOG.critical("Process imap id %s\n" % ( the_id ))
                
                #get everything once for all
                new_data = self.src.fetch(the_id, GIMAPFetcher.GET_ALL_INFO )
                
                the_dir      = gmvault_utils.get_ym_from_datetime(new_data[the_id][GIMAPFetcher.IMAP_INTERNALDATE])
                
                #pass the dir and the ID
                curr_metadata = GMVaulter.check_email_on_disk( gstorer , \
                                                               new_data[the_id][GIMAPFetcher.GMAIL_ID])
                
                #if on disk check that the data is not different
                if curr_metadata:
                    
                    LOG.critical("metadata for %s already exists. Check if different" % (new_data[the_id][GIMAPFetcher.GMAIL_ID]))
                    
                    if self._metadata_needs_update(curr_metadata, new_data[the_id]):
                        #restore everything at the moment
                        gid  = gstorer.bury_email(new_data[the_id], compress = compress)
                        
                        LOG.critical("update email with imap id %s and gmail id %s\n" % (the_id, gid))
                        
                        #update local index id gid => index per directory to be thought out
                else:
                    
                    # store data on disk within year month dir 
                    gid  = gstorer.bury_email(new_data[the_id], local_dir = the_dir, compress = compress)
                    
                    #update local index id gid => index per directory to be thought out
                    LOG.critical("Create and store email  with imap id %s, gmail id %s\n" % (the_id, gid))   
            
            except imaplib.IMAP4.error, error:
                # check if this is a cannot be fetched error 
                # I do not like to do string guessing within an exception but I do not have any choice here
                
                LOG.exception("Error [%s]" % error.message, error )
                
                if error.message == "fetch failed: 'Some messages could not be FETCHed (Failure)'":
                    try:
                        #try to get the gmail_id
                        curr = self.src.fetch(the_id, GIMAPFetcher.GET_GMAIL_ID) 
                    except Exception, _: #pylint:disable-msg=W0703
                        curr = None
                    
                    if curr:
                        gmail_id = curr[the_id][GIMAPFetcher.GMAIL_ID]
                    else:
                        gmail_id = None
                    
                    #add ignored id
                    ignored_ids.append((the_id, gmail_id))
                else:
                    raise error #rethrow error
        
        
        LOG.critical("list of ignored ids %s" % (ignored_ids))
       
    
    
    def _delete_sync(self, imap_ids, db_cleaning):
        """
           Delete emails from the database if necessary
           imap_ids      : all remote imap_ids to check
           delete_dry_run: True to simulate everything but the deletion
        """ 
        gstorer = GmailStorer(self.db_root_dir)
        
        LOG.critical("get all existing ids from disk")
        
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
            
            data = self.src.fetch(group_imap_id, GIMAPFetcher.GET_GMAIL_ID)
            
            imap_gmail_ids = set()
            
            for key in data:
                imap_gmail_ids.add(data[key][GIMAPFetcher.GMAIL_ID])
            
            db_gmail_ids -= imap_gmail_ids
            
            #quit loop if db set is already empty
            if len(db_gmail_ids) == 0:
                break
            
        LOG.critical("Will delete %s imap from disk db" % (len(db_gmail_ids)) )
        if db_cleaning: #delete if db_cleaning ordered
            for gm_id in db_gmail_ids:
                LOG.critical("gm_id %s not in imap. Delete it" % (gm_id))
                gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])])
        
    def sync(self, imap_req = GIMAPFetcher.IMAP_ALL, compress_on_disk = True, db_cleaning = False):
        """
           sync with db on disk
        """
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # create new emails in db and update existing emails
        self._create_update_sync(imap_ids, compress_on_disk)
        
        #delete supress emails from DB since last sync
        self._delete_sync(imap_ids, db_cleaning)
    
    def remote_sync(self):
        """
           Sync with a remote source (IMAP mirror or cloud storage area)
        """
        #sync remotely 
        
    def sync_with_gmail_acc(self, gm_server, gm_port, gm_login, gm_password, extra_labels = []):
        
        """
           Test method to restore emails in gmail 
        """
        
        # connect to destination email account
        gdestination = GIMAPFetcher(gm_server, gm_port, gm_login, gm_password, readonly_folder = False)
        
        gdestination.connect()
        
        LOG.critical("restore email database in gmail account %s" % (gm_login) ) 
        
        gstorer = GmailStorer(self.db_root_dir, self.encrypt_key)
        
        LOG.critical("get all existing gmail ids from disk")
        
        #get gmail_ids from db
        db_gmail_ids_info = gstorer.get_all_existing_gmail_ids()
        
        LOG.critical("got all existing ids from disk. Will have to restore %s emails" % (len(db_gmail_ids_info)) )
        
        seen_labels = set() #set of seen labels to not call create_gmail_labels all the time
        
        for gm_id, yy_dir in db_gmail_ids_info.iteritems():
            
            LOG.critical("restore email with id %s" % (gm_id))
            
            email_meta, email_data = gstorer.unbury_email(gm_id)
            
            #labels for this email => real_labels U extra_labels
            labels = set(email_meta[gstorer.LABELS_K])
            labels = labels.union(extra_labels)
            
            # get list of labels to create 
            labels_to_create = [ label for label in labels if label not in seen_labels]
            
            #create the non existing labels
            gdestination.create_gmail_labels(labels_to_create)
            
            #update seen labels
            seen_labels.update(set(labels_to_create))
            
            try:
                #restore email
                gdestination.push_email(email_data, \
                                    email_meta[gstorer.FLAGS_K] , \
                                    email_meta[gstorer.INT_DATE_K], \
                                    labels)
            except imaplib.IMAP4.error, err:
                # problem with this email, put it in quarantine
                if str(err) == "APPEND command error: BAD ['Invalid Arguments: Unable to parse message']":
                    LOG.critical("Quarantine email with gm id %s. GMAIL IMAP cannot restore it: err={%s}" % (gm_id, str(err)))
            except Exception, err:
                print("Catch the following exception %s" % (str(err)))
                raise err
            
            # TODO need something to avoid pushing twice the same email 
            #perform a gmail search with wathever is possible or a imap search
            
            
        
        #read disk db (maybe will need requests to restrict by date)     
        # get list of existing ids
        # for each id unbury email info (contains everything)
        # maintain a list of folders and create them if they do not exist (set of labels))
        # push email (maybe will push multiple emails)            
            
            
        
    

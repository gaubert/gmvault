'''
Created on Nov 16, 2011

@author: guillaume.aubert@gmail.com
'''
import json
import zlib
import gzip
import re
import datetime
import time
import os
import itertools

from imapclient import IMAPClient
import gmvault_utils as gmvault_utils

class MonkeyIMAPClient(IMAPClient):
    """
       Need to extend the IMAPClient to do more things such as compression
       Compression inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    
    def __init__(self, host, port=None, use_uid=True, ssl=False):
        """
           constructor
        """
        super(MonkeyIMAPClient, self).__init__(host, port, use_uid, ssl)
        
        self.inflator = None
        self.deflator = None

    def enable_compression(self):
      """ enable compression on the socket (RFC 4978) """
  
      self.deflator = zlib.decompressobj(-15)
      self.inflator = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)

        
        

class GIMAPFetcher(object):
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
    
    #to be removed
    EMAIL_BODY_OLD        = 'RFC822' #set msg as seen
    IMAP_BODY_PEEK    = 'BODY.PEEK[]' #get body without setting msg as seen
    
    
    #GET_IM_UID_RE
    APPENDUID         = '^[APPENDUID [0-9]* ([0-9]*)] \(Success\)$'
    
    APPENDUID_RE      = re.compile(APPENDUID)
    
    GET_ALL_INFO      = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, IMAP_BODY_PEEK, IMAP_FLAGS]

    GET_ALL_BUT_DATA  = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, IMAP_FLAGS]
 
    GET_GMAIL_ID      = [ GMAIL_ID ]
    
    GET_GMAIL_ID_DATE = [ GMAIL_ID,  IMAP_INTERNALDATE]

    def __init__(self, host, port, login, password, readonly_folder = True):
        '''
            Constructor
        '''
        self.host            = host
        self.port            = port
        self.login           = login
        self.password        = password
        self.ssl             = True
        self.use_uid         = True
        self.readonly_folder = readonly_folder
        
        self.server          = None
    
    def connect(self, go_to_all_folder = True):
        """
           connect to the IMAP server
        """
        self.server = MonkeyIMAPClient(self.host, port = self.port, use_uid= self.use_uid, ssl= self.ssl)
        
        self.server.login(self.login, self.password)
        
        self._all_mail_folder = None
        
        #find the all mail folder
        self.find_all_mail_folder()
        
        # set to GMAIL_ALL dir by default and in readonly
        if go_to_all_folder:
            self.server.select_folder(self._all_mail_folder, readonly = self.readonly_folder)
    
    def find_all_mail_folder(self):
        """
           depending on your account the all mail folder can be named 
           [GMAIL]/ALL Mail or [GoogleMail]/All Mail.
           Find and set the right one
        """
        
        folders = self.server.list_folders()
        dir = None
        for (_, _, dir) in folders:
            if dir == GIMAPFetcher.GMAIL_ALL:
                self._all_mail_folder = GIMAPFetcher.GMAIL_ALL
                break
            elif dir == GIMAPFetcher.GOOGLE_MAIL_ALL:
                self._all_mail_folder = GIMAPFetcher.GOOGLE_MAIL_ALL
                break
        
        if dir == None:
            #Error
            raise Exception("Cannot find global dir %s or %s. Are you sure it is a GMail account" % (GIMAPFetcher.GMAIL_ALL, GIMAPFetcher.GOOGLE_MAIL_ALL))
            
        
    
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
    
    def fetch(self, a_ids, a_attributes):
        """
           Return all attributes associated to each message
        """
        return self.server.fetch(a_ids, a_attributes)
    
    def _build_labels_str(self, a_labels):
        """
           Create IMAP label string from list of given labels
           a_labels: List of labels
        """
        # add GMAIL LABELS 
        labels_str = None
        if a_labels and len(a_labels) > 0:
            labels_str = '('
            for label in a_labels:
                labels_str += '%s ' % (label)
            labels_str = '%s%s' % (labels_str[:-1],')')
        
        return labels_str
        
    
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
        
            # check if it is ok otherwise exception
            if ret_code != 'OK':
                raise Exception("Cannot add Labels %s to email with uid %d. Error:%s" % (labels_str, result_uid, data))
        
        return result_uid
            
class GmailStorer(object):
    '''
       Store emails
    ''' 
    ID_FLAG="#ID:"
    THREAD_ID_FLAG="#THRID:"
    LABELS_FLAG="#LABELS:"
    EMAIL_FLAG="#EMAIL:"
    
    DATA_FNAME     = "%s/%s.eml"
    METADATA_FNAME = "%s/%s.meta"
    
    def __init__(self, a_storage_dir):
        """
           Store on disks
        """
        self._top_dir = a_storage_dir
        
        gmvault_utils.makedirs(a_storage_dir)
        
    def store_index(self, index_obj):
        """
           Store the index file that create the IMAP_ID:GM_ID relation
        """
        
        index_path = "%s/index.dx" % (self._top_dir)
        fd = open(index_path, "w")
        
        json.dump(index_obj, fd , ensure_ascii = False)
        
    def load_index(self):
        """ load the index of the current dir """
        
        index_path = "%s/index.dx" % (self._top_dir)
        
        return json.load( open(index_path) )
    
    def get_all_existing_gmail_ids(self):
        """
           get all existing gmail_ids from the database
        """
        gmail_ids = {}
        iter = gmvault_utils.dirwalk(self._top_dir, "*.meta")
        
        for filepath in iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[long(os.path.splitext(fname)[0])] = os.path.basename(directory)
    
        return gmail_ids
            
        
    def bury_email(self, email_info, compress = False):
        """
           store a json structure with all email elements in a file
           If compress is True, use gzip compression
        """
        meta_path = self.METADATA_FNAME % (self._top_dir, email_info[GIMAPFetcher.GMAIL_ID])
        data_path = self.DATA_FNAME % (self._top_dir, email_info[GIMAPFetcher.GMAIL_ID])
        
        if compress:
            data_path = '%s.gz' % (data_path)
            data_desc = gzip.open(data_path, 'wb')
        else:
            data_desc = open(data_path, 'w')
            
        meta_desc = open(meta_path, 'w')
             
        #create json structure
        data_obj= { 'id'            : email_info[GIMAPFetcher.GMAIL_ID],
                    'email'         : email_info[GIMAPFetcher.EMAIL_BODY],
                    'thread_ids'    : email_info[GIMAPFetcher.GMAIL_THREAD_ID],
                    'labels'        : email_info[GIMAPFetcher.GMAIL_LABELS],
                    'internal_date' : gmvault_utils.datetime2e(email_info[GIMAPFetcher.IMAP_INTERNALDATE]),
                    'flags'         : email_info[GIMAPFetcher.IMAP_FLAGS]}
        
        json.dump(data_obj, data_desc, ensure_ascii = False)
        
        meta_obj = { 'id'     : email_info[GIMAPFetcher.GMAIL_ID],
                     'labels' : email_info[GIMAPFetcher.GMAIL_LABELS],
                     'flags'  : email_info[GIMAPFetcher.IMAP_FLAGS]}
        
        json.dump(meta_obj, meta_desc, ensure_ascii = False)
        
        meta_desc.flush()
        meta_desc.flush()
        
        data_desc.flush()
        data_desc.close()
        
        return email_info[GIMAPFetcher.GMAIL_ID]
    
    
    def _get_db_files_from_id(self, id):
        """
           build data and metadata file from the given id
        """
        meta_p = self.METADATA_FNAME % (self._top_dir, id)
        data_p = self.DATA_FNAME % (self._top_dir, id)
        
        # check if it compressed or not
        if os.path.exists('%s.gz' % (data_p)):
            data_fd = gzip.open('%s.gz' % (data_p), 'r')
        else:
            data_fd = open(data_p)
            
        
        return open(meta_p), data_fd
    
    def _get_data_file_from_id(self, id):
        """
           Return data file from the id
        """
        data_p = self.DATA_FNAME % (self._top_dir, id)
        
        # check if it compressed or not
        if os.path.exists('%s.gz' % (data_p)):
            data_fd = gzip.open('%s.gz' % (data_p), 'r')
        else:
            data_fd = open(data_p)
            
        
        return data_fd
    
    def _get_metadata_file_from_id(self, id):
        """
           metadata file
        """
        meta_p = self.METADATA_FNAME % (self._top_dir, id)
        
        return open(meta_p)
        
    
    def unbury_email(self, id):
        """
           Restore email info from info stored on disk
        """
        
        data_fd = self._get_data_file_from_id(id)
        
        res = json.load(data_fd)
        
        res['internal_date'] =  gmvault_utils.e2datetime(res['internal_date'])
        
        return res
    
    def unbury_metadata(self, id):
        """
           Get metadata info from DB
        """
        meta_fd = self._get_metadata_file_from_id(id)
        
        metadata = json.load(meta_fd)
        
        return metadata
    
    def delete_emails(self, emails_info):
        """
           Delete all emails and metadata with ids
        """
        for (id, date_dir) in emails_info:
            
            the_dir = '%s/%s' % (self._top_dir, date_dir)
            
            data_p      = self.DATA_FNAME % (the_dir, id)
            comp_data_p = '%s.gz' % (data_p)
            metadata_p  = self.METADATA_FNAME % (the_dir, id)
            
            #delete files if they exists
            if os.path.exists(data_p):
                os.remove(data_p)
                
            if os.path.exists(comp_data_p):
                os.remove(comp_data_p)
                
            if os.path.exists(metadata_p):
                os.remove(metadata_p)
    
class GMVaultIndexer(object):
    """
       Indexer maintaining the association between 
    """
        
class GMVaulter(object):
    """
       Main object operating over gmail
    """ 
    
    def __init__(self, db_root_dir, host, port, login, passwd):
        """
           constructor
        """   
        self.db_root_dir = db_root_dir
        
        #create dir if it doesn't exist
        gmvault_utils.makedirs(self.db_root_dir)
        
        
        # create source and try to connect
        self.src = GIMAPFetcher(host, port, login, passwd)
        self.src.connect()
        
    def _sync_between(self, begin_date, end_date, storage_dir, compress = True):
        """
           sync between 2 dates
        """
        #for the moment compress = False
        #compress = False
        
        #create storer
        gstorer = GmailStorer(storage_dir)
        
        #search before the next month
        imap_req = 'Before %s' % (gmvault_utils.datetime2imapdate(end_date))
        
        ids = self.src.search(imap_req)
                              
        #loop over all ids, get email store email
        for id in ids:
            
            #retrieve email from destination email account
            data      = self.src.fetch(id, GIMAPFetcher.GET_ALL_INFO)
            
            file_path = gstorer.bury_email(data[id], compress = compress)
            
            print("Stored email %d in %s" %(id, file_path))
        
    def _get_next_date(self, a_current_date, start_month_beginning = False):
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
    def check_email_on_disk(cls, a_storage_dir, a_id):
        """
           Factory method to create the object if it exists
        """
        # look for a_storage_dir/a_id.meta
        if os.path.exists('%s/%s.meta' % (a_storage_dir, a_id)):
            gs = GmailStorer(a_storage_dir)
            metadata = gs.unbury_metadata(a_id) 
            return gs, metadata
        
        return None, None
    
    def _metadata_needs_update(self, curr_metadata, new_metadata):
        """
           Needs update
        """
        if curr_metadata['id'] != new_metadata['X-GM-MSGID']:
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
        for id in imap_ids:
            
            print("Process imap id %s\n" %(id))
            
            #ids[0] should be the oldest so get the date and start from here
            curr = self.src.fetch(id, GIMAPFetcher.GET_ALL_BUT_DATA )
            
            yy_mon = gmvault_utils.get_ym_from_datetime(curr[id][GIMAPFetcher.IMAP_INTERNALDATE])
            
            dir  = '%s/%s' % (self.db_root_dir, \
                              yy_mon)
            
            gstorer, curr_metadata = GMVaulter.check_email_on_disk(dir, curr[id][GIMAPFetcher.GMAIL_ID])
            
            #if on disk check that the data is not different
            if curr_metadata:
                
                print("metadata for %s already exists. Check if different" % (curr[id][GIMAPFetcher.GMAIL_ID]))
                
                new_metadata = self.src.fetch(id, GIMAPFetcher.GET_ALL_BUT_DATA)
                
                if self._metadata_needs_update(curr_metadata, new_metadata[id]):
                    #restore everything at the moment
                    #retrieve email from destination email account
                    data = self.src.fetch(id, GIMAPFetcher.GET_ALL_INFO)
            
                    gid  = gstorer.store_email(data[id], compress = compress)
                    
                    print("update email with imap id %s and gmail id %s\n" % (id, gid))
                    
                    #update local index id gid => index per directory to be thought out
            else:
                
                # store data on disk within year month dir 
                gstorer =  GmailStorer(dir)  
                
                #retrieve email from destination email account
                data = self.src.fetch(id, GIMAPFetcher.GET_ALL_INFO)
            
                gid  = gstorer.bury_email(data[id], compress = compress)
                
                #update local index id gid => index per directory to be thought out
                print("Create and store email  with imap id %s, gmail id %s\n" % (id, gid))    
       
    
    
    def _delete_sync(self, imap_ids):
        """
           delete emails from the database if necessary
        """ 
        gstorer = GmailStorer(self.db_root_dir)
        
        #get gmail_ids from db
        db_gmail_ids_info = gstorer.get_all_existing_gmail_ids()
        
        #create a set of keys
        db_gmail_ids = set(db_gmail_ids_info.keys())
        
        #calculate the list elements to delete
        #query 10 items in one query
        for ten_imap_id in itertools.izip_longest(fillvalue=None,*[iter(imap_ids)]*10):
            
            # if None in list remove it
            if None in ten_imap_id: 
                ten_imap_id = [ id for id in ten_imap_id if id != None ]
            
            data = self.src.fetch(ten_imap_id, GIMAPFetcher.GET_GMAIL_ID)
            
            imap_gmail_ids = set()
            
            for key in data:
                imap_gmail_ids.add(data[key][GIMAPFetcher.GMAIL_ID])
            
            db_gmail_ids -= imap_gmail_ids
            
            #quit loop if db set is already empty
            if len(db_gmail_ids) == 0:
                break
        
        for gm_id in db_gmail_ids:
            #need to delete gm_id
            print("gm_id %s not in imap. Delete it" % (gm_id))
            gstorer.delete_emails([(gm_id, db_gmail_ids_info[gm_id])])
        
        
        
    def sync(self, imap_req = GIMAPFetcher.IMAP_ALL, compress = True):
        """
           sync with db on disk
        """
        # get all imap ids in All Mail
        imap_ids = self.src.search(imap_req)
        
        # create new emails in db and update existing emails
        self._create_update_sync(imap_ids, compress)
        
        #delete supress emails from DB since last sync
        self._delete_sync(imap_ids)
    
    def remote_sync(self):
        """
           Sync with a remote source (IMAP mirror or cloud storage area)
        """
        #sync remotely 
                         
            
            
        
    
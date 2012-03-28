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

Module containing the IMAPFetcher object which is the Wrapper around the modified IMAPClient object

'''
import math
import time
import socket
import re

import functools

import imaplib

import log_utils
import credential_utils

import gmvault_utils
import mod_imap as mimap

LOG = log_utils.LoggerFactory.get_logger('imap_utils')

class PushEmailError(Exception):
    """
       PushEmail Error
    """
    def __init__(self, a_msg, quarantined = False):
        """
           Constructor
        """
        super(PushEmailError, self).__init__(a_msg)
        self._in_quarantine = quarantined
    
    def quarantined(self):
        return self._in_quarantine

#retry decorator with nb of tries and sleep_time and backoff
def retry(a_nb_tries=3, a_sleep_time=1, a_backoff=1):
    """
      Decorator for retrying command when it failed with a imap or socket error.
      Should be used exclusively on imap exchanges.
      Strategy, always retry on any imaplib or socket error. Wait few seconds before to retry
      backoff sets the factor by which the a_sleep_time should lengthen after each failure. backoff must be greater than 1,
      or else it isn't really a backoff
    """
    if a_backoff < 1:
        raise ValueError("a_backoff must be greater or equal to 1")

    a_nb_tries = math.floor(a_nb_tries)
    if a_nb_tries < 0:
        raise ValueError("a_nb_tries must be 0 or greater")

    if a_sleep_time <= 0:
        raise ValueError("a_sleep_time must be greater than 0")
    
    def reconnect(the_self, rec_nb_tries, rec_error, rec_sleep_time = [1]):
        """
           Reconnect procedure. Sleep and try to reconnect
        """
        # go in retry mode if less than a_nb_tries
        while rec_nb_tries[0] < a_nb_tries:
            
            the_self.disconnect()            
            
            # add X sec of wait
            time.sleep(rec_sleep_time[0])
            rec_sleep_time[0] *= a_backoff #increase sleep time for next time
            
            rec_nb_tries[0] += 1
            
            #increase total nb of reconns
            the_self.total_nb_reconns += 1
           
            # go in retry mode: reconnect.
            # retry reconnect as long as we have tries left
            try:
                the_self.connect()
                
                return 
            
            except Exception, ignored:
                # catch all errors and try as long as we have tries left
                LOG.exception(ignored)
        else:
            #cascade error
            raise rec_error
    
    def inner_retry(the_func): #pylint:disable-msg=C0111
        def wrapper(*args, **kwargs): #pylint:disable-msg=C0111
            nb_tries = [0] # make it mutable in reconnect
            m_sleep_time = [a_sleep_time]  #make it mutable in reconnect
            while True:
                try:
                    return the_func(*args, **kwargs)
                except PushEmailError, p_err:
                    
                    LOG.debug("error message = %s. traceback:%s" % (p_err, gmvault_utils.get_exception_traceback()))
                    
                    LOG.critical("Cannot reach the gmail server (see logs). Wait %s seconds and retrying." % (m_sleep_time[0]))
                    
                    reconnect(args[0], nb_tries, p_err, m_sleep_time)
                
                except imaplib.IMAP4.abort, err: #abort is recoverable and error is not
                    
                    LOG.debug("error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    LOG.critical("Cannot reach the gmail server (see logs). Wait 1 seconds and retrying")
                    
                    # problem with this email, put it in quarantine
                    reconnect(args[0], nb_tries, err, m_sleep_time)    
                    
                except socket.error, sock_err:
                    LOG.debug("error message = %s. traceback:%s" % (sock_err, gmvault_utils.get_exception_traceback()))
                    
                    LOG.critical("Cannot reach the gmail server (see logs). Wait 1 seconds and retrying")
                    
                    reconnect(args[0], nb_tries, sock_err, m_sleep_time)
                    
                except imaplib.IMAP4.error, err:
                    
                    #just trace it back for the moment
                    LOG.debug("IMAP (normal) error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    raise err

        return functools.wraps(the_func)(wrapper)
        #return wrapper
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
    IMAP_ALL          = {'type':'imap', 'req':'ALL'}
    
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

    GET_ALL_BUT_DATA  = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, IMAP_FLAGS, IMAP_HEADER_FIELDS]
    
    GET_DATA_ONLY     = [GMAIL_ID, IMAP_BODY_PEEK]
 
    GET_GMAIL_ID      = [ GMAIL_ID ]
    
    GET_GMAIL_ID_DATE = [ GMAIL_ID,  IMAP_INTERNALDATE]

    def __init__(self, host, port, login, credential, readonly_folder = True): #pylint:disable-msg=R0913
        '''
            Constructor
        '''
        self.host                   = host
        self.port                   = port
        self.login                  = login
        self.once_connected         = False
        self.credential             = credential
        self.ssl                    = True
        self.use_uid                = True
        self.readonly_folder        = readonly_folder
        self._all_mail_folder       = None
        self.server                 = None
        self.go_to_all_folder       = True
        self.total_nb_reconns       = 0
    
    def connect(self, go_to_all_folder = True):
        """
           connect to the IMAP server
        """
        # create imap object
        self.server = mimap.MonkeyIMAPClient(self.host, port = self.port, use_uid= self.use_uid, ssl= self.ssl)
        # connect with password or xoauth
        if self.credential['type'] == 'passwd':
            self.server.login(self.login, self.credential['value'])
        elif self.credential['type'] == 'xoauth':
            #connect with xoauth 
            if self.once_connected:
                #already connected once so renew xoauth req because it can expire
                self.credential['value'] = credential_utils.CredentialHelper.get_xoauth_req_from_email(self.login)
                
            self.server.xoauth_login(self.credential['value']) 
        else:
            raise Exception("Unknown authentication method %s. Please use xoauth or passwd authentication " % (self.credential['type']))
            
        #set connected to True to hanlde reconnection in case of failure
        self.once_connected = True
        
        # check gmailness
        self.check_gmailness()
        
        self._all_mail_folder = None
        
        #find the all mail folder
        self.find_all_mail_folder()
        
        # set to GMAIL_ALL dir by default and in readonly
        if go_to_all_folder:
            self.server.select_folder(self._all_mail_folder, readonly = self.readonly_folder)
            
    def disconnect(self):
        """
           disconnect to avoid too many simultaneous connection problem
        """
        if self.server:
            try:
                self.server.logout()
            except Exception, ignored: #ignored exception but still og it in log file if activated
                LOG.exception(ignored)
                
            self.server = None
    
    def enable_compression(self):
        """
           Try to enable the compression
        """
        self.server.enable_compression()
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
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
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def get_all_folders(self): 
        """
           Return all folders mainly for debuging purposes
        """
        return self.server.list_folders()
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def get_capabilities(self):
        """
           return the server capabilities
        """
        if not self.server:
            raise Exception("GIMAPFetcher not connect to the GMAIL server")
        
        return self.server.capabilities()
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def check_gmailness(self):
        """
           Check that the server is a gmail server
        """
        if not GIMAPFetcher.GMAIL_EXTENSION in self.get_capabilities():
            raise Exception("GIMAPFetcher is not connect to a IMAP GMAIL server. Please check host (%s) and port (%s)" % (self.host, self.port))
        
        return True
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def search(self, a_criteria):
        """
           Return all found ids corresponding to the search
        """
        return self.server.search(a_criteria)
    
    @retry(4,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec
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
                    
         
    @retry(4,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec
    def push_email(self, a_body, a_flags, a_internal_time, a_labels):
        """
           Push a complete email body 
        """
        #protection against myself
        if self.login == 'guillaume.aubert@gmail.com':
            raise Exception("Cannot push to this account")
    
        LOG.debug("Before to Append")
        res = self.server.append(self._all_mail_folder, a_body, a_flags, a_internal_time)
    
        LOG.debug("Appended data with flags %s and internal time %s" % (a_flags, a_internal_time))
        
        # check res otherwise Exception
        if '(Success)' not in res:
            raise PushEmailError("GIMAPFetcher cannot restore email in %s account." %(self.login))
        
        match = GIMAPFetcher.APPENDUID_RE.match(res)
        if match:
            result_uid = int(match.group(1))
        else:
            # do not quarantine it because it seems to be done by Google Mail to forbid data uploading.
            raise PushEmailError("No email id returned by IMAP APPEND command. Quarantine this email.", quarantined = True)
        
        labels_str = self._build_labels_str(a_labels)
        
        if labels_str:  
            #has labels so update email  
            LOG.debug("Before to store")
            ret_code, data = self.server._imap.uid('STORE', result_uid, '+X-GM-LABELS', labels_str)
            
            
            LOG.debug("Stored Labels %s in gm_id %s" % (labels_str, result_uid))
        
            # check if it is ok otherwise exception
            if ret_code != 'OK':
                raise PushEmailError("Cannot add Labels %s to email with uid %d. Error:%s" % (labels_str, result_uid, data))
        
        return result_uid
    
    def fetch_with_gmid(self, a_gm_id):
        """
           fetch an email with it gmailID
        """
        pass

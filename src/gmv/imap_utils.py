# -*- coding: utf-8 -*-
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Module containing the IMAPFetcher object which is the Wrapper around the modified IMAPClient object

'''
import math
import time
import socket
import re

import functools

import ssl
import imaplib

import gmv.gmvault_const as gmvault_const
import gmv.log_utils as log_utils
import gmv.credential_utils as credential_utils

import gmv.gmvault_utils as gmvault_utils
import gmv.mod_imap as mimap

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
        """ Get email to quarantine """
        return self._in_quarantine

class LabelError(Exception):
    """
       LabelError. Exception send when there is an error when adding labels to message
    """
    def __init__(self, a_msg, ignore = False):
        """
           Constructor
        """
        super(LabelError, self).__init__(a_msg)
        self._ignore = ignore
    
    def ignore(self):
        """ ignore """
        return self._ignore

#retry decorator with nb of tries and sleep_time and backoff
def retry(a_nb_tries=3, a_sleep_time=1, a_backoff=1): #pylint:disable=R0912
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
    
    def reconnect(the_self, rec_nb_tries, total_nb_tries, rec_error, rec_sleep_time = [1]): #pylint: disable=W0102
        """
           Reconnect procedure. Sleep and try to reconnect
        """
        # go in retry mode if less than a_nb_tries
        while rec_nb_tries[0] < total_nb_tries:
            
            LOG.critical("Disconnecting from Gmail Server and sleeping ...")
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
                LOG.critical("Reconnecting to the from Gmail Server.")
                
                #reconnect to the current folder
                the_self.connect(go_to_current_folder = True )
                
                return 
            
            except Exception, ignored:
                # catch all errors and try as long as we have tries left
                LOG.exception(ignored)
        else:
            #cascade error
            raise rec_error
    
    def inner_retry(the_func): #pylint:disable=C0111,R0912
        def wrapper(*args, **kwargs): #pylint:disable=C0111,R0912
            nb_tries = [0] # make it mutable in reconnect
            m_sleep_time = [a_sleep_time]  #make it mutable in reconnect
            while True:
                try:
                    return the_func(*args, **kwargs)
                except PushEmailError, p_err:
                    
                    LOG.debug("error message = %s. traceback:%s" % (p_err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Cannot reach the Gmail server. Wait %s second(s) and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                    
                    reconnect(args[0], nb_tries, a_nb_tries, p_err, m_sleep_time)
                
                except imaplib.IMAP4.abort, err: #abort is recoverable and error is not
                    
                    LOG.debug("IMAP (abort) error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Received an IMAP abort error. Wait %s second(s) and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                        
                    # problem with this email, put it in quarantine
                    reconnect(args[0], nb_tries, a_nb_tries, err, m_sleep_time)    
                    
                except socket.error, sock_err:
                    LOG.debug("error message = %s. traceback:%s" % (sock_err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Cannot reach the Gmail server. Wait %s second(s) and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                        
                    reconnect(args[0], nb_tries, a_nb_tries, sock_err, m_sleep_time)
                
                except ssl.SSLError, ssl_err:
                    LOG.debug("error message = %s. traceback:%s" % (ssl_err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Cannot reach the Gmail server. Wait %s second(s) and retrying." % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                        
                    reconnect(args[0], nb_tries, a_nb_tries, sock_err, m_sleep_time)
                
                except imaplib.IMAP4.error, err:
                    
                    #just trace it back for the moment
                    LOG.debug("IMAP (normal) error message = %s. traceback:%s" % (err, gmvault_utils.get_exception_traceback()))
                    
                    if nb_tries[0] < a_nb_tries:
                        LOG.critical("Error when reaching Gmail server. Wait %s second(s) and retry up to 2 times." \
                                     % (m_sleep_time[0]))
                    else:
                        LOG.critical("Stop retrying, tried too many times ...")
                    
                    #raise err
                    # retry 2 times before to quit
                    reconnect(args[0], nb_tries, 2, err, m_sleep_time)

        return functools.wraps(the_func)(wrapper)
        #return wrapper
    return inner_retry

class GIMAPFetcher(object): #pylint:disable=R0902,R0904
    '''
    IMAP Class reading the information
    '''
    GMAIL_EXTENSION     = 'X-GM-EXT-1'  # GMAIL capability
    GMAIL_ALL           = u'[Gmail]/All Mail' #GMAIL All Mail mailbox
    
    GENERIC_GMAIL_ALL   = u'\\AllMail' # unlocalised GMAIL ALL
    GENERIC_DRAFTS      = u'\\Drafts' # unlocalised DRAFTS
    GENERIC_GMAIL_CHATS = gmvault_const.GMAIL_UNLOCAL_CHATS   # unlocalised Chats names
    
    FOLDER_NAMES        = ['ALLMAIL', 'CHATS', 'DRAFTS']
    
    GMAIL_ID            = 'X-GM-MSGID' #GMAIL ID attribute
    GMAIL_THREAD_ID     = 'X-GM-THRID'
    GMAIL_LABELS        = 'X-GM-LABELS'
    
    IMAP_INTERNALDATE = 'INTERNALDATE'
    IMAP_FLAGS        = 'FLAGS'
    IMAP_ALL          = {'type':'imap', 'req':'ALL'}
    
    EMAIL_BODY        = 'BODY[]'
    
    GMAIL_SPECIAL_DIRS = ['\\Inbox', '\\Starred', '\\Sent', '\\Draft', '\\Important']
    
    #GMAIL_SPECIAL_DIRS_LOWER = ['\\inbox', '\\starred', '\\sent', '\\draft', '\\important']
    GMAIL_SPECIAL_DIRS_LOWER = ['\\inbox', '\\starred', '\\sent', '\\draft', '\\important', '\\trash']
    
    IMAP_BODY_PEEK     = 'BODY.PEEK[]' #get body without setting msg as seen

    #get the body info without setting msg as seen
    IMAP_HEADER_PEEK_FIELDS = 'BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]' 

    #key used to find these fields in the IMAP Response
    IMAP_HEADER_FIELDS_KEY      = 'BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT X-GMAIL-RECEIVED)]'
    
    #GET_IM_UID_RE
    APPENDUID         = r'^[APPENDUID [0-9]* ([0-9]*)] \(Success\)$'
    
    APPENDUID_RE      = re.compile(APPENDUID)
    
    GET_ALL_INFO      = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, \
                          IMAP_BODY_PEEK, IMAP_FLAGS, IMAP_HEADER_PEEK_FIELDS]

    GET_ALL_BUT_DATA  = [ GMAIL_ID, GMAIL_THREAD_ID, GMAIL_LABELS, IMAP_INTERNALDATE, \
                          IMAP_FLAGS, IMAP_HEADER_PEEK_FIELDS]
    
    GET_DATA_ONLY     = [ GMAIL_ID, IMAP_BODY_PEEK]
 
    GET_GMAIL_ID      = [ GMAIL_ID ]
    
    GET_GMAIL_ID_DATE = [ GMAIL_ID,  IMAP_INTERNALDATE]

    def __init__(self, host, port, login, credential, readonly_folder = True): #pylint:disable=R0913
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
        
        self.localized_folders      = { 'ALLMAIL': { 'loc_dir' : None, 'friendly_name' : 'allmail'}, 
                                        'CHATS'  : { 'loc_dir' : None, 'friendly_name' : 'chats'}, 
                                        'DRAFTS' : { 'loc_dir' : None, 'friendly_name' : 'drafts'} }
        
        # memoize the current folder (All Mail or Chats) for reconnection management
        self.current_folder        = None
        
        self.server                 = None
        self.go_to_all_folder       = True
        self.total_nb_reconns       = 0
        # True when CHATS or other folder error msg has been already printed
        self.printed_folder_error_msg = { 'ALLMAIL' : False, 'CHATS': False , 'DRAFTS':False }
        
        #update GENERIC_GMAIL_CHATS. Should be done at the class level
        self.GENERIC_GMAIL_CHATS.extend(gmvault_utils.get_conf_defaults().get_list('Localisation', 'chat_folder', []))
        
    def spawn_connection(self):
        """
           spawn a connection with the same parameters
        """
        conn = GIMAPFetcher(self.host, self.port, self.login, self.credential, self.readonly_folder)
        conn.connect()
        return conn
        
    def connect(self, go_to_current_folder = False):
        """
           connect to the IMAP server
        """
        # create imap object
        self.server = mimap.MonkeyIMAPClient(self.host, port = self.port, use_uid= self.use_uid, need_ssl= self.ssl)
        # connect with password or xoauth
        if self.credential['type'] == 'passwd':
            self.server.login(self.login, self.credential['value'])
        elif self.credential['type'] == 'oauth2':
            #connect with oauth2
            if self.once_connected:
                self.credential = credential_utils.CredentialHelper.get_oauth2_credential(self.login, renew_cred = False)

            LOG.debug("credential['value'] = %s" % (self.credential['value']))
            #try to login
            self.server.oauth2_login(self.credential['value'])
        else:
            raise Exception("Unknown authentication method %s. Please use xoauth or passwd authentication " \
                            % (self.credential['type']))
            
        #set connected to True to handle reconnection in case of failure
        self.once_connected = True
        
        # check gmailness
        self.check_gmailness()
         
        # find allmail chats and drafts folders
        self.find_folder_names()

        if go_to_current_folder and self.current_folder:
            self.server.select_folder(self.current_folder, readonly = self.readonly_folder)
            
        #enable compression
        if gmvault_utils.get_conf_defaults().get_boolean('General', 'enable_imap_compression', True):
            self.enable_compression()
            LOG.debug("After Enabling compression.")
        else:
            LOG.debug("Do not enable imap compression.") 
            
    def disconnect(self):
        """
           disconnect to avoid too many simultaneous connection problem
        """
        if self.server:
            try:
                self.server.logout()
            except Exception, ignored: #ignored exception but still log it in log file if activated
                LOG.exception(ignored)
                
            self.server = None
    
    def reconnect(self):
        """
           disconnect and connect again
        """
        self.disconnect()
        self.connect()
    
    def enable_compression(self):
        """
           Try to enable the compression
        """
        #self.server.enable_compression()
        pass

    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def find_folder_names(self):
        """
           depending on your account the all mail folder can be named 
           [GMAIL]/ALL Mail or [GoogleMail]/All Mail.
           Find and set the right one
        """      
        #use xlist because of localized dir names
        folders = self.server.xlist_folders()
        
        the_dir = None
        for (flags, _, the_dir) in folders:
            #non localised GMAIL_ALL
            if GIMAPFetcher.GENERIC_GMAIL_ALL in flags:
                #it could be a localized Dir name
                self.localized_folders['ALLMAIL']['loc_dir'] = the_dir
            elif the_dir in GIMAPFetcher.GENERIC_GMAIL_CHATS :
                #it could be a localized Dir name
                self.localized_folders['CHATS']['loc_dir'] = the_dir
            elif GIMAPFetcher.GENERIC_DRAFTS in flags:
                self.localized_folders['DRAFTS']['loc_dir'] = the_dir
                
        if not self.localized_folders['ALLMAIL']['loc_dir']: # all mail error
            raise Exception("Cannot find global 'All Mail' folder (maybe localized and translated into your language) ! "\
                            "Check whether 'Show in IMAP for 'All Mail' is enabled in Gmail (Go to Settings->Labels->All Mail)")
        elif not self.localized_folders['CHATS']['loc_dir'] and \
                 gmvault_utils.get_conf_defaults().getboolean("General","errors_if_chat_not_visible", False):
            raise Exception("Cannot find global 'Chats' folder ! Check whether 'Show in IMAP for 'Chats' "\
                            "is enabled in Gmail (Go to Settings->Labels->All Mail)") 
        elif not self.localized_folders['DRAFTS']['loc_dir']:
            raise Exception("Cannot find global 'Drafts' folder.")
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def find_all_mail_folder(self):
        """
           depending on your account the all mail folder can be named 
           [GMAIL]/ALL Mail or [GoogleMail]/All Mail.
           Find and set the right one
        """      
        #use xlist because of localized dir names
        folders = self.server.xlist_folders()
        
        the_dir = None
        for (flags, _, the_dir) in folders:
            #non localised GMAIL_ALL
            if GIMAPFetcher.GENERIC_GMAIL_ALL in flags:
                #it could be a localized Dir name
                self.localized_folders['ALLMAIL']['loc_dir'] = the_dir
                return the_dir
        
        if not self.localized_folders['ALLMAIL']['loc_dir']:
            #Error
            raise Exception("Cannot find global 'All Mail' folder (maybe localized and translated into your language) !"\
                  " Check whether 'Show in IMAP for 'All Mail' is enabled in Gmail (Go to Settings->Labels->All Mail)")
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def find_chats_folder(self):
        """
           depending on your account the chats folder can be named 
           [GMAIL]/Chats or [GoogleMail]/Chats, [GMAIL]/tous les chats ...
           Find and set the right one
           Npte: Cannot use the flags as Chats is not a system label. Thanks Google
        """
        #use xlist because of localized dir names
        folders = self.server.xlist_folders()
        
        LOG.debug("Folders = %s\n" % (folders))
        
        the_dir = None
        for (_, _, the_dir) in folders:
            #look for GMAIL Chats
            if the_dir in GIMAPFetcher.GENERIC_GMAIL_CHATS :
                #it could be a localized Dir name
                self.localized_folders['CHATS']['loc_dir'] = the_dir
                return the_dir
        
        #Error did not find Chats dir 
        if gmvault_utils.get_conf_defaults().getboolean("General", "errors_if_chat_not_visible", False):
            raise Exception("Cannot find global 'Chats' folder ! Check whether 'Show in IMAP for 'Chats' "\
                            "is enabled in Gmail (Go to Settings->Labels->All Mail)") 
       
        return None
    
    def is_visible(self, a_folder_name):
        """
           check if a folder is visible otherwise 
        """
        dummy = self.localized_folders.get(a_folder_name)
        
        if dummy and (dummy.get('loc_dir', None) is not None):
            return True
            
        if not self.printed_folder_error_msg.get(a_folder_name, None): 
            LOG.critical("Cannot find 'Chats' folder on Gmail Server. If you wish to backup your chats,"\
                         " look at the documentation to see how to configure your Gmail account.\n")
            self.printed_folder_error_msg[a_folder_name] = True
        
          
        return False

    def get_folder_name(self, a_folder_name):
        """return real folder name from generic ones"""        
        if a_folder_name not in self.FOLDER_NAMES:
            raise Exception("%s is not a predefined folder names. Please use one" % (a_folder_name) )
            
        folder = self.localized_folders.get(a_folder_name, {'loc_dir' : 'GMVNONAME'})['loc_dir']

        return folder
           
    @retry(3,1,2)  # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def select_folder(self, a_folder_name, use_predef_names = True):
        """
           Select one of the existing folder
        """
        if use_predef_names:
            if a_folder_name not in self.FOLDER_NAMES:
                raise Exception("%s is not a predefined folder names. Please use one" % (a_folder_name) )
            
            folder = self.localized_folders.get(a_folder_name, {'loc_dir' : 'GMVNONAME'})['loc_dir']
            
            if self.current_folder != folder:
                self.server.select_folder(folder, readonly = self.readonly_folder)
                self.current_folder = folder
            
        elif self.current_folder != a_folder_name:
            self.server.select_folder(a_folder_name, readonly = self.readonly_folder)
            self.current_folder = a_folder_name
        
        return self.current_folder
        
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def list_all_folders(self): 
        """
           Return all folders mainly for debuging purposes
        """
        return self.server.xlist_folders()
        
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
            raise Exception("GIMAPFetcher is not connected to a IMAP GMAIL server. Please check host (%s) and port (%s)" \
                  % (self.host, self.port))
        
        return True
    
    @retry(3,1,2) # try 3 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 4 sec
    def search(self, a_criteria):
        """
           Return all found ids corresponding to the search
        """
        return self.server.search(a_criteria)
    
    @retry(3,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec
    def fetch(self, a_ids, a_attributes):
        """
           Return all attributes associated to each message
        """
        return self.server.fetch(a_ids, a_attributes)

    @classmethod
    def _build_labels_str(cls, a_labels):
        """
           Create IMAP label string from list of given labels. 
           Convert the labels to utf7
           a_labels: List of labels
        """
        # add GMAIL LABELS
        labels_str = None
        if a_labels and len(a_labels) > 0:
            labels_str = '('
            for label in a_labels:
                label = gmvault_utils.remove_consecutive_spaces_and_strip(label)
                #add not in self.GMAIL_SPECIAL_DIRS_LOWER
                if label.lower() in cls.GMAIL_SPECIAL_DIRS_LOWER:
                    labels_str += '%s ' % (label)
                else:
                    label = label.replace('"', '\\"') #replace quote with escaped quotes
                    labels_str += '\"%s\" ' % (label)
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
            lab = gmvault_utils.remove_consecutive_spaces_and_strip(lab)
            if i == 0:
                dirs.append(lab)
            else:
                dirs.append('%s/%s' % (dirs[i-1], lab))
            
            i += 1
        
        return dirs
    
    def create_gmail_labels(self, labels, existing_folders):
        """
           Create folders and subfolders on Gmail in order
           to recreate the label hierarchy before to upload emails
           Note that adding labels with +X-GM-LABELS create only nested labels
           but not nested ones. This is why this trick must be used to 
           recreate the label hierarchy
           
           labels: list of labels to create
           
        """
        
        #1.5-beta moved that out of the loop to minimize the number of calls
        #to that method. (Could go further and memoize it)
        
        #get existing directories (or label parts)
        # get in lower case because Gmail labels are case insensitive
        listed_folders   = set([ directory.lower() for (_, _, directory) in self.list_all_folders() ])
        existing_folders = listed_folders.union(existing_folders)
        reserved_labels_map = gmvault_utils.get_conf_defaults().get_dict("Restore", "reserved_labels_map", \
                              { u'migrated' : u'gmv-migrated', u'\muted' : u'gmv-muted' })
        
        

        LOG.debug("Labels to create: [%s]" % (labels))
            
        for lab in labels:
            #LOG.info("Reserved labels = %s\n" % (reserved_labels))
            #LOG.info("lab.lower = %s\n" % (lab.lower()))
            if lab.lower() in reserved_labels_map.keys(): #exclude creation of migrated label
                n_lab = reserved_labels_map.get(lab.lower(), "gmv-default-label")
                LOG.info("Warning ! label '%s' (lower or uppercase) is reserved by Gmail and cannot be used."\
                         "Use %s instead" % (lab, n_lab)) 
                lab = n_lab
                LOG.info("translated lab = %s\n" % (lab))
           
            #split all labels
            labs = self._get_dir_from_labels(lab) 
            
            for directory in labs:
                low_directory = directory.lower() #get lower case directory but store original label
                if (low_directory not in existing_folders) and (low_directory not in self.GMAIL_SPECIAL_DIRS_LOWER):
                    try:
                        if self.server.create_folder(directory) != 'Success':
                            raise Exception("Cannot create label %s: the directory %s cannot be created." % (lab, directory))
                        else:
                            LOG.debug("============== ####### Created Labels (%s)." % (directory))
                    except imaplib.IMAP4.error, error:
                        #log error in log file if it exists
                        LOG.debug(gmvault_utils.get_exception_traceback())
                        if str(error).startswith("create failed: '[ALREADYEXISTS] Duplicate folder"):
                            LOG.critical("Warning: label %s already exists on Gmail and Gmvault tried to create it."\
                                         " Ignore this issue." % (directory) )
                        else:
                            raise error
                    
                    #add created folder in folders
                    existing_folders.add(low_directory)

        #return all existing folders
        return existing_folders
    
    
    @retry(3,1,2)
    def apply_labels_to(self, imap_ids, labels):
        """
           apply one labels to x emails
        """
        # go to All Mail folder
        LOG.debug("Applying labels %s" % (labels))
        
        the_timer = gmvault_utils.Timer()
        the_timer.start()

        #utf7 the labels as they should be
        labels = [ utf7_encode(label) for label in labels ]

        labels_str = self._build_labels_str(labels) # create labels str
    
        if labels_str:  
            #has labels so update email  
            the_timer.start()
            LOG.debug("Before to store labels %s" % (labels_str))
            id_list = ",".join(map(str, imap_ids))
            #+X-GM-LABELS.SILENT to have not returned data
            try:
                ret_code, data = self.server._imap.uid('STORE', id_list, '+X-GM-LABELS.SILENT', labels_str) #pylint: disable=W0212
            except imaplib.IMAP4.error, original_err:
                LOG.info("Error in apply_labels_to. See exception traceback")
                LOG.debug(gmvault_utils.get_exception_traceback())
                # try to add labels to each individual ids
                faulty_ids = []
                for the_id in imap_ids:
                    try:
                       ret_code, data = self.server._imap.uid('STORE', the_id, '+X-GM-LABELS.SILENT', labels_str) #pylint: disable=W0212
                    except imaplib.IMAP4.error, store_err:
                       LOG.debug("Error when trying to apply labels %s to emails with imap_id %s. Error:%s" % (labels_str, the_id, store_err))
                       faulty_ids.append(the_id)
                
                #raise an error to ignore faulty emails       
                raise LabelError("Cannot add Labels %s to emails with uids %s. Error:%s" % (labels_str, faulty_ids, original_err), ignore = True) 

            #ret_code, data = self.server._imap.uid('COPY', id_list, labels[0])
            LOG.debug("After storing labels %s. Operation time = %s s.\nret = %s\ndata=%s" \
                      % (labels_str, the_timer.elapsed_ms(),ret_code, data))

            # check if it is ok otherwise exception
            if ret_code != 'OK':
                #update individuals emails
                faulty_ids = []
                for the_id in imap_ids:
                    try:
                       ret_code, data = self.server._imap.uid('STORE', the_id, '+X-GM-LABELS.SILENT', labels_str) #pylint: disable=W0212
                    except imaplib.IMAP4.error, store_err:
                       LOG.debug("Error when trying to apply labels %s to emails with imap_id %s. Error:%s" % (labels_str, the_id, store_err))
                       faulty_ids.append(the_id)

                raise LabelError("Cannot add Labels %s to emails with uids %s. Error:%s" % (labels_str, faulty_ids, data), ignore = True)
            else:
                LOG.debug("Stored Labels %s for gm_ids %s" % (labels_str, imap_ids))
       
    def delete_gmail_labels(self, labels, force_delete = False):
        """
           Delete passed labels. Beware experimental and labels must be ordered
        """
        for label in reversed(labels):
            
            labs = self._get_dir_from_labels(label)
            
            for directory in reversed(labs):
                
                if force_delete or ( (directory.lower() not in self.GMAIL_SPECIAL_DIRS_LOWER) \
                   and self.server.folder_exists(directory) ): #call server exists each time
                    try:
                        self.server.delete_folder(directory)
                    except imaplib.IMAP4.error, _:
                        LOG.debug(gmvault_utils.get_exception_traceback())
    
    
    def erase_mailbox(self):
        """
           This is for testing purpose and cannot be used with my own mailbox
        """
        
        if self.login == "guillaume.aubert@gmail.com":
            raise Exception("Error cannot activate erase_mailbox with %s" % (self.login))

        LOG.info("Erase mailbox for account %s." % (self.login))

        LOG.info("Delete folders")

        #delete folders
        folders = self.server.xlist_folders()

        LOG.debug("Folders = %s.\n" %(folders))

        trash_folder_name = None

        for (flags, _, the_dir) in folders:
            if (u'\\Starred' in flags) or (u'\\Spam' in flags) or (u'\\Sent' in flags) \
               or (u'\\Important' in flags) or (the_dir == u'[Google Mail]/Chats') \
               or (the_dir == u'[Google Mail]') or (u'\\Trash' in flags) or \
               (u'\\Inbox' in flags) or (GIMAPFetcher.GENERIC_GMAIL_ALL in flags) or \
               (GIMAPFetcher.GENERIC_DRAFTS in flags) or (GIMAPFetcher.GENERIC_GMAIL_CHATS in flags):
                LOG.info("Ignore folder %s" % (the_dir))           

                if (u'\\Trash' in flags): #keep trash folder name
                    trash_folder_name = the_dir
            else:
                LOG.info("Delete folder %s" % (the_dir))
                self.server.delete_folder(the_dir)
        
        self.select_folder('ALLMAIL')

        #self.server.store("1:*",'+X-GM-LABELS', '\\Trash')
        #self.server._imap.uid('STORE', id_list, '+X-GM-LABELS.SILENT', '\\Trash')
        #self.server.add_gmail_labels(self, messages, labels)

        LOG.info("Move emails to Trash.")
        
        # get all imap ids in ALLMAIL
        imap_ids = self.search(GIMAPFetcher.IMAP_ALL)

        #flag all message as deleted
        #print(self.server.delete_messages(imap_ids))

        if len(imap_ids) > 0:
            self.apply_labels_to(imap_ids, ['\\Trash'])

            LOG.info("Got all imap_ids flagged to Trash : %s." % (imap_ids))

        
        else:
            LOG.info("No messages to erase.")

        LOG.info("Delete emails from Trash.")

        if trash_folder_name == None:
            raise Exception("No trash folder ???")

        self.select_folder(trash_folder_name, False)
        
        # get all imap ids in ALLMAIL
        imap_ids = self.search(GIMAPFetcher.IMAP_ALL)

        if len(imap_ids) > 0:
            res = self.server.delete_messages(imap_ids)
            LOG.debug("Delete messages result = %s" % (res))

        LOG.info("Expunge everything.")
        self.server.expunge()

    @retry(4,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec    
    def push_data(self, a_folder, a_body, a_flags, a_internal_time):
        """
           Push the data
        """  
        # protection against myself
        if self.login == 'guillaume.aubert@gmail.com':
            raise Exception("Cannot push to this account")
        
        the_timer = gmvault_utils.Timer()
        the_timer.start()
        LOG.debug("Before to Append email contents")
        #import sys  #to print the msg in stdout
        #import codecs
        #sys.stdout = codecs.getwriter('utf-8')(sys.__stdout__) 
        #msg = "a_folder = %s, a_flags = %s" % (a_folder.encode('utf-8'), a_flags)
        #msg = "a_folder = %s" % (a_folder.encode('utf-8'))
        #msg = msg.encode('utf-8')
        #print(msg)
        res = None
        try:
           #a_body = self._clean_email_body(a_body)
           res = self.server.append(a_folder, a_body, a_flags, a_internal_time)
        except imaplib.IMAP4.abort, err:
           # handle issue when there are invalid characters (This is do to the presence of null characters)
           if str(err).find("APPEND => Invalid character in literal") >= 0:
              LOG.critical("Invalid character detected. Try to clean the email and reconnect.")
              a_body = self._clean_email_body(a_body)
              self.reconnect()
              res    = self.server.append(a_folder, a_body, a_flags, a_internal_time)
    
        LOG.debug("Appended data with flags %s and internal time %s. Operation time = %s.\nres = %s\n" \
                  % (a_flags, a_internal_time, the_timer.elapsed_ms(), res))
        
        # check res otherwise Exception
        if '(Success)' not in res:
            raise PushEmailError("GIMAPFetcher cannot restore email in %s account." %(self.login))
        
        match = GIMAPFetcher.APPENDUID_RE.match(res)
        if match:
            result_uid = int(match.group(1))
            LOG.debug("result_uid = %s" %(result_uid))
        else:
            # do not quarantine it because it seems to be done by Google Mail to forbid data uploading.
            raise PushEmailError("No email id returned by IMAP APPEND command. Quarantine this email.", quarantined = True)
        
        return result_uid          

    def _clean_email_body(self, a_body):
        """
           Clean the body of the email
        """
        #for the moment just try to remove the null character brut force. In the future will have to parse the email and clean it
        return a_body.replace("\0", '')
         
    @retry(4,1,2) # try 4 times to reconnect with a sleep time of 1 sec and a backoff of 2. The fourth time will wait 8 sec
    def deprecated_push_email(self, a_body, a_flags, a_internal_time, a_labels):
        """
           Push a complete email body 
        """
        #protection against myself
        if self.login == 'guillaume.aubert@gmail.com':
            raise Exception("Cannot push to this account")
    
        the_t = gmvault_utils.Timer()
        the_t.start()
        LOG.debug("Before to Append email contents")


        try:
           res = self.server.append(u'[Google Mail]/All Mail', a_body, a_flags, a_internal_time)
        except imaplib.IMAP4.abort, err:
           # handle issue when there are invalid characters (This is do to the presence of null characters)
           if str(err).find("APPEND => Invalid character in literal") >= 0:
              a_body = self._clean_email_body(a_body)
              res    = self.server.append(u'[Google Mail]/All Mail', a_body, a_flags, a_internal_time)
    
        LOG.debug("Appended data with flags %s and internal time %s. Operation time = %s.\nres = %s\n" \
                  % (a_flags, a_internal_time, the_t.elapsed_ms(), res))
        
        # check res otherwise Exception
        if '(Success)' not in res:
            raise PushEmailError("GIMAPFetcher cannot restore email in %s account." %(self.login))
        
        match = GIMAPFetcher.APPENDUID_RE.match(res)
        if match:
            result_uid = int(match.group(1))
            LOG.debug("result_uid = %s" %(result_uid))
        else:
            # do not quarantine it because it seems to be done by Google Mail to forbid data uploading.
            raise PushEmailError("No email id returned by IMAP APPEND command. Quarantine this email.", quarantined = True)
        
        labels_str = self._build_labels_str(a_labels)
        
        if labels_str:  
            #has labels so update email  
            the_t.start()
            LOG.debug("Before to store labels %s" % (labels_str))
            self.server.select_folder(u'[Google Mail]/All Mail', readonly = self.readonly_folder) # go to current folder
            LOG.debug("Changing folders. elapsed %s s\n" % (the_t.elapsed_ms()))
            the_t.start()
            ret_code, data = self.server._imap.uid('STORE', result_uid, '+X-GM-LABELS', labels_str) #pylint: disable=W0212
            #ret_code = self.server._store('+X-GM-LABELS', [result_uid],labels_str)
            LOG.debug("After storing labels %s. Operation time = %s s.\nret = %s\ndata=%s" \
                      % (labels_str, the_t.elapsed_ms(),ret_code, data))
            
            LOG.debug("Stored Labels %s in gm_id %s" % (labels_str, result_uid))

            self.server.select_folder(u'[Google Mail]/Drafts', readonly = self.readonly_folder) # go to current folder
        
            # check if it is ok otherwise exception
            if ret_code != 'OK':
                raise PushEmailError("Cannot add Labels %s to email with uid %d. Error:%s" % (labels_str, result_uid, data))
        
        return result_uid

def decode_labels(labels):
    """
       Decode labels when they are received as utf7 entities or numbers
    """
    new_labels = []
    for label in labels:
        if isinstance(label, (int, long, float, complex)):
            label = str(label) 
        new_labels.append(utf7_decode(label))

    return new_labels

# utf7 conversion functions
def utf7_encode(s): #pylint: disable=C0103
    """encode in utf7"""
    if isinstance(s, str) and sum(n for n in (ord(c) for c in s) if n > 127):
        raise ValueError("%r contains characters not valid in a str folder name. "
                              "Convert to unicode first?" % s)

    r = [] #pylint: disable=C0103
    _in = []
    for c in s: #pylint: disable=C0103
        if ord(c) in (range(0x20, 0x26) + range(0x27, 0x7f)):
            if _in:
                r.extend(['&', utf7_modified_base64(''.join(_in)), '-'])
                del _in[:]
            r.append(str(c))
        elif c == '&':
            if _in:
                r.extend(['&', utf7_modified_base64(''.join(_in)), '-'])
                del _in[:]
            r.append('&-')
        else:
            _in.append(c)
    if _in:
        r.extend(['&', utf7_modified_base64(''.join(_in)), '-'])
    return ''.join(r)


def utf7_decode(s): #pylint: disable=C0103
    """decode utf7"""
    r = [] #pylint: disable=C0103
    decode = []
    for c in s: #pylint: disable=C0103
        if c == '&' and not decode:
            decode.append('&')
        elif c == '-' and decode:
            if len(decode) == 1:
                r.append('&')
            else:
                r.append(utf7_modified_unbase64(''.join(decode[1:])))
            decode = []
        elif decode:
            decode.append(c)
        else:
            r.append(c)
    if decode:
        r.append(utf7_modified_unbase64(''.join(decode[1:])))
    out = ''.join(r)

    if not isinstance(out, unicode):
        out = unicode(out, 'latin-1')
    return out


def utf7_modified_base64(s): #pylint: disable=C0103
    """utf7 base64"""
    s_utf7 = s.encode('utf-7')
    return s_utf7[1:-1].replace('/', ',')


def utf7_modified_unbase64(s): #pylint: disable=C0103
    """ utf7 unbase64"""
    s_utf7 = '+' + s.replace(',', '/') + '-'
    return s_utf7.decode('utf-7')


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

    Contains the class monkey patching IMAPClient and imaplib

'''
import zlib
import datetime
import re
import socket
import ssl
import cStringIO
import os

import imaplib  #for the exception
import imapclient

#enable imap debugging if GMV_IMAP_DEBUG is set 
if os.getenv("GMV_IMAP_DEBUG"):
    imaplib.Debug = 4 #enable debugging

#to enable imap debugging and see all command
#imaplib.Debug = 4 #enable debugging

INTERNALDATE_RE = re.compile(r'.*INTERNALDATE "'
r'(?P<day>[ 0123][0-9])-(?P<mon>[A-Z][a-z][a-z])-(?P<year>[0-9][0-9][0-9][0-9])'
r' (?P<hour>[0-9][0-9]):(?P<min>[0-9][0-9]):(?P<sec>[0-9][0-9])'
r' (?P<zonen>[-+])(?P<zoneh>[0-9][0-9])(?P<zonem>[0-9][0-9])'
r'"')

MON2NUM = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

#need to monkey patch _convert_INTERNALDATE to work with imaplib2
#modification of IMAPClient
def mod_convert_INTERNALDATE(date_string, normalise_times=True):#pylint: disable=C0103
    """
       monkey patched convert_INTERNALDATE
    """
    mon = INTERNALDATE_RE.match('INTERNALDATE "%s"' % date_string)
    if not mon:
        raise ValueError("couldn't parse date %r" % date_string)
    
    zoneh = int(mon.group('zoneh'))
    zonem = (zoneh * 60) + int(mon.group('zonem'))
    if mon.group('zonen') == '-':
        zonem = -zonem
    timez = imapclient.fixed_offset.FixedOffset(zonem)
    
    year    = int(mon.group('year'))
    the_mon = MON2NUM[mon.group('mon')]
    day     = int(mon.group('day'))
    hour    = int(mon.group('hour'))
    minute  = int(mon.group('min'))
    sec = int(mon.group('sec'))
    
    the_dt = datetime.datetime(year, the_mon, day, hour, minute, sec, 0, timez)
    
    if normalise_times:
        # Normalise to host system's timezone
        return the_dt.astimezone(imapclient.fixed_offset.FixedOffset.for_system()).replace(tzinfo=None)
    return the_dt

#monkey patching is done here
imapclient.response_parser._convert_INTERNALDATE = mod_convert_INTERNALDATE #pylint: disable=W0212

#monkey patching add compress in COMMANDS of imap
imaplib.Commands['COMPRESS'] = ('AUTH', 'SELECTED')

def datetime_to_imap(dt):
    """Convert a datetime instance to a IMAP datetime string.

    If timezone information is missing the current system
    timezone is used.
    """
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=imapclient.fixed_offset.FixedOffset.for_system())
    return dt.strftime("%d-%b-%Y %H:%M:%S %z")

def to_unicode(s):
    if isinstance(s, imapclient.six.binary_type):
        return s.decode('ascii')
    return s

def to_bytes(s):
    if isinstance(s, imapclient.six.text_type):
        return s.encode('ascii')
    return s

class IMAP4COMPSSL(imaplib.IMAP4_SSL): #pylint:disable=R0904
    """
       Add support for compression inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    SOCK_TIMEOUT = 70 # set a socket timeout of 70 sec to avoid for ever blockage in ssl.read

    def __init__(self, host = '', port = imaplib.IMAP4_SSL_PORT, keyfile = None, certfile = None):
        """
           constructor
        """
        self.compressor = None
        self.decompressor = None
        
        imaplib.IMAP4_SSL.__init__(self, host, port, keyfile, certfile)
        
    def activate_compression(self):
        """
           activate_compressing()
           Enable deflate compression on the socket (RFC 4978).
        """
        # rfc 1951 - pure DEFLATE, so use -15 for both windows
        self.decompressor = zlib.decompressobj(-15)
        self.compressor   = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)
        
    def open(self, host = '', port = imaplib.IMAP4_SSL_PORT): 
        """Setup connection to remote server on "host:port".
           (default: localhost:standard IMAP4 SSL port).
           This connection will be used by the routines:
           read, readline, send, shutdown.
        """
        self.host   = host
        self.port   = port

        self.sock   = socket.create_connection((host, port), self.SOCK_TIMEOUT) #add so_timeout  

        #self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1) #try to set TCP NO DELAY to increase performances

        self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile)
        #self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile, suppress_ragged_eofs = False)
        
        # This is the last correction added to avoid memory fragmentation in imaplib
        # makefile creates a file object that makes use of cStringIO to avoid mem fragmentation
        # it could be used without the compression 
        # (maybe make 2 set of methods without compression and with compression)
        #self.file   = self.sslobj.makefile('rb')

    def new_read(self, size):
        """
            Read 'size' bytes from remote.
            Call _intern_read that takes care of the compression
        """
        
        chunks = cStringIO.StringIO() #use cStringIO.cStringIO to avoir too much fragmentation
        read = 0
        while read < size:
            try:
                data = self._intern_read(min(size-read, 16384)) #never ask more than 16384 because imaplib can do it
            except ssl.SSLError, err:
                print("************* SSLError received %s" % (err)) 
                raise self.abort('Gmvault ssl socket error: EOF. Connection lost, reconnect.')
            read += len(data)
            chunks.write(data)
        
        return chunks.getvalue() #return the cStringIO content
    
    def read(self, size):
        """
            Read 'size' bytes from remote.
            Call _intern_read that takes care of the compression
        """
        
        chunks = cStringIO.StringIO() #use cStringIO.cStringIO to avoir too much fragmentation
        read = 0
        while read < size:
            data = self._intern_read(min(size-read, 16384)) #never ask more than 16384 because imaplib can do it
            if not data: 
                #to avoid infinite looping due to empty string returned
                raise self.abort('Gmvault ssl socket error: EOF. Connection lost, reconnect.') 
            read += len(data)
            chunks.write(data)
        
        return chunks.getvalue() #return the cStringIO content
  
    def _intern_read(self, size):
        """
            Read at most 'size' bytes from remote.
            Takes care of the compression
        """
        if self.decompressor is None:
            return self.sslobj.read(size)

        if self.decompressor.unconsumed_tail:
            data = self.decompressor.unconsumed_tail
        else:
            data = self.sslobj.read(8192) #Fixed buffer size. maybe change to 16384

        return self.decompressor.decompress(data, size)
        
    def readline(self):
        """Read line from remote."""
        line = cStringIO.StringIO() #use cStringIO to avoid memory fragmentation
        while 1:
            #make use of read that takes care of the compression
            #it could be simplified without compression
            char = self.read(1) 
            line.write(char)
            if char in ("\n", ""): 
                return line.getvalue()
    
    def shutdown(self):
        """Close I/O established in "open"."""
        #self.file.close() #if file created
        self.sock.close()
        
      
    def send(self, data):
        """send(data)
        Send 'data' to remote."""
        if self.compressor is not None:
            data = self.compressor.compress(data)
            data += self.compressor.flush(zlib.Z_SYNC_FLUSH)
        self.sslobj.sendall(data)
       
def seq_to_parenlist(flags):
    """Convert a sequence of strings into parenthised list string for
    use with IMAP commands.
    """
    if isinstance(flags, str):
        flags = (flags,)
    elif not isinstance(flags, (tuple, list)):
        raise ValueError('invalid flags list: %r' % flags)
    return '(%s)' % ' '.join(flags)
    
class MonkeyIMAPClient(imapclient.IMAPClient): #pylint:disable=R0903,R0904
    """
       Need to extend the IMAPClient to do more things such as compression
       Compression inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    
    def __init__(self, host, port=None, use_uid=True, need_ssl=False):
        """
           constructor
        """
        super(MonkeyIMAPClient, self).__init__(host, port, use_uid, need_ssl)

    def oauth2_login(self, oauth2_cred):
        """
        Connect using oauth2
        :param oauth2_cred:
        :return:
        """
        typ, data = self._imap.authenticate('XOAUTH2', lambda x: oauth2_cred)
        self._checkok('authenticate', typ, data)
        return data[0]
    
    def search(self, criteria): #pylint: disable=W0221
        """
           Perform a imap search or gmail search
        """
        if criteria.get('type','') == 'imap':
            #encoding criteria in utf-8
            req     = criteria['req'].encode('utf-8')
            charset = 'utf-8'
            return super(MonkeyIMAPClient, self).search(req, charset)
        elif criteria.get('type','') == 'gmail':
            return self.gmail_search(criteria.get('req',''))
        else:
            raise Exception("Unknown search type %s" % (criteria.get('type','no request type passed')))
        
    def gmail_search(self, criteria):
        """
           perform a search with gmailsearch criteria.
           eg, subject:Hello World
        """  
        criteria = criteria.replace('\\', '\\\\')
        criteria = criteria.replace('"', '\\"')

        #working but cannot send that understand when non ascii chars are used
        #args = ['CHARSET', 'utf-8', 'X-GM-RAW', '"%s"' % (criteria)]
        #typ, data = self._imap.uid('SEARCH', *args)

        #working Literal search 
        self._imap.literal = '"%s"' % (criteria)
        self._imap.literal = imaplib.MapCRLF.sub(imaplib.CRLF, self._imap.literal)
        self._imap.literal = self._imap.literal.encode("utf-8")
 
        #use uid to keep the imap ids consistent
        args = ['CHARSET', 'utf-8', 'X-GM-RAW']
        typ, data = self._imap.uid('SEARCH', *args) #pylint: disable=W0142
        
        self._checkok('search', typ, data)
        if data == [None]: # no untagged responses...
            return [ ]

        return [ long(i) for i in data[0].split() ]

    def append(self, folder, msg, flags=(), msg_time=None):
        """Append a message to *folder*.

        *msg* should be a string contains the full message including
        headers.

        *flags* should be a sequence of message flags to set. If not
        specified no flags will be set.

        *msg_time* is an optional datetime instance specifying the
        date and time to set on the message. The server will set a
        time if it isn't specified. If *msg_time* contains timezone
        information (tzinfo), this will be honoured. Otherwise the
        local machine's time zone sent to the server.

        Returns the APPEND response as returned by the server.
        """
        if msg_time:
            time_val = '"%s"' % datetime_to_imap(msg_time)
            time_val = to_bytes(time_val)
        else:
            time_val = None
        return self._command_and_check('append',
                                       self._normalise_folder(folder),
                                       imapclient.imapclient.seq_to_parenstr(flags),
                                       time_val,
                                       to_bytes(msg),
                                       unpack=True)
    
    def enable_compression(self):
        """
        enable_compression()
        Ask the server to start compressing the connection.
        Should be called from user of this class after instantiation, as in:
            if 'COMPRESS=DEFLATE' in imapobj.capabilities:
                imapobj.enable_compression()
        """
        ret_code, _ = self._imap._simple_command('COMPRESS', 'DEFLATE') #pylint: disable=W0212
        if ret_code == 'OK':
            self._imap.activate_compression()
        else:
            #no errors for the moment
            pass

        

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

Contains the class monkey patching IMAPClient and imaplib
'''

import zlib
import time
import datetime
import re
import socket
import ssl
import cStringIO

import imaplib  #for the exception
import imapclient

INTERNALDATE_RE = re.compile(r'.*INTERNALDATE "'
r'(?P<day>[ 0123][0-9])-(?P<mon>[A-Z][a-z][a-z])-(?P<year>[0-9][0-9][0-9][0-9])'
r' (?P<hour>[0-9][0-9]):(?P<min>[0-9][0-9]):(?P<sec>[0-9][0-9])'
r' (?P<zonen>[-+])(?P<zoneh>[0-9][0-9])(?P<zonem>[0-9][0-9])'
r'"')

MON2NUM = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

#need to monkey patch _convert_INTERNALDATE to work with imaplib2
#modification of IMAPClient
def mod_convert_INTERNALDATE(date_string, normalise_times=True):
    """
       monkey patched convert_INTERNALDATE
    """
    mo = INTERNALDATE_RE.match('INTERNALDATE "%s"' % date_string)
    if not mo:
        raise ValueError("couldn't parse date %r" % date_string)
    
    zoneh = int(mo.group('zoneh'))
    zonem = (zoneh * 60) + int(mo.group('zonem'))
    if mo.group('zonen') == '-':
        zonem = -zonem
    tz = imapclient.fixed_offset.FixedOffset(zonem)
    
    year = int(mo.group('year'))
    mon = MON2NUM[mo.group('mon')]
    day = int(mo.group('day'))
    hour = int(mo.group('hour'))
    minute = int(mo.group('min'))
    sec = int(mo.group('sec'))
    
    dt = datetime.datetime(year, mon, day, hour, minute, sec, 0, tz)
    
    if normalise_times:
        # Normalise to host system's timezone
        return dt.astimezone(imapclient.fixed_offset.FixedOffset.for_system()).replace(tzinfo=None)
    return dt

#monkey patching is done here
imapclient.response_parser._convert_INTERNALDATE = mod_convert_INTERNALDATE

#monkey patching add compress in COMMANDS of imap
imaplib.Commands['COMPRESS'] = ('AUTH', 'SELECTED')

class IMAP4COMPSSL(imaplib.IMAP4_SSL): #pylint:disable-msg=R0904

    SOCK_TIMEOUT = 70 # set a socket timeout of 70 sec to avoid for ever blockage in ssl.read

    """
       Add support for compression inspired by inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
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

            self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile)
            
            # This is the last correction added to avoid memory fragmentation in imaplib
            # makefile creates a file object that makes use of cStringIO to avoid mem fragmentation
            # it could be used without the compression 
            # (maybe make 2 set of methods without compression and with compression)
            #self.file   = self.sslobj.makefile('rb')
    
    def read(self, size):
        """
            Read 'size' bytes from remote.
            Call _intern_read that takes care of the compression
        """
        
        chunks = cStringIO.StringIO() #use cStringIO.cStringIO to avoir too much fragmentation
        read = 0
        while read < size:
            data = self._intern_read(min(size-read, 16384)) #never ask more than 16384 because imaplib can do it
            if not data: raise self.abort('Gmvault ssl socket error: EOF') #to avoid infinite looping due to empty string returned
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
            data = self.sslobj.read(8192) #maybe change to 16384

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
    
class MonkeyIMAPClient(imapclient.IMAPClient): #pylint:disable-msg=R0903
    """
       Need to extend the IMAPClient to do more things such as compression
       Compression inspired by http://www.janeelix.com/piers/python/py2html.cgi/piers/python/imaplib2
    """
    
    def __init__(self, host, port=None, use_uid=True, ssl=False):
        """
           constructor
        """
        super(MonkeyIMAPClient, self).__init__(host, port, use_uid, ssl)
    
    def _create_IMAP4(self): #pylint:disable-msg=C0103
        """
           Factory method creating an IMAPCOMPSSL or a standard IMAP4 Class
        """
        ImapClass = self.ssl and IMAP4COMPSSL or imaplib.IMAP4
        return ImapClass(self.host, self.port)
    
    def xoauth_login(self, xoauth_cred ):
        """
           Connect with xoauth
           Redefine this method to suppress dependency to oauth2 (non-necessary)
        """

        typ, data = self._imap.authenticate('XOAUTH', lambda x: xoauth_cred)
        self._checkok('authenticate', typ, data)
        return data[0]  
    
    def search(self, criteria):
        """
           Perform a imap search or gmail search
        """
        if criteria.get('type','') == 'imap':
            return super(MonkeyIMAPClient, self).search(criteria.get('req',''))
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
        
        typ, data = self._imap.uid('SEARCH', 'X-GM-RAW', '"%s"' % (criteria))
        
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
            time_val = time.mktime(msg_time.timetuple())
        else:
            time_val = None

        flags_list = seq_to_parenlist(flags)

        typ, data = self._imap.append(self._encode_folder_name(folder),
                                      flags_list, time_val, msg)
        self._checkok('append', typ, data)

        return data[0]
    
    def enable_compression(self):
        """
        enable_compression()
        Ask the server to start compressing the connection.
        Should be called from user of this class after instantiation, as in:
            if 'COMPRESS=DEFLATE' in imapobj.capabilities:
                imapobj.enable_compression()
        """
        ret_code, _ = self._imap._simple_command('COMPRESS', 'DEFLATE')
        if ret_code == 'OK':
            self._imap.activate_compression()
        else:
            #no errors for the moment
            pass

        

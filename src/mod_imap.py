'''
Created on Jan 6, 2012

@author: guillaume.aubert@gmail.com

Contains the class monkey patching IMAPClient and imaplib

'''
import zlib
import time
import imaplib  #for the exception
from imapclient import IMAPClient

#monkey patching add compress in COMMANDS of imap
imaplib.Commands['COMPRESS'] = ('AUTH', 'SELECTED')

class IMAP4COMPSSL(imaplib.IMAP4_SSL): #pylint:disable-msg=R0904
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
        
    
    def read(self, size):
        """Read 'size' bytes from remote."""
        # sslobj.read() sometimes returns < size bytes
        chunks = []
        read = 0
        while read < size:
            data = self._intern_read(min(size-read, 16384))
            read += len(data)
            chunks.append(data)
        
        return ''.join(chunks)
  
    def _intern_read(self, size):
        """
            Read at most 'size' bytes from remote.
        """

        if self.decompressor is None:
            return self.sslobj.read(size)

        if self.decompressor.unconsumed_tail:
            data = self.decompressor.unconsumed_tail
        else:
            data = self.sslobj.read(8192)

        return self.decompressor.decompress(data, size)
    
    def readline(self):
        """Read line from remote."""
        line = []
        while 1:
            char = self.read(1)
            line.append(char)
            if char in ("\n", ""): 
                return ''.join(line)
  
    def send(self, data):
        """send(data)
        Send 'data' to remote."""
        if self.compressor is not None:
            data = self.compressor.compress(data)
            data += self.compressor.flush(zlib.Z_SYNC_FLUSH)
        self.sslobj.sendall(data)
        

def datetime_to_imap(dt):
    """Convert a datetime instance to a IMAP datetime string.
    
    If timezone information is missing the current system
    timezone is used.
    """
    #if not dt.tzinfo:
    #    dt = dt.replace(tzinfo=FixedOffset.for_system())
    #return dt.strftime("%d-%b-%Y %H:%M:%S %z")
    return dt.strftime("%d-%b-%Y %H:%M:%S")

def seq_to_parenlist(flags):
    """Convert a sequence of strings into parenthised list string for
    use with IMAP commands.
    """
    if isinstance(flags, str):
        flags = (flags,)
    elif not isinstance(flags, (tuple, list)):
        raise ValueError('invalid flags list: %r' % flags)
    return '(%s)' % ' '.join(flags)
    
class MonkeyIMAPClient(IMAPClient): #pylint:disable-msg=R0903
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
        # Create the IMAP instance in a separate method to make unit tests easier
        #ImapClass = self.ssl and imaplib.IMAP4_SSL or imaplib.IMAP4
        ImapClass = self.ssl and IMAP4COMPSSL or imaplib.IMAP4
        return ImapClass(self.host, self.port)
    
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
            #time_val = '"%s"' % datetime_to_imap(msg_time)
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

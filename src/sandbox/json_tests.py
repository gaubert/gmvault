# -*- coding: utf-8 -*-
"""
Created on Nov 27, 2012

@author: aubert
"""
import json

string_to_test = u"Чаты"
labels = [ 0, string_to_test ]

def format(self, record):
        """
           Formats a record with the given formatter. If no formatter
           is set, the record message is returned. Generally speaking the
           return value is most likely a unicode string, but nothing in
           the handler interface requires a formatter to return a unicode
           string.

           The combination of a handler and formatter might have the
           formatter return an XML element tree for example.
        """
        # Decode the message to support non-ascii characters
        # We must choose the charset manually
        for record_charset in 'UTF-8', 'US-ASCII', 'ISO-8859-1':
            try:
                record.message = record.message.decode(record_charset)
                self.encoding = record_charset
            except UnicodeError:
                pass
            else:
                break
            
        if self.formatter is None:
            return record.message
        return self.formatter(record, self)

def data_to_test():
    """
       data to test
    """
    meta_obj = { 'labels' : labels }
    
    with open("/tmp/test.json", 'w') as f:
        json.dump(meta_obj, f)

    print("Data stored")
    
    with open("/tmp/test.json") as f:
        metadata = json.load(f)
    
    new_labels = []
    
    for label in metadata['labels']:
        if isinstance(label, (int, long, float, complex)):
            label = unicode(str(label))
        
        new_labels.append(label)
    
    metadata['labels'] = new_labels
    
    print("metadata = %s\n" % metadata)
    
    print("type(metadata['labels'][0]) = %s" % (type(metadata['labels'][0])))  
    
    print("metadata['labels'][0] = %s" % (metadata['labels'][0]))  
    
    print("type(metadata['labels'][1]) = %s" % (type(metadata['labels'][1])))  
    
    print("metadata['labels'][1] = %s" % (metadata['labels'][1]))  
    

def header_regexpr_test():
    """
    
    """ 
    #the_str = 'X-Gmail-Received: cef1a177794b2b6282967d22bcc2b6f49447a70d\r\nMessage-ID: <8b230a7105082305316d9c1a54@mail.gmail.com>\r\nSubject: Hessian ssl\r\n\r\n'
    the_str = 'Message-ID: <8b230a7105082305316d9c1a54@mail.gmail.com>\r\nX-Gmail-Received: cef1a177794b2b6282967d22bcc2b6f49447a70d\r\nSubject: Hessian ssl\r\n\r\n'
    
    
    import gmv.gmvault_db as gmvault_db
    
    matched = gmvault_db.GmailStorer.HF_SUB_RE.search(the_str)
    if matched:
        subject = matched.group('subject')
        print("subject matched = <%s>\n" % (subject))
        
    # look for a msg id
    matched = gmvault_db.GmailStorer.HF_MSGID_RE.search(the_str)
    if matched:
        msgid = matched.group('msgid')
        print("msgid matched = <%s>\n" % (msgid))

    
    matched = gmvault_db.GmailStorer.HF_XGMAIL_RECV_RE.search(the_str)
    if matched:
        received = matched.group('received').strip()
        print("matched = <%s>\n" % (received))

if __name__ == '__main__':
    header_regexpr_test()
    #data_to_test()

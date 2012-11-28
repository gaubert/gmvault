# -*- coding: utf-8 -*-
'''
Created on Nov 27, 2012

@author: aubert
'''
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
    
    meta_desc = open("/tmp/test.json", 'w')
    
    json.dump(meta_obj, meta_desc)
        
    meta_desc.flush()
    meta_desc.close()
    
    print("Data stored")
    
    meta_desc = open("/tmp/test.json")
    
    metadata = json.load(meta_desc)
    
    new_labels = []
    
    for label in metadata['labels']:
        if isinstance(label, (int, long, float, complex)):
            label = unicode(str(label))
        
        new_labels.append(label)
    
    metadata['labels'] = new_labels
    
    print("metadata = %s\n" % (metadata))
    
    print("type(metadata['labels'][0]) = %s" % (type(metadata['labels'][0])))  
    
    print("metadata['labels'][0] = %s" % (metadata['labels'][0]))  
    
    print("type(metadata['labels'][1]) = %s" % (type(metadata['labels'][1])))  
    
    print("metadata['labels'][1] = %s" % (metadata['labels'][1]))   
 

if __name__ == '__main__':
    data_to_test()
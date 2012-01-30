'''
Created on Jan 30, 2012

@author: guillaume.aubert@gmail.com
'''

from cmdline_utils  import CmdLineParser
import argparse
import sys

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    subparsers = parser.add_subparsers(help='commands')
    
    # A list command
    list_parser = subparsers.add_parser('sync', help='synchronize with given gmail account')
    list_parser.add_argument('email', action='store', help='email to sync with')
    list_parser.add_argument('-t', action='store', help='type of synchronisation')
    
    # A create command
    create_parser = subparsers.add_parser('create', help='Create a directory')
    create_parser.add_argument('dirname', action='store', help='New directory to create')
    create_parser.add_argument('--read-only', default=False, action='store_true',
                               help='Set permissions to prevent writing to the directory',
                               )
    
    # A delete command
    delete_parser = subparsers.add_parser('delete', help='Remove a directory')
    delete_parser.add_argument('dirname', action='store', help='The directory to remove')
    delete_parser.add_argument('--recursive', '-r', default=False, action='store_true',
                               help='Remove the contents of the directory, too',
                               )
    
    #sys.argv = ['gmvault.py', 'sync', '-h']
    
    sys.argv = ['gmvault.py', 'sync', 'guillaume.aubert@gmail.com', '-t', 'full_sync']
    
    print(parser.parse_args())
    
    #print("options = %s\n" % (options))
    #print("args = %s\n" % (args))

    
    
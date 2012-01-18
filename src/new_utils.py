'''
Created on Jan 18, 2012

@author: aubert
'''
import os
import log_utils
import gmvault_utils

LOG = log_utils.LoggerFactory.get_logger('gmv')

GMVAULT_DIR='GMVAULT_DIR'

def get_home_dir_path():
    """
       Get the Home dir
    """
    gmvault_dir = os.getenv(GMVAULT_DIR, None)

    # check by default in user[HOME]
    if not gmvault_dir:
        LOG.info("no ENV variable $GMVAULT_DIR defined. Set by default $GMVAULT_DIR to $HOME/.gmvault")
        gmvault_dir = "%s/.gmvault" % (os.getenv("HOME", "."))
    
    #create dir if not there
    gmvault_utils.makedirs(gmvault_dir)

    return gmvault_dir

def store_passwd(email, passwd):
    """
    """
    passwd_file = '%s/%s.passwd' % (get_home_dir_path(), email)
    
    fd = open(passwd_file, "w+")
    
    fd.write(passwd)
    
    fd.close()
    
    

if __name__ == '__main__':
    pass
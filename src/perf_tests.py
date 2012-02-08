'''
Created on Feb 8, 2012

@author: guillaume.aubert@gmail.com
'''
import unittest
import datetime
import os
import gmv.gmvault_utils as gmvault_utils
import gmv.collections_utils as collections_utils


class TestPerf(unittest.TestCase): #pylint:disable-msg=R0904
    """
       Current Main test class
    """

    def __init__(self, stuff):
        """ constructor """
        super(TestPerf, self).__init__(stuff)
        
    
    def setUp(self): #pylint:disable-msg=C0103
        pass
    
    def _create_dirs(self, working_dir, nb_dirs, nb_files_per_dir):
        """
           create all the dirs and files
        """
        dirname   = 'dir_%d'
        data_file = '%d.eml'
        meta_file = '%d.meta'
        
        for nb in xrange(0, nb_dirs):
            #make dir
            the_dir = '%s/%s' % (working_dir, dirname % (nb))
            gmvault_utils.makedirs(the_dir)
            
            for file_id in xrange(0,nb_files_per_dir):
                #create data file
                fd = open('%s/%s_%s' % (the_dir, dirname % (nb) , data_file % (file_id)), 'w')
                fd.write("something")
                fd.close()
                #create metadata file
                fd = open('%s/%s_%s' % (the_dir, dirname % (nb) , meta_file % (file_id)), 'w')
                fd.write("another info something")
                fd.close()
                
            
    
    def test_read_lots_of_files(self):
        """
           Test to mesure how long it takes to list over 100 000 files
           On server: 250 000 meta files in 50 dirs => 12 sec to list them 
           On linux macbook pro linux virtual machine => 9.91 sec to list them
        """
        root_dir = '/tmp/dirs'
        #create dirs and files
        #t1 = datetime.datetime.now()
        #self._create_dirs('/tmp/dirs', 50, 5000)
        #t2 = datetime.datetime.now()
        
        #print("\nTime to create dirs : %s\n" % (t2-t1))
        #print("\nFiles and dirs created.\n")
        
        the_iter = gmvault_utils.dirwalk(root_dir, a_wildcards= '*.meta')
        t1 = datetime.datetime.now()
        
        gmail_ids = collections_utils.OrderedDict()
        
        for filepath in the_iter:
            directory, fname = os.path.split(filepath)
            gmail_ids[os.path.splitext(fname)[0]] = os.path.basename(directory)
        t2 = datetime.datetime.now()
        
        print("\nnb of files = %s" % (len(gmail_ids.keys())))
        print("\nTime to read all meta files : %s\n" % (t2-t1))
        

def tests():
    """
       main test function
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerf)
    unittest.TextTestRunner(verbosity=2).run(suite)
 
if __name__ == '__main__':
    
    tests()
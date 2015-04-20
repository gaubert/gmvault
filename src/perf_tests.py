'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

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
            the_dir = '%s/%s' % (working_dir, dirname % nb)
            gmvault_utils.makedirs(the_dir)

            for file_id in xrange(0,nb_files_per_dir):
                #create data file
                with open('%s/%s_%s' % (the_dir, dirname % nb,
                                        data_file % file_id), 'w') as f:
                    f.write("something")
                #create metadata file
                with open('%s/%s_%s' % (the_dir, dirname % nb,
                                        meta_file % file_id), 'w') as f:
                    f.write("another info something")

    def test_read_lots_of_files(self):
        """
           Test to mesure how long it takes to list over 100 000 files
           On server: 250 000 meta files in 50 dirs (50,5000) => 9.74  sec to list them 
                      100 000 meta files in 20 dirs (20,5000) => 3.068 sec to list them
                      60  000 meta files in 60 dirs (60,1000) => 1.826 sec to list them
           On linux macbook pro linux virtual machine:
                      250 000 meta files in 50 dirs (50,5000) => 9.91 sec to list them
                      100 000 meta files in 20 dirs (20,5000) => 6.59 sec to list them
                      60  000 meta files in 60 dirs (60,1000) => 2.26 sec to list them
           On Win7 laptop machine:
                      250 000 meta files in 50 dirs (50,5000) => 56.50 sec (3min 27 sec if dir created and listed afterward) to list them
                      100 000 meta files in 20 dirs (20,5000) => 20.1 sec to list them
                      60  000 meta files in 60 dirs (60,1000) => 9.96 sec to list them
           
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

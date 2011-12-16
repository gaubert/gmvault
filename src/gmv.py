'''
Created on Dec 16, 2011

@author: guillaume.aubert@gmail.com
'''
from cmdline_utils  import CmdLineParser


HELP_USAGE = """ nms_client [options] request files or request
                                     
Arguments: a list of request files or an inline request."""

HELP_EPILOGUE = """Examples:

a) Requests examples

- Retrieve shi data with a request stored in a file
#> nms_client ims_shi.req

b) Pattern examples

#> nms_client shi.req -f "{req_id}_{req_fileprefix}.data"
will create 546_shi.data.
   
#> nms_client shi.req -f "{req_id}_{date}.data"
will create 547_20091224.data.

#> nms_client shi.req -f "{req_id}_{datetime}.data"
will create 548_20091224-01h12m23s.data

#> nms_client shi-1.req shi-2.req -f "{req_id}_{req_fileprefix}.data"
will create 549_shi-1.data and 550_shi-2.data
"""

class GMVaultLauncher(object):
    
    def __init__(self):
        """ constructor """
        super(GMVaultLauncher, self).__init__()

    def parse_args(self):
        """ Parse command line arguments 
            
            :returns: a dict that contains the arguments
               
            :except Exception Error
            
        """
        #print sys.argv
        
        parser = CmdLineParser()
        
        parser.add_option("-f", "--from", help = "From datetime (YYYY-MM-DDTHH:MM:SS)", \
                          dest = "dfrom", default = None)
        
        parser.add_option("-u", "--until", \
                          help="Until datetime (YYYY-MM-DDTHH:MM:SS)",\
                          dest="duntil", default= None)
        
        parser.add_option("-n", "--facilities", \
                          help="List of facilities (DVB_EUR_UPLINK, DVB_CBAND_SAM)",\
                          dest="facilities", default=None)
        
        parser.add_option("-m", "--hosts", \
                          help="filter by hosts if necessary",\
                          dest="hosts", default="ALL")
     
        parser.add_option("-v", "--verbose", \
                          help="Activate the verbose mode.",\
                          action="store_true", dest="verbose", default=False)
       
        """
        dir_help =  "Directory where the result files will be stored.".ljust(66)
        dir_help += "(Default =. the current dir)".ljust(66)
        dir_help += "The directory will be created if it doesn't exist.".ljust(66)
        
        parser.add_option("-d", "--dir", metavar="DIR", \
                          help = dir_help,\
                          dest ="output_dir", default=".")
        """
        
        # add custom usage and epilogue
        parser.epilogue = HELP_EPILOGUE
        parser.usage    = HELP_USAGE
        
        (options, args) = parser.parse_args() #pylint: disable-msg=W0612
        
        parsed_args = { }
        
        # if file check that file exist and read it
        # otherwise if -i read stdin 
        # otherwise start interactive session
        
        # enter request_file mode       
        if len(args) > 0:
            #create a list of grep elements
            parsed_args['search_request']       = " ".join(args) 
        
        # if file check that file exist and read it
        # otherwise if -i read stdin 
        # otherwise start interactive session
            
        # add from
        parsed_args['from']              = options.dfrom
        
        # add until
        parsed_args['until']             = options.duntil
        
        #facilities
        parsed_args['facilities']        = options.facilities
        
        #hosts
        parsed_args['hosts']             = options.hosts
     
        #verbose
        parsed_args['verbose']           = options.verbose
        
        #add parser itself for error handling
        parsed_args['parser'] = parser
        
        return parsed_args
    
    def run(self, args):
        """
           Run the grep with the given args 
        """
        print("In run. Args = %s\n" %(args))
    
def bootstrap_run():
    """ temporary bootstrap """
    
    gmvault = GMVaultLauncher()
    
    args = gmvault.parse_args()
    
    gmvault.run(args)
   
    
if __name__ == '__main__':
    import sys
    sys.argv = ['/homespace/gaubert/ecli-workspace/rodd/src/eumetsat/dmon/gems_grep.py', '--from', '2011-04-03T14:30:00', '--until', '2011-05-04T14:40:00', "dmon.log"]
    
    print(sys.argv)
    
    bootstrap_run()
    
    sys.exit(0)

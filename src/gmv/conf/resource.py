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
'''

import sys
import os

import conf.conf_helper

class ResourceError(Exception):
    """Base class for ressource exceptions"""

    def __init__(self,aMsg):
        
        super(ResourceError,self).__init__(aMsg)
        


class Resource(object):
    """
        Class read a ressource.
        It can be read first from the Command Line, then from the ENV as an env variable and finally from a conf file 
    """
    
    def __init__(self,CliArgument=None,EnvVariable=None,ConfProperty=None): 
        """ 
          Default Constructor.
          It is important to understand that there is precedence between the different ways to set the ressource:
          - get from the command line if defined otherwise get from the Env variable if defined otherwise get from the conf file otherwise error
       
           Args:
              CliArgument : The command line argument name
              EnvVariable : The env variable name used for this ressource
              ConfProperty: It should be a tuple containing two elements (group,property)
        """
      
        self._cliArg   = CliArgument.lower() if CliArgument is not None else None
        self._envVar   = EnvVariable.upper() if EnvVariable is not None else None
      
        if ConfProperty is not None:
            (self._confGroup,self._confProperty) = ConfProperty
        else:
            self._confGroup    = None
            self._confProperty = None
      
    def setCliArgument(self,CliArgument):
        self._cliArg = CliArgument.lower()
        
    def setEnvVariable(self,EnvVariable):
        self._envVar = EnvVariable
    
    def _get_srandardized_cli_argument(self,a_tostrip):
        """
           remove -- or - from the command line argument and add a -- prefix to standardize the cli argument 
        """
        s = a_tostrip
        
        while s.startswith('-'):
            s = s[1:]
        
        return '--%s'%(s)
    
    def _getValueFromTheCommandLine(self):
        """
          internal method for extracting the value from the command line.
          All command line agruments must be lower case (unix style).
          To Do support short and long cli args.
           
           Returns:
             the Value if defined otherwise None
        """
          
        # check precondition
        if self._cliArg == None:
            return None
        

        s = self._get_srandardized_cli_argument(self._cliArg)
    
        # look for cliArg in sys argv
        for arg in sys.argv:
            if arg.lower() == s:
                i = sys.argv.index(arg)
                #print "i = %d, val = %s\n"%(i,sys.argv[i])
                if len(sys.argv) <= i:
                    # No more thing to read in the command line so quit
                    print "Resource: Commandline argument %s has no value\n"%(self._cliArg)
                    return None 
                else:
                    #print "i+1 = %d, val = %s\n"%(i+1,sys.argv[i+1])
                    return sys.argv[i+1]
            

    def _getValueFromEnv(self):
        """
          internal method for extracting the value from the env.
          All support ENV Variables should be in uppercase.
           
           Returns:
             the Value if defined otherwise None
        """
      
        # precondition
        if self._envVar == None:
            return None
     
        return os.environ.get(self._envVar,None)
      
    def _getFromConf(self):
        """
           Try to read the info from the Configuration if possible
        """
        if (self._confGroup is not None) and (self._confProperty is not None):
            if conf_helper.Conf.can_be_instanciated():
                return conf_helper.Conf.get_instance().get(self._confGroup,self._confProperty)
        
        return None
          
        
    def getValue(self,aRaiseException=True):
        """
           Return the value of the Resource as a string.
           - get from the command line if defined otherwise get from the Env variable if defined otherwise get from the conf file otherwise error
              
           Arguments:
              aRaiseException: flag indicating if an exception should be raise if value not found
           Returns:
              value of the Resource as a String
       
           Raises:
              exception CTBTOError if the aRaiseExceptionOnError flag is activated
        """
       
        # get a value using precedence rule 1) command-line, 2) ENV, 3) Conf
        val = self._getValueFromTheCommandLine()
        if val is None:
            val = self._getValueFromEnv()
            if val is None:
                val = self._getFromConf()
                if (val is None) and aRaiseException:
                    
                    the_str = "Cannot find "
                    add_nor = 0
                    
                    if self._cliArg is not None:
                        the_str += "commandline argument %s" % (self._cliArg)
                        add_nor += 1
                    
                    if self._envVar is not None:
                        
                        if add_nor > 0:
                            the_str += ", nor "
                    
                        the_str += "the Env Variable %s" % (self._envVar)
                        add_nor += 1
                    
                    if self._confGroup is not None:
                        if add_nor > 0:
                            the_str += ", nor "
                        
                        the_str += "the Conf Group:[%s] and Property=%s" % (self._confGroup, self._confProperty)
                        add_nor += 1
                        
                    if add_nor == 0:
                        the_str += " any defined commandline argument, nor any env variable or Conf group and properties. They are all None, fatal error"
                    else:
                        the_str += ". One of them should be defined"
                    
                    raise ResourceError(the_str)
    
        # we do have a val
        return val
   
    def _get(self,conv):
        """
           Private _get method used to convert to the right expected type (int,float or boolean).
           Strongly inspired by ConfigParser.py
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return conv(self.getValue())

    def getValueAsInt(self):
        """
           Return the value as an int
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return self._get(int)

    def getValueAsFloat(self):
        """
           Return the value as a float
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return self._get(float)

    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def getValueAsBoolean(self):
        """
           Return the value as a boolean
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        v = self.getValue()
        if v.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % v
        return self._boolean_states[v.lower()]
  
 # unit tests part
import unittest
class TestResource(unittest.TestCase):
    
    def testResourceSimpleCli(self):
        """testResourceSimpleCli: read resource from CLI"""
        # set command line
        sys.argv.append("--LongName")
        sys.argv.append("My Cli Value")
        
        r = Resource(CliArgument="--LongName",EnvVariable=None) 
        
        self.assertEqual("My Cli Value",r.getValue())
        
        # look for LongName without --. It should be formalized by the Resource object
        r = Resource(CliArgument="LongName",EnvVariable=None) 
        
        self.assertEqual("My Cli Value",r.getValue())
    
    def testResourceFromEnv(self): 
        """testResourceFromENV: read resource from ENV"""   
        #ENV 
        os.environ["MYENVVAR"]="My ENV Value"
  
        r = Resource(CliArgument=None,EnvVariable="MYENVVAR")
        
        self.assertEqual("My ENV Value",r.getValue())
        
    def ztestResourcePriorityRules(self):
        """testResourcePriorityRules: test priority rules"""   
        r = Resource(CliArgument="--LongName",EnvVariable="MYENVVAR")
  
        self.assertEqual("My Cli Value",r.getValue())
  
    def testResourceGetDifferentTypes(self):
        """testResourceGetDifferentTypes: return resource in different types"""
        
        os.environ["MYENVVAR"]="yes"
        r = Resource(CliArgument=None,EnvVariable="MYENVVAR")
        
        self.assertEqual(r.getValueAsBoolean(),True)
        
        os.environ["MYENVVAR"]="4"
  
        r = Resource(CliArgument=None,EnvVariable="MYENVVAR")
  
        self.assertEqual(r.getValueAsInt()+1,5)
        
        os.environ["MYENVVAR"]="4.345"
  
        r = Resource(CliArgument=None,EnvVariable="MYENVVAR")
  
        self.assertEqual(r.getValueAsFloat()+1,5.345)
 
       

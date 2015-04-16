'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
import sys
import os
import re
import codecs

import gmv.conf.exceptions as exceptions
import gmv.conf.utils.struct_parser as struct_parser                                      

class ResourceError(Exception):
    """
        Base class for ressource exceptions 
    """

    def __init__(self, a_msg):
        
        super(ResourceError, self).__init__(a_msg)

class Resource(object):
    """
        Class read a ressource.
        It can be read first from the Command Line, then from the ENV as an env variable and finally from a conf file 
    """
    
    def __init__(self, a_cli_argument=None, a_env_variable=None, a_conf_property=None): 
        """ 
          Default Constructor.
          It is important to understand that there is precedence between the different ways to set the ressource:
          - get from the command line if defined otherwise get from the Env variable if defined otherwise get from the conf file otherwise error
       
           Args:
              a_cli_argument : The command line argument name
              a_env_variable : The env variable name used for this ressource
              a_conf_property: It should be a tuple containing two elements (group,property)
        """
      
        self._cli_arg   = a_cli_argument.lower() if a_cli_argument is not None else None
        self._env_var   = a_env_variable.upper() if a_env_variable is not None else None
      
        if a_conf_property is not None:
            (self._conf_group, self._conf_property) = a_conf_property
        else:
            self._conf_group    = None
            self._conf_property = None
      
    def set_cli_argument(self, a_cli_argument):
        """cli_argument setter"""
        self._cli_arg = a_cli_argument.lower()
        
    def set_env_variable(self, a_env_variable):
        """env_variable setter"""
        self._env_var = a_env_variable
    
    @classmethod
    def _get_srandardized_cli_argument(cls, a_tostrip):
        """
           remove -- or - from the command line argument and add a -- prefix to standardize the cli argument 
        """
        the_str = a_tostrip
        
        while the_str.startswith('-'):
            the_str = the_str[1:]
        
        return '--%s' % (the_str)
    
    def _get_value_from_command_line(self):
        """
          internal method for extracting the value from the command line.
          All command line agruments must be lower case (unix style).
          To Do support short and long cli args.
           
           Returns:
             the Value if defined otherwise None
        """
          
        # check precondition
        if self._cli_arg == None:
            return None
        

        the_s = Resource._get_srandardized_cli_argument(self._cli_arg)
    
        # look for cliArg in sys argv
        for arg in sys.argv:
            if arg.lower() == the_s:
                i = sys.argv.index(arg)
                #print "i = %d, val = %s\n"%(i,sys.argv[i])
                if len(sys.argv) <= i:
                    # No more thing to read in the command line so quit
                    print "Resource: Commandline argument %s has no value\n" % (self._cli_arg)
                    return None 
                else:
                    #print "i+1 = %d, val = %s\n"%(i+1,sys.argv[i+1])
                    return sys.argv[i+1]
            

    def _get_value_from_env(self):
        """
          internal method for extracting the value from the env.
          All support ENV Variables should be in uppercase.
           
           Returns:
             the Value if defined otherwise None
        """
      
        # precondition
        if self._env_var == None:
            return None
     
        return os.environ.get(self._env_var, None)
      
    def _get_from_conf(self):
        """
           Try to read the info from the Configuration if possible
        """
        if self._conf_group and self._conf_property:
            if Conf.can_be_instanciated():
                return Conf.get_instance().get(self._conf_group, self._conf_property)
        
        return None
          
        
    def get_value(self, a_raise_exception=True):
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
        val = self._get_value_from_command_line()
        if val is None:
            val = self._get_value_from_env()
            if val is None:
                val = self._get_from_conf()
                if (val is None) and a_raise_exception:
                    
                    the_str = "Cannot find "
                    add_nor = 0
                    
                    if self._cli_arg is not None:
                        the_str += "commandline argument %s" % (self._cli_arg)
                        add_nor += 1
                    
                    if self._env_var is not None:
                        
                        if add_nor > 0:
                            the_str += ", nor "
                    
                        the_str += "the Env Variable %s" % (self._env_var)
                        add_nor += 1
                    
                    if self._conf_group is not None:
                        if add_nor > 0:
                            the_str += ", nor "
                        
                        the_str += "the Conf Group:[%s] and Property=%s" % (self._conf_group, self._conf_property)
                        add_nor += 1
                        
                    if add_nor == 0:
                        the_str += " any defined commandline argument, nor any env variable or"\
                                   " Conf group and properties. They are all None, fatal error"
                    else:
                        the_str += ". One of them should be defined"
                    
                    raise ResourceError(the_str)
    
        return val
   
    def _get(self, conv):
        """
           Private _get method used to convert to the right expected type (int,float or boolean).
           Strongly inspired by ConfigParser.py
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return conv(self.get_value())

    def get_value_as_int(self):
        """
           Return the value as an int
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        return self._get(int)

    def get_value_as_float(self):
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

    def get_value_as_boolean(self):
        """
           Return the value as a boolean
              
           Returns:
              value converted into the asked type
       
           Raises:
              exception ValueError if conversion issue
        """
        val = self.get_value()
        if val.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % val
        return self._boolean_states[val.lower()]

class MockConf(object):
    """
       MockConf Object that returns only defaults
    """
    def __init__(self, use_resource=True):
        """
           default constructor
        """
        pass
    
    @classmethod
    def get(cls, section, option, default=None, fail_if_missing=False): #pylint: disable=W0613
        """ get one option from a section.
        """
        return default
    
    @classmethod
    def print_content(cls, substitute_values = True):#pylint: disable=W0613
        """ print all the options variables substituted.
        
            :param a_substitue_vals: bool for substituting values
            :returns: the string containing all sections and variables
        """
        raise exceptions.Error("Not implemented in MockupConf")            

    @classmethod
    def items(cls, section):#pylint: disable=W0613
        """ return all items from a section. Items is a list of tuples (option,value)
            
            Args:
               section. The section where to find the option
               
            Returns: a list of tuples (option,value)
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
        raise exceptions.Error("Not implemented in MockupConf") 
  
    @classmethod
    def getint(cls, section, option, default=0, fail_if_missing=False):#pylint: disable=W0613
        """Return the int value of the option.
        Default value is 0, None value can't be used as default value"""
        return default

    @classmethod
    def getfloat(cls, section, option, default=0, fail_if_missing=False):#pylint: disable=W0613
        """Return the float value of the option. 
        Default value is 0, None value can't be used as default value"""
        return default

    @classmethod
    def getboolean(cls, section, option, default=False, fail_if_missing=False):#pylint: disable=W0613
        """get bool value """
        return default
    
    @classmethod
    def get_list(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ get a list of string, int  """
        return default
    
    @classmethod
    def getlist(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ Deprecated, use get_list instead"""
        return cls.get_list(section, option, default, fail_if_missing)

    @classmethod
    def getdict(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ Deprecated, use get_dict instead"""
        return cls.get_dict(section, option, default, fail_if_missing)
        
    
    @classmethod
    def get_dict(cls, section, option, default=None, fail_if_missing=False):#pylint: disable=W0613
        """ get a dict """
        return default
 
class Conf(object):
    """ Configuration Object with a several features:
    
         * get configuration info in different types
         * support for import
         * support for variables in configuration file
         * support for default values in all accessors
         * integrated with the resources object offering to get the configuration from an env var, a commandline option or the conf
         * to be done : support for blocs, list comprehension and dict comprehension, json 
         * to be done : define resources in the conf using the [Resource] group with A= { ENV:TESTVAR, CLI:--testvar, VAL:1.234 }
    
    """
    # command line and env resource stuff
    CLINAME = "--conf_file"
    ENVNAME = "CONF_FILE" 
    
    #class member
    _instance = None
    
    _CLIGROUP = "CLI"
    _ENVGROUP = "ENV"
    _MAX_INCLUDE_DEPTH = 10
    
    @classmethod
    def get_instance(cls):
        """ singleton method """
        if cls._instance == None:
            cls._instance = Conf()
        return cls._instance
    
    @classmethod
    def can_be_instanciated(cls):
        """Class method used by the Resource to check that the Conf can be instantiated. 
        
        These two objects have a special contract as they are strongly coupled. 
        A Resource can use the Conf to check for a Resource and the Conf uses a Resource to read Conf filepath.
        
        :returns: True if the Conf file has got a file.
           
        :except Error: Base Conf Error
        
        """
        #No conf info passed to the resource so the Resource will not look into the conf (to avoid recursive search)
        the_res = Resource(cls.CLINAME, cls.ENVNAME)
        
        filepath = the_res.get_value(a_raise_exception=False)
        
        if (filepath is not None) and os.path.exists(filepath):
            return True
        
        return False
            
    
    def __init__(self, use_resource=True):
        """
           Constructor
        """
        
        # create resource for the conf file
        self._conf_resource = Resource(Conf.CLINAME, Conf.ENVNAME)
        
        # list of sections
        self._sections = {}
        
        self._configuration_file_path = None
        
        # create config object 
        if use_resource:       
            self._load_config()

    def _load_config(self, a_file=None):
        """ _load the configuration file """
        try:  
            # get it from a Resource if not files are passed
            if a_file is None:
                a_file = self._conf_resource.get_value() 

            if a_file is None:
                raise exceptions.Error("Conf. Error, need a configuration file path")

            with codecs.open(a_file, 'r', 'utf-8') as f:
                self._read(f, a_file)

            # memorize conf file path
            self._configuration_file_path = a_file

        except Exception, exce:
            print "Can't read the config file %s" % a_file
            print "Current executing from dir = %s\n" % os.getcwd()
            raise exce

    def get_conf_file_path(self):
        """return conf_file_path"""
        return self._configuration_file_path if self._configuration_file_path != None else "unknown"
       
    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        # self._sections will never have [DEFAULT] in it
        return self._sections.keys()
    
    @classmethod
    def _get_defaults(cls, section, option, default, fail_if_missing):
        """ To manage defaults.
            Args:
               default. The default value to return if fail_if_missing is False
               fail_if_missing. Throw an exception when the option is not found and fail_if_missing is true
               
            Returns: default if fail_if_missing is False
        
            Raises:
               exception NoOptionError if fail_if_missing is True
        """
        if fail_if_missing:
            raise exceptions.Error(2, "No option %s in section %s" %(option, section))
        else:
            if default is not None:
                return str(default)
            else:
                return None
    
    def get(self, section, option, default=None, fail_if_missing=False):
        """ get one option from a section.
        
            return the default if it is not found and if fail_if_missing is False, otherwise return NoOptionError
          
            :param section: Section where to find the option
            :type  section: str
            :param option:  Option to get
            :param default: Default value to return if fail_if_missing is False
            :param fail_if_missing: Will throw an exception when the option is not found and fail_if_missing is true
               
            :returns: the option as a string
            
            :except NoOptionError: Raised only when fail_is_missing set to True
        
        """
        # all options are kept in lowercase
        opt = self.optionxform(option)
        
        if section not in self._sections:
            #check if it is a ENV section
            dummy = None
            if section == Conf._ENVGROUP:
                the_r = Resource(a_cli_argument=None, a_env_variable=opt)
                dummy = the_r.get_value()
            elif section == Conf._CLIGROUP:
                the_r = Resource(a_cli_argument=opt, a_env_variable=None)
                dummy = the_r.get_value()
            #return default if dummy is None otherwise return dummy
            return ((self._get_defaults(section, opt, default, fail_if_missing)) if dummy == None else dummy)
        elif opt in self._sections[section]:
            return self._replace_vars(self._sections[section][opt], "%s[%s]" % (section, option), - 1)
        else:
            return self._get_defaults(section, opt, default, fail_if_missing)
        
    
    def print_content(self, substitute_values = True):
        """ print all the options variables substituted.
        
            :param a_substitue_vals: bool for substituting values
            :returns: the string containing all sections and variables
        """
        
        result_str = ""
        
        for section_name in self._sections:
            result_str += "[%s]\n" % (section_name)
            section = self._sections[section_name]
            for option in section:
                if option != '__name__':
                    if substitute_values:
                        result_str += "%s = %s\n" % (option, self.get(section_name, option))
                    else:
                        result_str += "%s = %s\n" % (option, self._sections[section_name][option])
            
            result_str += "\n"
        
        return result_str
            

    def items(self, section):
        """ return all items from a section. Items is a list of tuples (option,value)
            
            Args:
               section. The section where to find the option
               
            Returns: a list of tuples (option,value)
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
        try:
            all_sec = self._sections[section]
            # make a copy
            a_copy = all_sec.copy()
            # remove __name__ from d
            if "__name__" in a_copy:
                del a_copy["__name__"]
                
            return a_copy.items()
        
        except KeyError:
            raise exceptions.NoSectionError(section)

    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        has_option = False
        if self.has_section(section):
            option = self.optionxform(option)
            has_option = (option in self._sections[section])
        return has_option
    
    def has_section(self, section):
        """Check for the existence of a given section in the configuration."""
        has_section = False
        if section in self._sections:
            has_section = True
        return has_section
        
    @classmethod
    def _get_closing_bracket_index(cls, index, the_str, location, lineno):
        """ private method used by _replace_vars to count the closing brackets.
            
            Args:
               index. The index from where to look for a closing bracket
               s. The string to parse
               group. group and options that are substituted. Mainly used to create a nice exception message
               option. option that is substituted. Mainly used to create a nice exception message
               
            Returns: the index of the found closing bracket
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
        
        tolook = the_str[index + 2:]
   
        opening_brack = 1
        closing_brack_index = index + 2
    
        i = 0
        for _ch in tolook:
            if _ch == ')':
                if opening_brack == 1:
                    return closing_brack_index
                else:
                    opening_brack -= 1
     
            elif _ch == '(':
                if tolook[i - 1] == '%':
                    opening_brack += 1
        
            # inc index
            closing_brack_index += 1
            i += 1
    
        raise exceptions.SubstitutionError(lineno, location, "Missing a closing bracket in %s" % (tolook))

    # very permissive regex
    _SUBSGROUPRE = re.compile(r"%\((?P<group>\w*)\[(?P<option>(.*))\]\)")
    
    def _replace_vars(self, a_str, location, lineno= - 1):
        """ private replacing all variables. A variable will be in the from of %(group[option]).
            Multiple variables are supported, ex /foo/%(group1[opt1])/%(group2[opt2])/bar
            Nested variables are also supported, ex /foo/%(group[%(group1[opt1]].
            Note that the group part cannot be substituted, only the option can. This is because of the Regular Expression _SUBSGROUPRE that accepts only words as values.
            
            Args:
               index. The index from where to look for a closing bracket
               s. The string to parse
               
            Returns: the final string with the replacements
        
            Raises:
               exception NoSectionError if the section cannot be found
        """
 
        toparse = a_str
    
        index = toparse.find("%(")
    
        # if found opening %( look for end bracket)
        if index >= 0:
            # look for closing brackets while counting openings one
            closing_brack_index = self._get_closing_bracket_index(index, a_str, location, lineno)
        
            #print "closing bracket %d"%(closing_brack_index)
            var   = toparse[index:closing_brack_index + 1]
            
            dummy = None
            
            matched = self._SUBSGROUPRE.match(var)
        
            if matched == None:
                raise exceptions.SubstitutionError(lineno, location, \
                                                   "Cannot match a group[option] in %s "\
                                                   "but found an opening bracket (. Malformated expression " \
                                                   % (var))
            else:
            
                # recursive calls
                group = self._replace_vars(matched.group('group'), location, - 1)
                option = self._replace_vars(matched.group('option'), location, - 1)
            
                try:
                    # if it is in ENVGROUP then check ENV variables with a Resource object
                    # if it is in CLIGROUP then check CLI argument with a Resource object
                    # otherwise check in standard groups
                    if group == Conf._ENVGROUP:
                        res = Resource(a_cli_argument=None, a_env_variable=option)
                        dummy = res.get_value()
                    elif group == Conf._CLIGROUP:
                        res = Resource(a_cli_argument=option, a_env_variable=None)
                        dummy = res.get_value()
                    else:
                        dummy = self._sections[group][self.optionxform(option)]
                except KeyError, _: #IGNORE:W0612
                    raise exceptions.SubstitutionError(lineno, location, "Property %s[%s] "\
                                                       "doesn't exist in this configuration file \n" \
                                                       % (group, option))
            
            toparse = toparse.replace(var, dummy)
            
            return self._replace_vars(toparse, location, - 1)    
        else:   
            return toparse 


    def _get(self, section, conv, option, default, fail_if_missing):
        """ Internal getter """
        return conv(self.get(section, option, default, fail_if_missing))

    def getint(self, section, option, default=0, fail_if_missing=False):
        """Return the int value of the option.
        Default value is 0, None value can't be used as default value"""
        return self._get(section, int, option, default, fail_if_missing)
    
    def get_int(self, section, option, default=0, fail_if_missing=False):
        """Return the int value of the option.
        Default value is 0, None value can't be used as default value"""
        return self._get(section, int, option, default, fail_if_missing)

    def getfloat(self, section, option, default=0, fail_if_missing=False):
        """Return the float value of the option. 
        Default value is 0, None value can't be used as default value"""
        return self._get(section, float, option, default, fail_if_missing)
    
    def get_float(self, section, option, default=0, fail_if_missing=False):
        """Return the float value of the option. 
        Default value is 0, None value can't be used as default value"""
        return self._get(section, float, option, default, fail_if_missing)

    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def getboolean(self, section, option, default=False, fail_if_missing=False):
        """getboolean value""" 
        val = self.get(section, option, default, fail_if_missing)
        if val.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % val
        return self._boolean_states[val.lower()]
    
    def get_boolean(self, section, option, default=False, fail_if_missing=False):
        """get_boolean value"""
        val = self.get(section, option, default, fail_if_missing)
        if val.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % val
        return self._boolean_states[val.lower()]
    
    def get_list(self, section, option, default=None, fail_if_missing=False):
        """ get a list of string, int  """
        
        val = self.get(section, option, default, fail_if_missing)
        
        # parse it and return an error if invalid
        try:
            compiler = struct_parser.Compiler()
            return compiler.compile_list(val)
        except struct_parser.CompilerError, err: 
            raise exceptions.Error(err.message)
    
    def getlist(self, section, option, default=None, fail_if_missing=False):
        """ Deprecated, use get_list instead"""
        return self.get_list(section, option, default, fail_if_missing)

    def getdict(self, section, option, default=None, fail_if_missing=False):
        """ Deprecated, use get_dict instead"""
        return self.get_dict(section, option, default, fail_if_missing)
        
    
    def get_dict(self, section, option, default=None, fail_if_missing=False):
        """ get a dict """
        
        val = self.get(section, option, default, fail_if_missing)
        
        # parse it and return an error if invalid
        try:
            compiler = struct_parser.Compiler()
            return compiler.compile_dict(val)
        except struct_parser.CompilerError, err: 
            raise exceptions.Error(err.message)
        
    @classmethod
    def optionxform(cls, optionstr):
        """optionxform"""
        return optionstr.lower()
    
    #
    # Regular expressions for parsing section headers and options.
    #
    SECTCRE = re.compile(
        r'\['                                 # [
        r'(?P<header>[^]]+)'                  # very permissive!
        r'\]'                                 # ]
        )
    OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*(?P<vi>[:=])\s*'                 # any number of space/tab,
                                              # followed by separator
                                              # (either : or =), followed
                                              # by any # space/tab
        r'(?P<value>.*)$'                     # everything up to eol
        )
            
    def _read_include(self, lineno, line, origin, depth):
        """_read_include"""      
        # Error if depth is MAX_INCLUDE_DEPTH 
        if depth >= Conf._MAX_INCLUDE_DEPTH:
            raise exceptions.IncludeError("Error. Cannot do more than %d nested includes."\
                                          " It is probably a mistake as you might have created a loop of includes" \
                                          % (Conf._MAX_INCLUDE_DEPTH))
        
        # remove %include from the path and we should have a path
        i = line.find('%include')
        
        #check if there is a < for including config files from a different format
        #position after include
        i = i + 8
        
        # include file with a specific reading module
        if line[i] == '<':
            dummy = line[i+1:].strip()
            f_i = dummy.find('>')
            if f_i == -1:
                raise exceptions.IncludeError("Error. > is missing in the include line no %s: %s."\
                                              " It should be %%include<mode:group_name> path" \
                                                   % (line, lineno), origin )
            else:
                group_name = None
                the_format     = dummy[:f_i].strip()
                
                the_list = the_format.split(':')
                if len(the_list) != 2 :
                    raise exceptions.IncludeError("Error. The mode and the group_name are not in the include line no %s: %s."\
                                                       " It should be %%include<mode:group_name> path" \
                                                       % (line, lineno), origin )
                else:
                    the_format, group_name = the_list
                    #strip the group name
                    group_name = group_name.strip()
                    
                path = dummy[f_i+1:].strip()
                
                # replace variables if there are any
                path = self._replace_vars(path, line, lineno)
                
                raise exceptions.IncludeError("External Module reading not enabled in this ConfHelper")
                #self._read_with_module(group_name, format, path, origin)
        else:
            # normal include   
            path = line[i:].strip() 
            
            # replace variables if there are any
            path = self._replace_vars(path, line, lineno)
            
            # check if file exits
            if not os.path.exists(path):
                raise exceptions.IncludeError("the config file to include %s does not exits" % (path), origin)
            else:
                # add include file and populate the section hash
                self._read(codecs.open(path, 'r', 'utf-8'), path, depth + 1)
                #self._read(open(path, 'r'), path, depth + 1)

    def _read(self, fpointer, fpname, depth=0): #pylint: disable=R0912
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        Depth for avoiding looping in the includes
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        err = None                                  # None, or an exception
        while True:
            line = fpointer.readline()
            if not line:
                break
            lineno = lineno + 1
            # include in this form %include
            if line.startswith('%include'):
                self._read_include(lineno, line, fpname, depth)
                continue
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                matched = self.SECTCRE.match(line)
                if matched:
                    sectname = matched.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    else:
                        cursect = {'__name__': sectname}
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise exceptions.MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    matched = self.OPTCRE.match(line)
                    if matched:
                        optname, vio, optval = matched.group('option', 'vi', 'value')
                        if vio in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos != - 1 and optval[pos - 1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not err:
                            err = exceptions.ParsingError(fpname)
                        err.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if err:
            raise err.get_error()

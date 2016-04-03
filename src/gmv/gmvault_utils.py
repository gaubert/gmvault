# -*- coding: utf-8 -*-
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
import os

import re
import datetime
import time
import calendar
import fnmatch
import functools

import StringIO
import sys
import traceback
import random 
import locale
import urllib
import chardet

import gmv.log_utils as log_utils
import gmv.conf.conf_helper
import gmv.gmvault_const as gmvault_const

LOG = log_utils.LoggerFactory.get_logger('gmvault_utils')

GMVAULT_VERSION = "1.9.1"

class memoized(object): #pylint: disable=C0103
    """Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            value = self.func(*args)
            self.cache[args] = value
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)
    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__
    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)
    
class Curry:
    """ Class used to implement the currification (functional programming technic) :
        Create a function from another one by instanciating some of its parameters.
        For example double = curry(operator.mul,2), res = double(4) = 8
    """
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()
        
    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            the_kw = self.kwargs.copy()
            the_kw.update(kwargs)
        else:
            the_kw = kwargs or self.kwargs
        return self.fun(*(self.pending + args), **the_kw) #pylint: disable=W0142



LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
DIGITS = '0123456789'

def make_password(minlength=8, maxlength=16):  
    """
       generate randomw password
    """
    length = random.randint(minlength, maxlength)
    letters = LETTERS + DIGITS 
    return ''.join([random.choice(letters) for _ in range(length)])  



def get_exception_traceback():
    """
            return the exception traceback (stack info and so on) in a string
        
            Args:
               None
               
            Returns:
               return a string that contains the exception traceback
        
            Raises:
               
    """
   
    the_file = StringIO.StringIO()
    exception_type, exception_value, exception_traceback = sys.exc_info() #IGNORE:W0702
    traceback.print_exception(exception_type, exception_value, exception_traceback, file = the_file)
    return the_file.getvalue()


MULTI_SPACES_PATTERN = r"\s{2,}"
MULTI_SPACES_RE = re.compile(MULTI_SPACES_PATTERN, flags=re.U) #to support unicode

def remove_consecutive_spaces_and_strip(a_str):
    """
       Supress consecutive spaces to replace them with a unique one.
       e.g "two  spaces" = "two spaces"
    """
    #return re.sub("\s{2,}", " ", a_str, flags=re.U).strip()
    return MULTI_SPACES_RE.sub(u" ", a_str).strip()


TIMER_SUFFIXES = ['y', 'w', 'd', 'h', 'm', 's']

class Timer(object):
    """
       Timer Class to mesure time.
       Possess also few time utilities
    """
    
 
    def __init__(self):
        
        self._start = None
        
    def start(self):
        """
           start the timer
        """
        self._start = time.time()
        
    def reset(self):
        """
           reset the timer to 0
        """
        self._start = time.time()
    
    def elapsed(self):
        """
           return elapsed time in sec
        """
        now = time.time()
        
        return int(round(now - self._start))
    
    def elapsed_ms(self):
        """
          return elapsed time up to micro second
        """
        return time.time() - self._start
    
    def elapsed_human_time(self, suffixes=TIMER_SUFFIXES, add_s=False, separator=' '):#pylint:disable=W0102
        """
        Takes an amount of seconds and turns it into a human-readable amount of time.
        """
        seconds = self.elapsed()
        
        return self.seconds_to_human_time(seconds, suffixes, add_s, separator)

    @classmethod
    def estimate_time_left(cls, nb_elem_done, in_sec, still_to_be_done, in_human_time = True):
        """
           Stupid estimate. Use current time to estimate how long it will take
        """
        if in_human_time:
            return cls.seconds_to_human_time(int(round(float(still_to_be_done * in_sec)/nb_elem_done)))
        else:
            return int(round(float(still_to_be_done * in_sec)/nb_elem_done))
    
    @classmethod
    def seconds_to_human_time(cls, seconds, suffixes=TIMER_SUFFIXES, add_s=False, separator=' '):#pylint:disable=W0102
        """
           convert seconds to human time
        """
        # the formatted time string to be returned
        the_time = []
        
        # the pieces of time to iterate over (days, hours, minutes, etc)
        # - the first piece in each tuple is the suffix (d, h, w)
        # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
        parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
              (suffixes[1], 60 * 60 * 24 * 7),
              (suffixes[2], 60 * 60 * 24),
              (suffixes[3], 60 * 60),
              (suffixes[4], 60),
              (suffixes[5], 1)]
        
        if seconds < 1: #less than a second case
            return "less than a second"
        
        # for each time piece, grab the value and remaining seconds, and add it to
        # the time string
        for suffix, length in parts:
            value = seconds / length
            if value > 0:
                seconds = seconds % length
                the_time.append('%s%s' % (str(value),
                               (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
            if seconds < 1:
                break
        
        return separator.join(the_time)

ZERO = datetime.timedelta(0) 
# A UTC class.    
class UTC(datetime.tzinfo):    
    """UTC Timezone"""    
    
    def utcoffset(self, a_dt): #pylint: disable=W0613
        ''' return utcoffset '''  
        return ZERO    
    
    def tzname(self, a_dt): #pylint: disable=W0613
        ''' return tzname '''    
        return "UTC"    
        
    def dst(self, a_dt): #pylint: disable=W0613 
        ''' return dst '''      
        return ZERO  

# pylint: enable-msg=W0613    
UTC_TZ = UTC()

def get_ym_from_datetime(a_datetime):
    """
       return year month from datetime
    """
    if a_datetime:
        return a_datetime.strftime('%Y-%m')
    
    return None

MONTH_CONV = { 1: 'Jan', 4: 'Apr', 6: 'Jun', 7: 'Jul', 10: 'Oct' , 12: 'Dec',
               2: 'Feb', 5: 'May', 8: 'Aug', 9: 'Sep', 11: 'Nov',
               3: 'Mar'}

REVERSE_MONTH_CONV = { 'Jan' : 1, 'Apr' : 4, 'Jun' : 6, 'Jul': 7, 'Oct': 10 , 'Dec':12,
                   'Feb' : 2, 'May' : 5, 'Aug' : 8, 'Sep': 9, 'Nov': 11,
                   'Mar' : 3}


MONTH_YEAR_PATTERN = r'(?P<year>(18|19|[2-5][0-9])\d\d)[-/.](?P<month>(0[1-9]|1[012]|[1-9]))'
MONTH_YEAR_RE = re.compile(MONTH_YEAR_PATTERN)

def compare_yymm_dir(first, second):
    """
       Compare directory names in the form of Year-Month
       Return 1 if first > second
              0 if equal
              -1 if second > first
    """
    
    matched = MONTH_YEAR_RE.match(first)
    
    if matched:
        first_year  = int(matched.group('year'))
        first_month = int(matched.group('month'))
        
        first_val   = (first_year * 1000) + first_month
    else:
        raise Exception("Invalid Year-Month expression (%s). Please correct it to be yyyy-mm" % (first))
        
    matched = MONTH_YEAR_RE.match(second)
    
    if matched:
        second_year  = int(matched.group('year'))
        second_month = int(matched.group('month'))
        
        second_val   = (second_year * 1000) + second_month
    else:
        raise Exception("Invalid Year-Month expression (%s). Please correct it" % (second))
    
    if first_val > second_val:
        return 1
    elif first_val == second_val:
        return 0
    else:
        return -1
    
def cmp_to_key(mycmp):
    """
        Taken from functools. Not in all python versions so had to redefine it
        Convert a cmp= function into a key= function
    """
    class Key(object): #pylint: disable=R0903
        """Key class"""
        def __init__(self, obj, *args): #pylint: disable=W0613
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
        def __hash__(self):
            raise TypeError('hash not implemented')
    return Key
    
def get_all_dirs_posterior_to(a_dir, dirs):
    """
           get all directories posterior
    """
    #sort the passed dirs list and return all dirs posterior to a_dir
         
    return [ name for name in sorted(dirs, key=cmp_to_key(compare_yymm_dir))\
             if compare_yymm_dir(a_dir, name) <= 0 ]

def get_all_dirs_under(root_dir, ignored_dirs = []):#pylint:disable=W0102
    """
       Get all directory names under (1 level only) the root dir
       params:
          root_dir   : the dir to look under
          ignored_dir: ignore the dir if it is in this list of dirnames 
    """
    return [ name for name in os.listdir(root_dir) \
             if ( os.path.isdir(os.path.join(root_dir, name)) \
                and (name not in ignored_dirs) ) ]

def datetime2imapdate(a_datetime):
    """
       Transfrom in date format for IMAP Request
    """
    if a_datetime:
        
        month = MONTH_CONV[a_datetime.month]
        
        pattern = '%%d-%s-%%Y' % (month) 
        
        return a_datetime.strftime(pattern)
    

def e2datetime(a_epoch):
    """
        convert epoch time in datetime

            Args:
               a_epoch: the epoch time to convert

            Returns: a datetime
    """

    #utcfromtimestamp is not working properly with a decimals.
    # use floor to create the datetime
#    decim = decimal.Decimal('%s' % (a_epoch)).quantize(decimal.Decimal('.001'), rounding=decimal.ROUND_DOWN)

    new_date = datetime.datetime.utcfromtimestamp(a_epoch)

    return new_date

def get_utcnow_epoch():
    return datetime2e(datetime.datetime.utcnow())

def datetime2e(a_date):
    """
        convert datetime in epoch
        Beware the datetime as to be in UTC otherwise you might have some surprises
            Args:
               a_date: the datertime to convert

            Returns: a epoch time
    """
    return calendar.timegm(a_date.timetuple())

def contains_any(string, char_set):
    """Check whether 'string' contains ANY of the chars in 'set'"""
    return 1 in [c in string for c in char_set]

def makedirs(a_path):
    """ my own version of makedir """
    
    if os.path.isdir(a_path):
        # it already exists so return
        return
    elif os.path.isfile(a_path):
        raise OSError("a file with the same name as the desired dir, '%s', already exists."%(a_path))

    os.makedirs(a_path)

def __rmgeneric(path, __func__):
    """ private function that is part of delete_all_under """
    try:
        __func__(path)
        #print 'Removed ', path
    except OSError, (_, strerror): #IGNORE:W0612
        print """Error removing %(path)s, %(error)s """ % {'path' : path, 'error': strerror }
            
def delete_all_under(path, delete_top_dir = False):
    """ delete all files and directories under path """

    if not os.path.isdir(path):
        return
    
    files = os.listdir(path)

    for the_f in files:
        fullpath = os.path.join(path, the_f)
        if os.path.isfile(fullpath):
            new_f = os.remove
            __rmgeneric(fullpath, new_f)
        elif os.path.isdir(fullpath):
            delete_all_under(fullpath)
            new_f = os.rmdir
            __rmgeneric(fullpath, new_f)
    
    if delete_top_dir:
        os.rmdir(path)

def ordered_dirwalk(a_dir, a_file_wildcards='*', a_dir_ignore_list=(), sort_func=sorted):
    """
        Walk a directory tree, using a generator.
        This implementation returns only the files in all the subdirectories.
        Beware, this is a generator.
        Args:
        a_dir: A root directory from where to list
        a_wildcards: Filtering wildcards a la unix
    """

    sub_dirs = []
    for the_file in sort_func(os.listdir(a_dir)):
        fullpath = os.path.join(a_dir, the_file)
        if os.path.isdir(fullpath):
            sub_dirs.append(fullpath) #it is a sub_dir
        elif fnmatch.fnmatch(fullpath, a_file_wildcards):
            yield fullpath

    #iterate over sub_dirs
    for sub_dir in sort_func(sub_dirs):
        if os.path.basename(sub_dir) not in a_dir_ignore_list:
            for p_elem in ordered_dirwalk(sub_dir, a_file_wildcards):
                yield p_elem 
        else:
            LOG.debug("Ignore subdir %s" % sub_dir)

def dirwalk(a_dir, a_wildcards='*'):
    """
       return all files and dirs in a directory
    """
    for root, _, files in os.walk(a_dir):
        for the_file in files:
            if fnmatch.fnmatch(the_file, a_wildcards):
                yield os.path.join(root, the_file)  

def ascii_hex(a_str):
    """
       transform any string in hexa values
    """
    new_str = ""
    for the_char in a_str:
        new_str += "%s=hex[%s]," % (the_char, hex(ord(the_char)))
    return new_str

def profile_this(fn):
    """ profiling decorator """
    def profiled_fn(*args, **kwargs):
        import cProfile
        fpath = fn.__name__ + ".profile"
        prof  = cProfile.Profile()
        ret   = prof.runcall(fn, *args, **kwargs)
        prof.dump_stats(fpath)
        return ret
    return profiled_fn

DEFAULT_ENC_LIST = ['ascii','iso-8859-1','iso-8859-2','windows-1250','windows-1252','utf-8']

class GuessEncoding(Exception): pass    # Guess encoding error

def guess_encoding(byte_str, use_encoding_list=True):
    """
       byte_str: byte string
       use_encoding_list: To try or not to brut force guess with the predefined list
       Try to guess the encoding of byte_str
       if encoding cannot be found return utf-8
    """
    encoding = None

    if type(byte_str) == type(unicode()):
       raise GuessEncoding("Error. The passed string is a unicode string and not a byte string")

    if use_encoding_list:
        encoding_list = get_conf_defaults().get('Localisation', 'encoding_guess_list', DEFAULT_ENC_LIST)
        for enc in encoding_list:
           try:
              unicode(byte_str ,enc,"strict")
              encoding = enc
           except:
              pass
           else:
              break

    if not encoding:
       #detect encoding with chardet
       enc = chardet.detect(byte_str)
       if enc and enc.get("encoding") != None:
          encoding = enc.get("encoding")
       else:
          LOG.debug("Force encoding to utf-8")
          encoding = "utf-8"

    return encoding


def convert_to_unicode(a_str):
    """
    Convert a string to unicode (except terminal strings)
    :param a_str:
    :return: unicode string
    """
    encoding = None

    #if email encoding is forced no more guessing
    email_encoding = get_conf_defaults().get('Localisation', 'email_encoding', None)

    try:
        if email_encoding:
            encoding = email_encoding
        else:
            LOG.debug("Guess encoding")
            #guess encoding based on the beginning of the string up to 128K character
            encoding = guess_encoding(a_str[:20000], use_encoding_list = False)

        LOG.debug("Convert to %s" % (encoding))
        u_str = unicode(a_str, encoding = encoding) #convert to unicode with given encoding
    except Exception, e:
        LOG.debug("Exception: %s" % (e))
        LOG.info("Warning: Guessed encoding = (%s). Ignore those characters" % (encoding if encoding else "Not defined"))
        #try utf-8
        u_str = unicode(a_str, encoding="utf-8", errors='replace')

    return u_str

def convert_argv_to_unicode(a_str):
    """
       Convert command line individual arguments (argv to unicode)
    """
    #if str is already unicode do nothing and return the str
    if type(a_str) == type(unicode()):
        return a_str

    #encoding can be forced from conf
    terminal_encoding = get_conf_defaults().get('Localisation', 'terminal_encoding', None)
    if not terminal_encoding:
        terminal_encoding = locale.getpreferredencoding() #use it to find the encoding for text terminal
        LOG.debug("encoding found with locale.getpreferredencoding()")
        if not terminal_encoding:
            loc = locale.getdefaultlocale() #try to get defaultlocale()
            if loc and len(loc) == 2:
                LOG.debug("encoding found with locale.getdefaultlocale()")
                terminal_encoding = loc[1]
            else:
                LOG.debug("Cannot Terminal encoding using locale.getpreferredencoding() and locale.getdefaultlocale(), loc = %s. Use chardet to try guessing the encoding." % (loc if loc else "None"))
                terminal_encoding = guess_encoding(a_str)
    else:
       LOG.debug("Use terminal encoding forced from the configuration file.") 
    try:
       LOG.debug("terminal encoding = %s." % (terminal_encoding))
       #decode byte string to unicode and fails in case of error
       u_str = a_str.decode(terminal_encoding)
       LOG.debug("unicode_escape val = %s." % (u_str.encode('unicode_escape')))
       LOG.debug("raw unicode     = %s." % (u_str))
    except Exception, err: 
       LOG.error(err)
       get_exception_traceback()
       LOG.info("Convertion of %s from %s to a unicode failed. Will now convert to unicode using utf-8 encoding and ignoring errors (non utf-8 characters will be eaten)." % (a_str, terminal_encoding))
       LOG.info("Please set properly the Terminal encoding or use the [Localisation]:terminal_encoding property to set it.")
       u_str = unicode(a_str, encoding='utf-8', errors='ignore')

    return u_str

@memoized
def get_home_dir_path():
    """
       Get the gmvault dir
    """
    gmvault_dir = os.getenv("GMVAULT_DIR", None)
    
    # check by default in user[HOME]
    if not gmvault_dir:
        LOG.debug("no ENV variable $GMVAULT_DIR defined. Set by default $GMVAULT_DIR to $HOME/.gmvault (%s/.gmvault)" \
                  % (os.getenv("HOME",".")))
        gmvault_dir = "%s/.gmvault" % (os.getenv("HOME", "."))
    
    #create dir if not there
    makedirs(gmvault_dir)
    
    return gmvault_dir

CONF_FILE = "gmvault_defaults.conf"

@memoized
def get_conf_defaults():
    """
       Return the conf object containing the defaults stored in HOME/gmvault_defaults.conf
       Beware it is memoized
    """
    filepath = get_conf_filepath()
    
    if filepath:
        
        os.environ[gmv.conf.conf_helper.Conf.ENVNAME] = filepath
    
        the_cf = gmv.conf.conf_helper.Conf.get_instance()
    
        LOG.debug("Load defaults from %s" % (filepath))
        
        return the_cf
    else:
        return gmv.conf.conf_helper.MockConf() #retrun MockObject that will play defaults
    
#VERSION DETECTION PATTERN
VERSION_PATTERN  = r'\s*conf_version=\s*(?P<version>\S*)\s*'
VERSION_RE  = re.compile(VERSION_PATTERN)

#list of version conf to not overwrite with the next
VERSIONS_TO_PRESERVE = [ '1.9' ]

def _get_version_from_conf(home_conf_file):
    """
       Check if the config file need to be replaced because it comes from an older version
    """
    #check version
    ver = None
    with open(home_conf_file) as curr_fd:
        for line in curr_fd:
            line = line.strip()
            matched = VERSION_RE.match(line)
            if matched:
                ver = matched.group('version')
                return ver.strip()
    
    return ver

def _create_default_conf_file(home_conf_file):
    """
       Write on disk the default file
    """
    LOG.critical("Create defaults in %s. Please touch this file only if you know what to do." % home_conf_file)
    try:
        with open(home_conf_file, "w+") as f:
            f.write(gmvault_const.DEFAULT_CONF_FILE)
        return home_conf_file
    except Exception, err:
        #catch all error and let run gmvault with defaults if needed
        LOG.critical("Ignore Error when trying to create conf file for defaults in %s:\n%s.\n" % (get_home_dir_path(), err))
        LOG.debug("=== Exception traceback ===")
        LOG.debug(get_exception_traceback())
        LOG.debug("=== End of Exception traceback ===\n")
        #return default file instead

@memoized
def get_conf_filepath():
    """
       If default file is not present, generate it from scratch.
       If it cannot be created, then return None
    """
    home_conf_file = "%s/%s" % (get_home_dir_path(), CONF_FILE)
    
    if not os.path.exists(home_conf_file):
        return _create_default_conf_file(home_conf_file)
    else:
        # check if the conf file needs to be replaced
        version = _get_version_from_conf(home_conf_file)
        if version not in VERSIONS_TO_PRESERVE:
            LOG.debug("%s with version %s is too old, overwrite it with the latest file." \
                       % (home_conf_file, version))
            return _create_default_conf_file(home_conf_file)    
    
    return home_conf_file


def chunker(seq, size):
    """Returns the contents of `seq` in chunks of up to `size` items."""
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))


def escape_url(text):
  """
  Escape characters as expected in OAUTH 5.1
  :param text: the escaped url
  :return: escaped url
  """
  return urllib.quote(text, safe='~-._')


def unescape_url(text):
  """
  Unescaped characters when needed (see OAUTH 5.1)
  :param text:
  :return: unescaped url
  """
  return urllib.unquote(text)

def format_url_params(params):
  """
  Formats given parameters as URL query string.
  :param params: a python dict
  :return: A URL query string version of the given dict.
  """
  param_elements = []
  for param in sorted(params.iteritems(), key=lambda x: x[0]):
    param_elements.append('%s=%s' % (param[0], escape_url(param[1])))
  return '&'.join(param_elements)

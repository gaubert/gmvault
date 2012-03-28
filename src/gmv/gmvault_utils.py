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

import log_utils 

LOG = log_utils.LoggerFactory.get_logger('gmvault_utils')

class memoized(object):
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
    
class curry:
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
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs
        return self.fun(*(self.pending + args), **kw) #IGNORE:W0142



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
    
    def elapsed(self):
        """
           return elapsed time in sec
        """
        now = time.time()
        
        return int(round(now - self._start))
    
    def elapsed_human_time(self, suffixes=['y','w','d','h','m','s'], add_s=False, separator=' '):
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
    def seconds_to_human_time(cls, seconds, suffixes=['y','w','d','h','m','s'], add_s=False, separator=' '):
        """
           convert seconds to human time
        """
        # the formatted time string to be returned
        time = []
        
        # the pieces of time to iterate over (days, hours, minutes, etc)
        # - the first piece in each tuple is the suffix (d, h, w)
        # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
        parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
              (suffixes[1], 60 * 60 * 24 * 7),
              (suffixes[2], 60 * 60 * 24),
              (suffixes[3], 60 * 60),
              (suffixes[4], 60),
              (suffixes[5], 1)]
        
        # for each time piece, grab the value and remaining seconds, and add it to
        # the time string
        for suffix, length in parts:
            value = seconds / length
            if value > 0:
                seconds = seconds % length
                time.append('%s%s' % (str(value),
                               (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
            if seconds < 1:
                break
        
        return separator.join(time)

ZERO = datetime.timedelta(0) 
# A UTC class.    
class UTC(datetime.tzinfo):    
    """UTC Timezone"""    
    
    def utcoffset(self, a_dt):  
        ''' return utcoffset '''  
        return ZERO    
    
    def tzname(self, a_dt):
        ''' return tzname '''    
        return "UTC"    
        
    def dst(self, a_dt):  
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
    class K(object):
        def __init__(self, obj, *args):
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
    return K
    
def get_all_directories_posterior_to(a_dir, dirs):
    """
           get all directories posterior
    """
    #sort the passed dirs list and return all dirs posterior to a_dir
         
    return [ name for name in sorted(dirs, key=cmp_to_key(compare_yymm_dir))\
             if compare_yymm_dir(a_dir, name) <= 0 ]

def get_all_dirs_under(root_dir):
    """
       Get all directory names under (1 level only) the root dir
    """
    return [ name for name in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, name)) ]

def datetime2imapdate(a_datetime):
    """
       Transfrom in date format for IMAP Request
    """
    if a_datetime:
        
        month = MONTH_CONV[a_datetime.month]
        
        pattern = '%%d-%s-%%Y' %(month) 
        
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

def datetime2e(a_date):
    """
        convert datetime in epoch
        Beware the datetime as to be in UTC otherwise you might have some surprises
            Args:
               a_date: the datertime to convert

            Returns: a epoch time
    """
    return calendar.timegm(a_date.timetuple())

def makedirs(aPath):
    """ my own version of makedir """
    
    if os.path.isdir(aPath):
        # it already exists so return
        return
    elif os.path.isfile(aPath):
        raise OSError("a file with the same name as the desired dir, '%s', already exists."%(aPath))

    os.makedirs(aPath)

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

    for x in files:
        fullpath = os.path.join(path, x)
        if os.path.isfile(fullpath):
            f = os.remove
            __rmgeneric(fullpath, f)
        elif os.path.isdir(fullpath):
            delete_all_under(fullpath)
            f = os.rmdir
            __rmgeneric(fullpath, f)
    
    if delete_top_dir:
        os.rmdir(path)
        
def ordered_dirwalk(a_dir, a_wildcards= '*', sort_func = sorted):
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
        elif fnmatch.fnmatch(fullpath, a_wildcards):
            yield fullpath
        
    #iterate over sub_dirs
    for sub_dir in sub_dirs:
        for p_elem in ordered_dirwalk(sub_dir, a_wildcards):
            yield p_elem 
  
def dirwalk(a_dir, a_wildcards= '*'):
    """
       return all files and dirs in a directory
    """
    for root, _, files in os.walk(a_dir):
        for the_file in files:
            if fnmatch.fnmatch(the_file, a_wildcards):
                yield os.path.join(root, the_file)  


@memoized
def get_home_dir_path():
    """
       Get the Home dir
    """
    gmvault_dir = os.getenv("GMVAULT_DIR", None)
    
    # check by default in user[HOME]
    if not gmvault_dir:
        LOG.debug("no ENV variable $GMVAULT_DIR defined. Set by default $GMVAULT_DIR to $HOME/.gmvault (%s/.gmvault)" % (os.getenv("HOME",".")))
        gmvault_dir = "%s/.gmvault" % (os.getenv("HOME", "."))
    
    #create dir if not there
    makedirs(gmvault_dir)
    
    return gmvault_dir
            
if __name__ == '__main__':
   
    timer = Timer()
    
    timer.start()
    
    import time
    time.sleep(3)
    
    print(timer.elapsed())

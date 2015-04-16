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
# exception classes
class Error(Exception):
    """Base class for Conf exceptions."""

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__
    
class NoOptionError(Error):
    """A requested option was not found."""

    def __init__(self, option, section):
        Error.__init__(self, "No option %r in section: %r" % 
                       (option, section))
        self.option = option
        self.section = section

class NoSectionError(Error):
    """Raised when no section matches a requested option."""

    def __init__(self, section):
        Error.__init__(self, 'No section: %r' % (section,))
        self.section = section

class SubstitutionError(Error):
    """Base class for substitution-related exceptions."""

    def __init__(self, lineno, location, msg):
        Error.__init__(self, 'SubstitutionError on line %d: %s. %s' \
                       % (lineno, location, msg) if lineno != - 1 \
                       else 'SubstitutionError in %s. %s' % (lineno, location))
        
class IncludeError(Error):
    """ Raised when an include command is incorrect """
    
    def __init__(self, msg, origin):
        Error.__init__(self, msg)
        self.origin = origin
        self.errors = []


class ParsingError(Error):
    """Raised when a configuration file does not follow legal syntax."""
    def __init__(self, filename):
        Error.__init__(self, 'File contains parsing errors: %s' % filename)
        self.filename = filename
        self.errors = []

    def append(self, lineno, line):
        """ add error message """
        self.errors.append((lineno, line))
        self.message += '\n\t[line %2d]: %s' % (lineno, line)
        
    def get_error(self):
        """ return the error """
        return self
        
class MissingSectionHeaderError(ParsingError):
    """Raised when a key-value pair is found before any section header."""

    def __init__(self, filename, lineno, line):
        ParsingError.__init__(
            self,
            'File contains no section headers.\nfile: %s, line: %d\n%r' % 
            (filename, lineno, line))
        self.filename = filename
        self.lineno = lineno
        self.line = line

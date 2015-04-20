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
import tokenize
import token
import StringIO

class TokenizerError(Exception):
    """Base class for All exceptions"""

    def __init__(self, a_msg, a_line=None, a_col=None):
        
        self._line = a_line
        self._col  = a_col
        
        if self._line == None and self._col == None:
            extra = "" 
        else:
            extra = "(line=%s,col=%s)" % (self._line, self._col)
        
        super(TokenizerError, self).__init__("%s %s." % (a_msg, extra))
    

class Token(object):
    """ Token class """
    def __init__(self, a_type, num, value, begin, end, parsed_line):
        
        self._type  = a_type
        self._num   = num
        self._value = value
        self._begin = begin
        self._end   = end
        self._parsed_line  = parsed_line
    
    @property
    def type(self):
        """ Return the token type """
        return self._type

    @property
    def num(self):
        """ Return the token type num """
        return self._num

    @property
    def value(self):
        """ Return the token value """
        return self._value
    
    @property
    def begin(self):
        """ Return the token begin """
        return self._begin
    
    @property
    def end(self):
        """ Return the token end """
        return self._end
    
    @property
    def parsed_line(self):
        """ Return the token line """
        return self._parsed_line
    
    def __repr__(self):
        return "[type,num]=[%s,%s],value=[%s], parsed line=%s,[begin index,end index]=[%s,%s]" \
               % (self._type, self._num, self._value, self._parsed_line, self._begin, self._end)
         

class Tokenizer(object):
    """ 
        Create tokens for parsing the grammar. 
        This class is a wrapper around the python tokenizer adapt to the DSL that is going to be used.
    """    
    def __init__(self):
        """ constructor """
        # list of tokens
        self._tokens  = []
        
        self._index   = 0
        
        self._current = None
       
    def tokenize(self, a_program, a_eatable_token_types = ()):
        """ parse the expression.
            By default the parser eats space but some extra tokens by have to be eaten
        
            Args:
               a_expression: the expression to parser
               
            Returns:
               return dict containing the different parts of the request (spectrum, ....)
        
            Raises:
               exception TokenizerError if the syntax of the aString string is incorrect
        """
        g_info = tokenize.generate_tokens(StringIO.StringIO(a_program).readline)   # tokenize the string
        
        for toknum, tokval, tokbeg, tokend, tokline  in g_info:
            if token.tok_name[toknum] not in a_eatable_token_types:
                self._tokens.append(Token(token.tok_name[toknum], toknum, tokval, tokbeg, tokend, tokline))
            
        
            
    def __iter__(self):
        """ iterator implemented with a generator.
        """
        for tok in self._tokens:
            self._current = tok
            yield tok
        
    def next(self):
        """ get next token.
          
            Returns:
               return next token
        """
        
        self._current = self._tokens[self._index]
        self._index += 1
        return self._current
    
    def has_next(self):
        """ check it there are more tokens to consume.
        
            Returns:
               return True if more tokens to consume False otherwise
        """
        return self._index < len(self._tokens)
    
    def current_token(self):
        """ return the latest consumed token.
        
            Returns:
               return the latest consumerd token
        """
        return self._current
    
    def consume_token(self, what):
        """ consume the next token if it is what """
        if self._current.value != what :
            raise TokenizerError("Expected '%s' but instead found '%s'" % (what, self._current.value))
        else:
            return self.next()
        
    def consume_while_next_token_is_in(self, a_token_types_list):
        """
           Consume the next tokens as long as they have one of the passed types.
           This means that at least one token with one of the passed types needs to be matched.
           
           Args:
               a_token_types_list: the token types to consume
            
           Returns:
               return the next non matching token 
        """
        
        self.consume_next_tokens(a_token_types_list)
        
        while True:
        
            tok = self.next()
        
            if tok.type not in a_token_types_list:
                return tok
    
    def consume_while_current_token_is_in(self, a_token_types_list): #pylint: disable=C0103
        """
           Consume the tokens starting from the current token as long as they have one of the passed types.
           It is a classical token eater. It eats tokens as long as they are the specified type
           
           Args:
               a_token_types_list: the token types to consume
            
           Returns:
               return the next non matching token 
        """
        
        tok = self.current_token()
        
        while tok.type in a_token_types_list:
            tok = self.next()
        
        return tok
    
    def consume_next_tokens(self, a_token_types_list):
        """
           Consume one of the next token types given in the list and check that it is the expected type otherwise send an exception
            
           Args:
               a_tokens_list:  the token types to list 
               
           Returns:
               return next token 
           
           Raises:
               exception  BadTokenError if a Token Type that is not in a_token_types_list is found
        """
        
        tok = self.next()
        
        if tok.type not in a_token_types_list:
            raise TokenizerError("Expected '%s' but instead found '%s'" % (a_token_types_list, tok))
        else:
            return tok
    
    def advance(self, inc=1):
        """ return the next + inc token but do not consume it.
            Useful to check future tokens.
        
            Args:
               a_expression: increment + 1 is the default (just look one step forward)
               
            Returns:
               return lookhead token
        """
        return self._tokens[self._index-1 + inc]
    
class CompilerError(Exception):
    """Base class for All exceptions"""

    def __init__(self, a_msg, a_line=None, a_col=None):
        
        self._line = a_line
        self._col  = a_col
        
        msg = ''
        
        if self._line == None and self._col == None:
            extra = ""
            msg = "%s." % (a_msg) 
        else:
            extra = "(line=%s,col=%s)" % (self._line, self._col)
            msg = "%s %s." % (a_msg, extra)
        
        super(CompilerError, self).__init__(msg)
    
class Compiler(object):
    """ compile some python structures
    """
    
    def __init__(self):
        """ constructor """
        
        #default tokens to ignore
        self._tokens_to_ignore = ('INDENT', 'DEDENT', 'NEWLINE', 'NL')
    
    def compile_list(self, a_to_compile_str):
        """ compile a list object """
        
        try:
            tokenizer = Tokenizer()
            tokenizer.tokenize(a_to_compile_str, self._tokens_to_ignore)
        except tokenize.TokenError, err:
            
            #translate this error into something understandable. 
            #It is because the bloody tokenizer counts the brackets
            if err.args[0] == "EOF in multi-line statement":
                raise CompilerError("Expression \"%s\" cannot be converted as a list" % (a_to_compile_str))
            else:
                raise CompilerError(err)
            
            print("Err = %s\n" % (err))
        
        tokenizer.next()
        
        return self._compile_list(tokenizer)
    
    def compile_dict(self, a_to_compile_str):
        """ compile a dict object """
        
        try:
            tokenizer = Tokenizer()
            tokenizer.tokenize(a_to_compile_str, self._tokens_to_ignore)
        except tokenize.TokenError, err:
            
            #translate this error into something understandable. 
            #It is because the bloody tokenizer counts the brackets
            if err.args[0] == "EOF in multi-line statement":
                raise CompilerError("Expression \"%s\" cannot be converted as a dict" % (a_to_compile_str))
            else:
                raise CompilerError(err)
            
            print("Err = %s\n" % (err))
        
        tokenizer.next()
        
        return self._compile_dict(tokenizer)

    def _compile_dict(self, a_tokenizer):
        """ internal method for compiling a dict struct """
        result = {}
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type != 'ENDMARKER':
            
            #look for an open bracket
            if the_token.type == 'OP' and the_token.value == '{':
               
                the_token = a_tokenizer.next()
                
                while True:
                   
                    if the_token.type == 'OP' and the_token.value == '}':
                        return result
                    else:
                        # get key values
                        (key, val) = self._compile_key_value(a_tokenizer)

                        result[key] = val  
                    
                    the_token = a_tokenizer.current_token()
                                   
            else:
                raise CompilerError("Unsupported token (type: %s, value : %s)" \
                                    % (the_token.type, the_token.value), the_token.begin[0], the_token.begin[1])
            
        #we should never reach that point (compilation error)
        raise CompilerError("End of line reached without finding a list. The line [%s] cannot be transformed as a list" \
                            % (the_token.parsed_line))
        
    def _compile_key_value(self, a_tokenizer):
        """ look for the pair key value component of a dict """
        
        the_token = a_tokenizer.current_token()
        
        key = None
        val = None
        
        # get key
        if the_token.type in ('STRING', 'NUMBER', 'NAME'):
            
            #next the_token is in _compile_litteral
            key = self._compile_litteral(a_tokenizer)
            
            the_token = a_tokenizer.current_token()
            
        else:
            raise CompilerError("unexpected token (type: %s, value : %s)" \
                                % (the_token.type, the_token.value), \
                                the_token.begin[0], the_token.begin[1])  
        
        #should have a comma now
        if the_token.type != 'OP' and the_token.value != ':':
            raise CompilerError("Expected a token (type:OP, value: :) but instead got (type: %s, value: %s)" \
                                % (the_token.type, the_token.value), the_token.begin[0], the_token.begin[1])
        else:
            #eat it
            the_token = a_tokenizer.next()
        
        #get value
        # it can be a
        if the_token.type in ('STRING', 'NUMBER', 'NAME'):
            #next the_token is in _compile_litteral
            val = self._compile_litteral(a_tokenizer)
            
            the_token = a_tokenizer.current_token()
        
        #check for a list
        elif the_token.value == '[' and the_token.type == 'OP':
            
            # look for a list
            val = self._compile_list(a_tokenizer)
            
            # positioning to the next token
            the_token = a_tokenizer.next()
            
        elif the_token.value == '{' and the_token.type == 'OP':
            
            # look for a dict
            val = self._compile_dict(a_tokenizer)
            
            # positioning to the next token
            the_token = a_tokenizer.next()
        
        elif the_token.value == '(' and the_token.type == 'OP':
            
            # look for a dict
            val = self._compile_tuple(a_tokenizer)
            
            # positioning to the next token
            the_token = a_tokenizer.next()
            
        else:
            raise CompilerError("unexpected token (type: %s, value : %s)" \
                                % (the_token.type, the_token.value), the_token.begin[0], \
                                the_token.begin[1])  
        
        #if we have a comma then eat it as it means that we will have more than one values
        if the_token.type == 'OP' and the_token.value == ',':
            the_token = a_tokenizer.next() 
            
        return (key, val)               
        
        
    def _compile_litteral(self, a_tokenizer):
        """ compile key. A key can be a NAME, STRING or NUMBER """
        
        val   = None
        
        dummy = None
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type not in ('OP', 'ENDMARKER'):
            if the_token.type == 'STRING':  
                #check if the string is unicode
                if len(the_token.value) >= 3 and the_token.value[:2] == "u'":
                    #unicode string
                    #dummy = unicode(the_token.value[2:-1], 'utf_8') #decode from utf-8 encoding not necessary if read full utf-8 file
                    dummy = unicode(the_token.value[2:-1])
                else:
                    #ascii string
                    # the value contains the quote or double quotes so remove them always
                    dummy = the_token.value[1:-1]
                    
            elif the_token.type == 'NAME':
                # intepret all non quoted names as a string
                dummy = the_token.value
                    
            elif the_token.type == 'NUMBER':  
                     
                dummy = self._create_number(the_token.value)
                 
            else:
                raise CompilerError("unexpected token (type: %s, value : %s)" \
                                    % (the_token.type, the_token.value), \
                                    the_token.begin[0], the_token.begin[1])
           
            #if val is not None, it has to be a string
            if val:
                val = '%s %s' % (str(val), str(dummy))
            else:
                val = dummy
            
            the_token = a_tokenizer.next()
            
        return val
    
    
    def _compile_tuple(self, a_tokenizer):
        """ process tuple structure """
        result = []
        
        open_bracket = 0
        # this is the mode without [ & ] operator : 1,2,3,4
        simple_list_mode = 0
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type != 'ENDMARKER':
            #look for an open bracket
            if the_token.value == '(' and the_token.type == 'OP':
                #first time we open a bracket and not in simple mode 
                if open_bracket == 0 and simple_list_mode == 0:
                    open_bracket += 1
                #recurse to create the imbricated list
                else:
                    result.append(self._compile_tuple(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '{' and the_token.type == 'OP':
               
                result.append(self._compile_dict(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '[' and the_token.type == 'OP':
               
                result.append(self._compile_list(a_tokenizer))
                    
                the_token = a_tokenizer.next()
                    
            elif the_token.type == 'OP' and the_token.value == ')':
                # end of list return result
                if open_bracket == 1:
                    return tuple(result)
                # cannot find a closing bracket and a simple list mode
                elif simple_list_mode == 1:
                    raise CompilerError("unexpected token (type: %s, value : %s)" \
                                        % (the_token.value, the_token.type), the_token.begin[0], \
                                        the_token.begin[1])
            # the comma case
            elif the_token.type == 'OP' and the_token.value == ',':
                # just eat it
                the_token = a_tokenizer.next()
                
            elif the_token.type in ('STRING', 'NUMBER', 'NAME'):
                
                # find values outside of a list 
                # this can be okay
                if open_bracket == 0:
                    simple_list_mode = 1
                    
                #next the_token is in _compile_litteral
                result.append(self._compile_litteral(a_tokenizer))
                
                the_token = a_tokenizer.current_token()
               
            else:
                raise CompilerError("Unsupported token (type: %s, value : %s)"\
                                    % (the_token.value, the_token.type), \
                                    the_token.begin[0], the_token.begin[1])
            
        
        # if we are in simple_list_mode return list else error
        if simple_list_mode == 1:
            return tuple(result)
            
        #we should never reach that point (compilation error)
        raise CompilerError("End of line reached without finding a list. The line [%s] cannot be transformed as a tuple" \
                            % (the_token.parsed_line))
    
    def _compile_list(self, a_tokenizer):
        """ process a list structure """
        result = []
        
        
        open_bracket = 0
        # this is the mode without [ & ] operator : 1,2,3,4
        simple_list_mode = 0
        
        the_token = a_tokenizer.current_token()
        
        while the_token.type != 'ENDMARKER':
            #look for an open bracket
            if the_token.value == '[' and the_token.type == 'OP':
                #first time we open a bracket and not in simple mode 
                if open_bracket == 0 and simple_list_mode == 0:
                    open_bracket += 1
                #recurse to create the imbricated list
                else:
                    result.append(self._compile_list(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '(' and the_token.type == 'OP':
               
                result.append(self._compile_tuple(a_tokenizer))
                    
                the_token = a_tokenizer.next()
            
            elif the_token.value == '{' and the_token.type == 'OP':
               
                result.append(self._compile_dict(a_tokenizer))
                    
                the_token = a_tokenizer.next()
                    
            elif the_token.type == 'OP' and the_token.value == ']':
                # end of list return result
                if open_bracket == 1:
                    return result
                # cannot find a closing bracket and a simple list mode
                elif simple_list_mode == 1:
                    raise CompilerError("unexpected token (type: %s, value : %s)" \
                                        % (the_token.value, the_token.type), the_token.begin[0], the_token.begin[1])
            # the comma case
            elif the_token.type == 'OP' and the_token.value == ',':
                # just eat it
                the_token = a_tokenizer.next()
                
            elif the_token.type in ('STRING', 'NUMBER', 'NAME'):
                
                # find values outside of a list 
                # this can be okay
                if open_bracket == 0:
                    simple_list_mode = 1
                    
                #next the_token is in _compile_litteral
                result.append(self._compile_litteral(a_tokenizer))
                
                the_token = a_tokenizer.current_token()
               
            else:
                raise CompilerError("Unsupported token (type: %s, value : %s)"\
                                    % (the_token.value, the_token.type), \
                                    the_token.begin[0], the_token.begin[1])
            
        
        # if we are in simple_list_mode return list else error
        if simple_list_mode == 1:
            return result
            
        #we should never reach that point (compilation error)
        raise CompilerError("End of line reached without finding a list. The line [%s] cannot be transformed as a list" \
                            % (the_token.parsed_line))
         
    @classmethod
    def _create_number(cls, a_number):
        """ depending on the value return a int or a float. 
            For the moment very simple: If there is . it is a float"""
        
        if a_number.find('.') > 0:
            return float(a_number)
        else:
            return int(a_number)

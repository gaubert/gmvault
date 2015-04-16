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
# unit tests part
import unittest
from gmv.conf.utils.struct_parser import Compiler, CompilerError

class TestParser(unittest.TestCase): #pylint: disable=R0904
    """ TestParser Class """
    
    def setUp(self): #pylint: disable=C0103
        pass
        
    def test_simple_list_test(self):
        """ a first simple test with space and indent, dedents to eat"""
        
        the_string = "         [ 'a',     1.435, 3 ]"
        
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, [ 'a', 1.435, 3])
    
    def test_negative_number_test(self):
        """ a negative number test """
        the_string = "         [ '-10.4',     1.435, 3 ]"
        
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, [ '-10.4', 1.435, 3])
    
    def test_imbricated_lists_test(self):
        """ multiple lists within lists """
        
        the_string = "[a,b, [1,2,3,4, [456,6,'absdef'], 234, 2.456 ], aqwe, done]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 'b', [1, 2, 3, 4, [456, 6, 'absdef'], 234, 2.456 ]\
                                      , 'aqwe', 'done'])
  
    def test_list_without_bracket_test(self):
        """ simple list without bracket test """
        
        the_string = " 'a', b"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 'b'])
    
    def test_list_without_bracket_test_2(self): #pylint: disable=C0103
        """ list without bracket test with a list inside """
        the_string = " 'a', b, ['a thing', 2]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 'b', ['a thing', 2] ])
        
    def test_list_error(self):
        """ list error """
        the_string = "  a ]"
        
        compiler = Compiler()
        
        try:
            compiler.compile_list(the_string)
        except CompilerError, err:
            self.assertEqual(err.message, 'Expression "  a ]" cannot be converted as a list.')
    
    def test_list_unicode_val(self):
        """ list unicode val """
        the_string = "[ u'[Gmail]/Чаты', 'z' ]".decode('utf-8')

        #to be in the same conditions as the conf object need to decode utf-8 as
        # it is done automatically with the os.open(...., 'uft-8')
        
        compiler = Compiler()
        
        compiler.compile_list(the_string)
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, [ u'[Gmail]/Чаты', 'z' ])
        
    def test_special_character_in_string(self):#pylint: disable=C0103
        """ simple list without bracket test """
        
        the_string = " 'a@', b"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a@','b'])
        
    def test_list_error_2(self):
        """ unsupported char @ """
        the_string = " a @"
        
        compiler = Compiler()
        
        try:
            compiler.compile_list(the_string)
        except CompilerError, err:
            self.assertEqual(err.message, 'Unsupported token (type: @, value : OP) (line=1,col=3).')
        
    def test_simple_dict(self):
        """ simple dict """
        
        the_string = "{'a':1, b:2 }"
                
        compiler = Compiler()
        
        the_result = compiler.compile_dict(the_string)
        
        self.assertEqual(the_result, {'a':1, 'b':2 })
        
    def test_dict_error(self):
        """ dict error """
        the_string = "{'a':1, b:2 "
                
        compiler = Compiler()
        
        try:
            compiler.compile_dict(the_string)
        except CompilerError, err:
            self.assertEqual(err.message, 'Expression "{\'a\':1, b:2 " cannot be converted as a dict.')
        
    def test_dict_with_list(self):
        """ dict with list """
        
        the_string = "{'a':1, b:[1,2,3,4,5] }"
                
        compiler = Compiler()
        
        the_result = compiler.compile_dict(the_string)
        
        self.assertEqual(the_result, {'a':1, 'b':[1, 2, 3, 4, 5]})
        
    def test_list_with_dict(self):
        """ list with dict """
        
        the_string = "['a',1,'b',{2:3,4:5} ]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 1, 'b', { 2 : 3 , 4 : 5} ])
        
    def test_noquotes_dict(self):
        """ no quotes dict """
        
        the_string = "{ no12: a b , no10:a}"
                
        compiler = Compiler()
        
        the_result = compiler.compile_dict(the_string)
        
        self.assertEqual(the_result, { 'no12': 'a b' , 'no10':'a'})
        
    def test_everything(self):
        """ everything """
        
        the_string = "['a',1,'b',{2:3,4:[1,'hello', no quotes, [1,2,3,{1:2,3:4}]]} ]"
                
        compiler = Compiler()
        
        the_result = compiler.compile_list(the_string)
        
        self.assertEqual(the_result, ['a', 1, 'b', \
                                      {2 : 3, \
                                       4: [1, 'hello', 'no quotes', [1, 2, 3, {1:2, 3:4 }]]} ])
        
def tests():
    """ Global test method """
    #suite = unittest.TestLoader().loadTestsFromModule(struct_parser)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParser)
    unittest.TextTestRunner(verbosity=2).run(suite)
        
        
if __name__ == '__main__':
    tests()

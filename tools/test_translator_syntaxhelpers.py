# Copyright (c) 2020-2022,  ellie/@ell1e & Horse64 Team (see AUTHORS.md).
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Alternatively, at your option, this file is offered under the Apache 2
# license, see accompanied LICENSE.md.


import textwrap
import unittest

from translator_syntaxhelpers import (
    tokenize, untokenize, split_toplevel_statements,
    get_statement_expr_ranges, get_statement_block_ranges,
    get_statement_inline_funcs, tree_transform_statements,
    firstnonblank, firstnonblankidx,
    get_leading_whitespace, separate_out_inline_funcs,
    get_global_standalone_func_names
)


class TestTranslatorSyntaxHelpers(unittest.TestCase):
    def test_get_global_standalone_func_names(self):
        testcode = textwrap.dedent("""\
        func hello {} func hello2(a=func x{return 5}) {
            print("Hello")
            while yes {
                func myfunc {}
            }
        }
        """)
        result = get_global_standalone_func_names(testcode)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "hello")
        self.assertEqual(result[1], "hello2")

    def test_get_statement_expr_ranges(self):
        t = ["func", " ", "myfunc", " ",
            "(", "bla", "=", "{", "->", "}", " ",
            ")", "{", "}"]
        ranges = get_statement_expr_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 4)
        self.assertEqual(t[ranges[0][0]], "(")
        self.assertEqual(ranges[0][1], 12)
        self.assertEqual(t[ranges[0][1] - 1], ")")
        ranges = get_statement_block_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 13)
        self.assertEqual(ranges[0][1], 13)

        t = ["func", " ", "myfunc", "(", "a",
            "=", "func", "{", "return", "5", "}",
            "(", ")", ")", "{", "return", "}"]
        ranges = get_statement_expr_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 3)
        self.assertEqual(t[ranges[0][0]], "(")
        self.assertEqual(ranges[0][1], 14)
        self.assertEqual(t[ranges[0][1] - 1], ")")
        ranges = get_statement_block_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 15)
        self.assertEqual(ranges[0][1], 16)

        t = ["with", "{", "lol", "}", "as", " ", "hello",
            "{", "return", "}"]
        ranges = get_statement_expr_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 1)
        self.assertEqual(ranges[0][1], 4)
        ranges = get_statement_block_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 8)
        self.assertEqual(ranges[0][1], 9)

        t = ["if", " ", "{", "lol", "}", "{", " ", "hello",
            "(", ")", "}", "elseif", " ", "yes",
            "{", "return", "}"]
        ranges = get_statement_expr_ranges(t)
        self.assertEqual(len(ranges), 2)
        ranges = get_statement_block_ranges(t)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0][0], 6)
        self.assertEqual(ranges[0][1], 10)
        self.assertEqual(ranges[1][0], 15)
        self.assertEqual(ranges[1][1], 16)

        t = ["v", "=", "func", "{", "}", "(", ")"]
        ranges = get_statement_inline_funcs(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 2)
        self.assertEqual(ranges[0][1], 3)
        self.assertEqual(ranges[0][2], 5)

        t = ["do", "{", "v", "=", "func", "{", "}", "(", ")", "}"]
        ranges = get_statement_inline_funcs(t)
        self.assertEqual(len(ranges), 0)

        t = ['func', ' ', 't', '{', 'while', ' ', 'yes', ' ',
            '{', 'print', '(', "'hello!'", ')', '}', '}']
        ranges = get_statement_block_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 4)
        self.assertEqual(ranges[0][1], 14)

        t = [" ", "const", "i"]
        ranges = get_statement_expr_ranges(t)
        self.assertEqual(len(ranges), 0)

        t = [" ", "const", "i", "=", "2"]
        ranges = get_statement_expr_ranges(t)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0][0], 4)
        self.assertEqual(ranges[0][1], 5)

        t = ['do', ' ', '{', '\n', 'x', ' ', '=', ' ',
            'oopsie_func', '(', '"florb"', ')', '  ', '\n', ' ', '}',
            ' ', 'rescue', ' ', 'ValueError', ' ', '{', '\n',
            ' ', 'x', ' ', '+=', ' ', '2', '  ', '    \n', '  ', '}',
            ' ', 'finally', ' ', '{', '\n', '   ',
            'x', ' ', '-=', ' ', '1', '  ', '  \n', ' ', '}',
            '\n', ' ']  # (Based on real world example)
        ranges = get_statement_block_ranges(t)
        self.assertEqual(len(ranges), 3)
        self.assertEqual(ranges[0][0], 3)
        self.assertEqual(ranges[0][1], 15)
        self.assertEqual(t[ranges[0][1]], "}")

    def test_get_leading_whitespace(self):
        t = get_leading_whitespace(["\n ", "\ttest"])
        self.assertEqual(t, "\n \t")

    def test_separate_out_inline_funcs(self):
        t = "func mine{func mine2{return yes}}"
        self.assertTrue("func mine" in t)
        self.assertTrue("func mine2" in t)
        tresult = separate_out_inline_funcs(t)
        self.assertTrue("func mine" in tresult)
        self.assertTrue("func mine2" in tresult)

        t = ("    func mine (a=\nfunc{return yes}){}")
        #print("tools/test_translator_syntaxhelper.py: " +
        #    "test_separate_out_inline_funcs: before 1: " +
        #    str(t))
        t_tokens = tokenize(t)
        franges = get_statement_inline_funcs(t_tokens)
        self.assertEqual(len(franges), 1)
        self.assertTrue(franges[0][2] < len(t_tokens))
        self.assertEqual(t_tokens[franges[0][2]], ")")
        tresult = separate_out_inline_funcs(t)
        #print("tools/test_translator_syntaxhelper.py: " +
        #    "test_separate_out_inline_funcs: after 1: " +
        #    str(tresult))
        self.assertTrue(tresult.startswith("    func"))

    def test_tree_transform_statements(self):
        def transform_while_weirdly(v):
            assert(type(v) == list and
                (len(v) == 0 or type(v[0]) == list))
            new_v = []
            for st in v:
                if firstnonblank(st) == "while":
                    st[firstnonblankidx(st)] = "weird"
                new_v.append(st)
            return new_v
        t = tree_transform_statements(
            "func t{while yes {print('hello!')}}",
            transform_while_weirdly)
        self.assertTrue(type(t) == str)
        self.assertTrue("weird" in t)
        self.assertTrue("while" not in t)

    def test_split_statements(self):
        t = tokenize(textwrap.dedent("""\
        func m1 {
            print('test')
        }
        func m2 {
            print('test')
        }
        """))
        statements = split_toplevel_statements(t)
        self.assertEqual(len(statements), 2)
        self.assertTrue(
            untokenize(statements[0]).strip().startswith("func "))
        self.assertTrue(
            untokenize(statements[1]).strip().startswith("func "))
        t = tokenize(textwrap.dedent("""\
        func m1 {
            print('test')
        } func m2 {
            print('test')
        }
        """))
        statements = split_toplevel_statements(t)
        self.assertEqual(len(statements), 2)
        self.assertTrue(
            untokenize(statements[0]).strip().startswith("func "))
        self.assertTrue(
            untokenize(statements[1]).strip().startswith("func "))


if __name__ == '__main__':
    unittest.main()

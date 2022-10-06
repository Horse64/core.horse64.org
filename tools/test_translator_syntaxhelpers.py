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
    get_statement_inline_funcs,
)


class TestTranslatorSyntaxHelpers(unittest.TestCase):
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

# Copyright (c) 2020-2024, ellie/@ell1e & Horse64 authors (see AUTHORS.md).
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

from translator_scopehelpers import (
    get_global_standalone_func_names,
    extract_all_imports,
    get_global_names, get_names_defined_in_func,
    statement_declared_identifiers,
)

from translator_syntaxhelpers import (
    tokenize, untokenize, split_toplevel_statements,
    get_statement_expr_ranges, get_statement_block_ranges,
    get_statement_inline_funcs, tree_transform_statements,
    firstnonblank, firstnonblankidx,
    get_leading_whitespace, separate_out_inline_funcs,
    is_number_token,
    expr_nonblank_equals, find_start_of_call_index_chain,
    is_identifier,
    make_kwargs_in_call_tailing, get_indent,
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
        self.assertTrue("hello" in result)
        self.assertTrue("hello2" in result)

    def test_get_names_defined_in_func(self):
        self.assertEqual(get_names_defined_in_func(
            textwrap.dedent("""\
            func blorb(abc) {
                var def
                if yes {
                    var blorb = 5
                }
                var flobb
            }""")), ["blorb", "abc", "def", "flobb"])
        self.assertEqual(get_names_defined_in_func(
            textwrap.dedent("""\
            var def
            """)), [])
        self.assertEqual(get_names_defined_in_func(
            textwrap.dedent("""\
            func (abc) {
                var stuff var xyz
                if yes {
                    var blorb = 5
                }
                var flobb
            }"""), is_anonymous_inline=True),
            ["abc", "stuff", "xyz", "flobb"])

    def test_get_global_names(self):
        self.assertEqual(set(get_global_names(textwrap.dedent("""\
                import net
                import net.fetch

                func blargh {
                    var c = 1
                }

                type xyz {
                    var i = 5
                }
                func net.something {
                }
                var x, y
            """), error_on_duplicates=True)),
            {"net", "blargh", "xyz", "x", "y"})
        had_value_error = False
        try:
            self.assertEqual(set(get_global_names(textwrap.dedent("""\
                import net
                import net.fetch

                func net {  # This should cause an error!
                    var c = 1
                }
            """), error_on_duplicates=True)),
            {"net"})
        except ValueError:
            had_value_error = True
            pass
        self.assertTrue(had_value_error)

    def test_statement_declared_identifiers(self):
        self.assertEqual(set(statement_declared_identifiers(
            "func x(y) {\nvar z = 1\n}",
            recurse=True)), {"x", "y", "z"})
        self.assertEqual(set(statement_declared_identifiers(
            "func x(y) {\nvar z = 1\n}",
            recurse=False)), {"x"})
        self.assertEqual(set(statement_declared_identifiers(
            "func x(y) {\nvar z = 1\nfunc j{var u}\n}",
            recurse=True)), {"x", "y", "z", "j"})
        self.assertEqual(set(statement_declared_identifiers(
            "if true {\nvar z = 1\n} else {var u}\n}",
            recurse=True)), {"z", "u"})

    def test_extract_all_imports(self):
        testcode = textwrap.dedent("""\
        import bla
        import bla.blu from bli.ble func hello {}
        func hello2(a=func x{return 5}) {
            print("Hello")
        }
        """)
        result = extract_all_imports(testcode)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], "bla")
        self.assertEqual(result[1][0], "bla.blu")
        self.assertEqual(result[1][1], "bli.ble")

if __name__ == '__main__':
    unittest.main()

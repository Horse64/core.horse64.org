# Copyright (c) 2020-2025, ellie/@ell1e & Horse64's contributors
# (see AUTHORS.md).
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
    tokenize, untokenize, expr_nonblank_equals
)

from translator_transformhelpers import (
    indent_sanity_check,
    line_has_multi_stmts_for_sure,
    transform_h64_misc_inline_to_python,
    make_string_literal_python_friendly,
    transform_h64_with_to_do_rescue,
    func_args_find_last_positional,
    is_isolated_pure_assign,
    apply_make_vec_call, vec_expr_len_if_any,
    apply_make_set_call, set_expr_len_if_any,
)

class TestTranslatorTransformHelpers(unittest.TestCase):
    def __init__(self, *args):
        super().__init__(*args)
        self.maxDiff = None

    def test_make_string_literal_python_friendly(self):
        self.assertEqual(make_string_literal_python_friendly(
            "\"test\""), "\"test\"")
        self.assertEqual(make_string_literal_python_friendly(
            ["1", "2", '"a\nb"']), ["1", "2", '"a\\nb"']
        )

    def test_line_has_multiple_statements(self):
        self.assertTrue(line_has_multi_stmts_for_sure("var x var y"))
        self.assertFalse(line_has_multi_stmts_for_sure(
            "tokens[start_pos + 1].kind == T_IDENTIFIER) {"
        ))

    def test_vec_expr_len_if_any(self):
        self.assertEqual(
            vec_expr_len_if_any(["abc", "[", "x",
                ":", "1", "]", "b"], 1), 5)
        self.assertEqual(
            vec_expr_len_if_any(["abc", "[", "x",
                ",", "1", "]", "b"], 1), None)

    def test_is_isolated_pure_assign(self):
        self.assertTrue(
            is_isolated_pure_assign("var _my_var")
        )
        self.assertFalse(
            is_isolated_pure_assign("var bla = test()")
        )
        self.assertTrue(
            is_isolated_pure_assign("var _my_var = (\n5\n) \n")
        )
        self.assertFalse(
            is_isolated_pure_assign("var bla = [test()]")
        )
        self.assertFalse(
            is_isolated_pure_assign("var bla = [test(), 2,]")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla = [, \n2,]")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla = []")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla, bla2 = [], []")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla = 2 * (not ((5)))")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla = 2 * (5)")
        )
        self.assertFalse(
            is_isolated_pure_assign("var bla = 2 * (5 + bla())")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla = {'test' + 'bla', 'blu'}")
        )
        self.assertTrue(
            is_isolated_pure_assign("var bla =  (threading.make_lock())")
        )

    def test_func_args_find_last_positional(self):
        (last_nonkw_arg_end, had_any_positional_arg, i) = (
            func_args_find_last_positional(["(", ")"], 0))
        assert(last_nonkw_arg_end == 1)
        assert(not had_any_positional_arg)
        assert(i == 2)
        (last_nonkw_arg_end, had_any_positional_arg, i) = (
            func_args_find_last_positional(["test", "(", ")"], 1))
        assert(last_nonkw_arg_end == 2)
        assert(not had_any_positional_arg)
        assert(i == 3)
        (last_nonkw_arg_end, had_any_positional_arg, i) = (
            func_args_find_last_positional(["(", "test", ")"], 0))
        assert(last_nonkw_arg_end == 2)
        assert(had_any_positional_arg)
        assert(i == 3)
        (last_nonkw_arg_end, had_any_positional_arg, i) = (
            func_args_find_last_positional(["(", "a", "=", "5", ")"], 0))
        assert(last_nonkw_arg_end == 1)
        assert(not had_any_positional_arg)
        assert(i == 5)
        (last_nonkw_arg_end, had_any_positional_arg, i) = (
            func_args_find_last_positional(["a", "=", "5"], 0))
        assert(last_nonkw_arg_end == 0)
        assert(not had_any_positional_arg)
        assert(i == 3)
        (last_nonkw_arg_end, had_any_positional_arg, i) = (
            func_args_find_last_positional(["a", "=", "5", "{"], 0))
        assert(last_nonkw_arg_end == 0)
        assert(not had_any_positional_arg)
        assert(i == 3)

    def test_transform_h64_with_to_do_rescue(self):
        s = transform_h64_with_to_do_rescue(textwrap.dedent("""\
        import io from core.horse64.org
        func main {
            with io.open("some_file.txt", "r") later as f {
                var result = f.read() later:

                await result
            }
        }
        """))
        self.assertEqual(textwrap.dedent("""\
        import io from core.horse64.org
        func main {
            var f = io.open("some_file.txt", "r") later:
            await f
            do {
                var result = f.read() later:

                await result
            } finally {
                if has_attr(f, "close") {
                    f.close()
                }
            }
        }
        """), s)
        s = transform_h64_with_to_do_rescue(textwrap.dedent("""\
        func some_func {
        }
        func main {
            do {
                print("toast")
                with some_func() as
                        oopsoops {
                    print("Hello")
                }
                print("Hello abc")
            } rescue IOError {
                print("oops")
            }
        }
        """))
        def _noemptylines(s):
            lines = s.splitlines()
            lines = [l for l in lines if l.strip() != ""]
            return "\n".join(lines)
        self.assertEqual(_noemptylines(textwrap.dedent("""\
        func some_func {
        }
        func main {
            var oopsoops
            do {
                print("toast")
                oopsoops = some_func()
                print("Hello")
                var _closevar = oopsoops
                oopsoops = none
                _closevar.close()
                print("Hello abc")
            } rescue IOError {
                if oopsoops != none and has_attr(oopsoops, "close") {
                    oopsoops.close()
                }
                print("oops")
            } finally {
                if oopsoops != none and has_attr(oopsoops, "close") {
                    oopsoops.close()
                }
            }
        }
        """)), _noemptylines(s))
        s = transform_h64_with_to_do_rescue(textwrap.dedent("""\
        func some_func {
        }
        func main {
            do {
                print("toast")
                with some_func() later as
                        oopsoops {
                    print("Hello")
                }
                print("Hello abc")
            } finally {
                print("oops")
            }
        }
        """))
        self.assertEqual(_noemptylines(textwrap.dedent("""\
        func some_func {
        }
        func main {
            var oopsoops
            do {
                print("toast")
                oopsoops = some_func() later:
                await oopsoops
                print("Hello")
                var _closevar = oopsoops
                oopsoops = none
                _closevar.close()
                print("Hello abc")
            } finally {
                if oopsoops != none and has_attr(oopsoops, "close") {
                    oopsoops.close()
                }
                print("oops")
            }
        }
        """)), _noemptylines(s))
        s = transform_h64_with_to_do_rescue(textwrap.dedent("""\
        func some_func {
        }
        func main {
            do {
                print("toast")
                with some_func() later as
                        oopsoops {
                    print("Hello")
                }
                print("Hello abc")
            } rescue IOError,
                    ValueError {
                print("OOOOP")
                do {
                    print("test!")
                }
            } rescue any {
                print("HELO!")
            } finally {
                print("oops")
            }
        }
        """))
        self.assertEqual(_noemptylines(textwrap.dedent("""\
        func some_func {
        }
        func main {
            var oopsoops
            do {
                print("toast")
                oopsoops = some_func() later:
                await oopsoops
                print("Hello")
                var _closevar = oopsoops
                oopsoops = none
                _closevar.close()
                print("Hello abc")
            } rescue IOError,
                    ValueError {
                if oopsoops != none and has_attr(oopsoops, "close") {
                    oopsoops.close()
                }
                print("OOOOP")
                do {
                    print("test!")
                }
            } rescue any {
                if oopsoops != none and has_attr(oopsoops, "close") {
                    oopsoops.close()
                }
                print("HELO!")
            } finally {
                if oopsoops != none and has_attr(oopsoops, "close") {
                    oopsoops.close()
                }
                print("oops")
            }
        }""")), _noemptylines(s))

    def test_indent_sanity_check(self):
        def do_test(s, should_fail=False):
            had_error = False
            try:
                indent_sanity_check(s)
            except ValueError:
                had_error = True
            self.assertEqual(had_error, should_fail,
                "expected " + ("no " if should_fail else
                "an ") + " indent mistake "
                "to be detected in this code:\n" +
                s)
        do_test(textwrap.dedent("""\
        func test {
            var a
                var b
        }
        """), should_fail=True)
        do_test(textwrap.dedent("""\
        var bla = [  # Test:
            ["new"]
        ]
        """), should_fail=False)
        do_test(textwrap.dedent("""\
        func test {
            var a
            var b
        }
        """), should_fail=False)
        do_test(textwrap.dedent("""\
        func test {
            do {
                var a
                var b
        }
        }
        """), should_fail=True)
        do_test(textwrap.dedent("""\
        func test {
            var a var b
        }
        """), should_fail=True)

    def test_transform_h64_misc_inline_to_python(self):
        t = ("s = s.replace(\"\r\", " ")." +
            "replace(\"\n\", " ").\n" +
            "    replace(\"\t\", " ").trim()")
        texpected = ("s = _translator_runtime_helpers." +
            "_container_trim(s.replace(\"\r\", " ")." +
            "replace(\"\n\", " ").\n" +
            "    replace(\"\t\", " "),)")
        tresult = transform_h64_misc_inline_to_python(t)
        self.assertTrue(expr_nonblank_equals(tresult, texpected),
            msg=("got " + tresult + ", expected: " + texpected))

        t = ("var test = " +
            "(\"complex string concat test: \" + f(l, 1).as_str())")
        texpected = ("var test = " +
            "(\"complex string concat test: \" + " +
            "_translator_runtime_helpers._value_to_str(f(l, 1)))")
        tresult = transform_h64_misc_inline_to_python(t)
        self.assertTrue(expr_nonblank_equals(tresult, texpected),
            msg=("got " + tresult + ", expected: " + texpected))

        t = ("args = args.sub(0, double_dash_idx) +" +
            "    args.sub(double_dash_idx + 1)")
        texpected = ("args = _translator_runtime_helpers." +
            "_container_sub(args, 0, double_dash_idx) +" +
            "    _translator_runtime_helpers._container_sub(" +
            "args, double_dash_idx + 1)")
        tresult = transform_h64_misc_inline_to_python(t)
        self.assertTrue(expr_nonblank_equals(tresult, texpected),
            msg=("got " + tresult + ", expected: " + texpected))

if __name__ == '__main__':
    unittest.main()

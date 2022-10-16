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
    expr_nonblank_equals, get_indent,
)

from translator_transformhelpers import (
    indent_sanity_check
)

from translator_latertransform import (
    transform_later_to_closure_unnested,
    transform_later_to_closures,
)


class TestTranslatorLaterTransform(unittest.TestCase):
    def test_transform_later_to_closure(self):
        # A helper function to test the later transform for us:
        def do_test(testcode, texpected, any_match_value=None,
                recursive=False):
            if texpected is None:  # That means no change expected.
                texpected = testcode
            indent_sanity_check(
                texpected,
                what_in="test_transform_later_to_closure() "
                "test input which must be indented right")

            # Get test code into expected format first:
            resultstmts = None
            resulttokens = []
            if not recursive:
                # Split it up into statements, run un-nested inner func:
                teststmts = split_toplevel_statements(
                    tokenize(testcode) if type(testcode) == str else
                    testcode)
                resultstmts = (
                    transform_later_to_closure_unnested(teststmts,
                        callback_delayed_func_name=[
                        "_translator_runtime_helpers", ".",
                        "_async_delay_call"]))
                resulttokens = []
                for resultstmt in resultstmts:
                    resulttokens += resultstmt
            else:
                # Run the recursive func to transform everything:
                resulttokens = transform_later_to_closures(
                    tokenize(testcode) if type(testcode) == str else
                    testcode,
                    callback_delayed_func_name=[
                        "_translator_runtime_helpers", ".",
                        "_async_delay_call"])

            # Check that the result is indented right:
            try:
                indent_sanity_check(
                    resulttokens,
                    what_in="test_transform_later_to_closure() "
                    "test result after applying the tested func")
            except ValueError:
                print('== WRONGLY INDENTED TEST OUTPUT: """\n' +
                      untokenize(resulttokens) +
                    '"""\n== GIVEN INPUT: """\n' +
                    (untokenize(testcode) if
                    type(testcode) != str else testcode) + '"""')
                raise

            # Check the result matches what we expected:
            mismatch_error = None
            try:
                expr_nonblank_equals(resulttokens,
                    (tokenize(texpected) if type(texpected) == str else
                     texpected), throw_error_with_details=True,
                    any_match_value=any_match_value)
            except ValueError as e:
                mismatch_error = e
            self.assertEqual(mismatch_error, None,
                'HAD A MISMATCH ERROR: ' + str(mismatch_error) + '\n'
                'Got: """' + str(untokenize(resulttokens)) +
                '""",\nexpected: """' + (
                texpected if type(texpected) == str else
                untokenize(texpected)) + '""",\noriginal '
                'test input: """' + (untokenize(testcode) if
                type(testcode) != str else testcode) + '"""')

        # First test that the non-recursive call won't recurse:
        do_test(textwrap.dedent("""\
        func hello2 {
            func blorb {
                mycall(abc) later:
            }
        }"""), None, recursive=False)

        # A slightly more complex attempt:
        do_test(textwrap.dedent("""\
        func f {
            print("Hello")
            mycall(abc) later:
            print("Bla")
        }"""
        ), textwrap.dedent("""\
        func f(__ANYTOK__) {
            print("Hello")
            func __ANYTOK__(__ANYTOK__, __ANYTOK__) {
                print("Bla")
                __ANYTOK__(None, None)
                return
            }
            mycall(abc, __ANYTOK__)
            return
        }
        """), any_match_value="__ANYTOK__")

        # Ensure trailing returns are handled fine:
        do_test(textwrap.dedent("""\
        func f {
            print("Hello")
            mycall(abc) later:
            print("Bla")
            return 5
        }"""
        ), textwrap.dedent("""\
        func f(__ANYTOK__) {
            print("Hello")
            func __ANYTOK__(__ANYTOK__, __ANYTOK__) {
                print("Bla")
                __ANYTOK__(None, 5)
                return
            }
            mycall(abc, __ANYTOK__)
            return
        }
        """
        ), any_match_value="__ANYTOK__")

        # Ensure arguments aren't in wrong order:
        do_test(textwrap.dedent("""\
        func xyz(args, thing=no) {
            return later "test"
        }
        func main {
            var result = xyz([1, 2], thing=yes) later:
        }"""), textwrap.dedent(
        """\
        func xyz(args, __ANYTOK__, thing=no) {
            func __ANYTOK__ {
                __ANYTOK__(None, "test")
            }
            return _translator_runtime_helpers._async_delay_call(
                __ANYTOK__, []
            )
        }
        func main(__ANYTOK__) {
            func __ANYTOK__(__ANYTOK__, result) {
                __ANYTOK__(None, None)
                return
            }
            var result = xyz([1, 2], thing=yes, __ANYTOK__)
            return
        }"""), any_match_value="__ANYTOK__")

        # Ensure do/rescue/finally is factored in correctly:
        do_test(textwrap.dedent("""\
        func f {
            do {
                print("Hello")
                mycall(abc) later:
                print("Bla")
                var x = mycall2(abc) later:
                print("test")
                await x
            } rescue any {
                print("Rescued!")
            } finally {
                print("Finally.")
            }
        }"""
        ), textwrap.dedent("""\
        func f(__ANYTOK__) {
            # Definitions of rescue/finally disable vars and callbacks:
            var __ANYTOK__  # Disable var 1/2
            var __ANYTOK__  # Disable var 2/2
            var __ANYTOK__ = no  # Callback 1/2
            var __ANYTOK__ = no  # Callback 2/2
            do {
                print("Hello")
                func __ANYTOK__(__ANYTOK__, __ANYTOK__) {
                    var __ANYTOK__ = no  # Local disable var 1/2
                    var __ANYTOK__ = no  # Local disable var 2/2
                    do {
                        print("Bla")
                        func __ANYTOK__(__ANYTOK__, x) {
                            var __ANYTOK__ = no  # Local disable var 1/2
                            var __ANYTOK__ = no  # Local disable var 2/2
                            do {
                                print("test")
                                # 'await x' transforms into an error throw:
                                if (__ANYTOK__ != none) {
                                    throw __ANYTOK__
                                }
                                __ANYTOK__(None, None)  # Final return none.
                                __ANYTOK__ = yes
                                __ANYTOK__ = yes
                                return
                            } rescue any {
                                if not __ANYTOK__ {
                                    __ANYTOK__()  # Call to rescue
                                }
                            } finally {
                                if not __ANYTOK__ {
                                    __ANYTOK__()  # Call to finally
                                }
                            }
                        }
                        var x = mycall2(__ANYTOK__, __ANYTOK__)
                        __ANYTOK__ = yes
                        __ANYTOK__ = yes
                        return
                    } rescue any {
                        if not __ANYTOK__ {
                            __ANYTOK__()  # Call to rescue
                        }
                    } finally {
                        if not __ANYTOK__ {
                            __ANYTOK__()  # Call to finally
                        }
                    }
                }
                # Definition & assignment of rescue/finally closure copies:
                func __ANYTOK__ {
                    print("Rescued!")
                }
                __ANYTOK__ = __ANYTOK__
                func __ANYTOK__ {
                    print("Finally.")
                }
                __ANYTOK__ = __ANYTOK__
                # The actual call (the 'later' call):
                mycall(abc, __ANYTOK__)
                # Disable our own finally/rescue now:
                __ANYTOK__ = yes
                __ANYTOK__ = yes
                return
            } rescue any {
                if not __ANYTOK__ {  # Checks the disable var.
                    print("Rescued!")
                }
            } finally {
                if not __ANYTOK__ {
                    print("Finally.")
                }
            }
            # Return for when we don't make it through first later boundary
            # above:
            __ANYTOK__(None, None)
            return
        }
        """), any_match_value="__ANYTOK__")


if __name__ == '__main__':
    unittest.main()

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
        def do_test(
                testcode, texpected, any_match_value=None,
                pair_match_prefix=None,
                recursive=False
                ):
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
                expr_nonblank_equals(
                    resulttokens,
                    (tokenize(texpected) if type(texpected) == str else
                     texpected), throw_error_with_details=True,
                    any_match_value=any_match_value,
                    pair_match_prefix=pair_match_prefix
                )
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
            var x = mycall(abc) later:
            do {
                await x
            } rescue ValueError {
                print("Oops")
            }
            print("Bla")
        }"""
        ), textwrap.dedent("""\
        func f(__ANYPAIR1__) {
            do {
                print("Hello")
                func __ANYTOK__(__ANYPAIR2__, x) {
                    do {
                        do {
                            if __ANYPAIR2__ != none {
                                throw __ANYPAIR2__
                            }
                        } rescue ValueError {
                            print("Oops")
                        }
                        print("Bla")
                        __ANYTOK__(none, none)
                        return
                    } rescue any as e {
                        if __ANYPAIR1__ != none {
                            __ANYPAIR1__(e, none)
                            return
                        }
                        throw e
                    }
                }
                mycall(abc, __ANYTOK__)
                return
            } rescue any as e {
                if __ANYPAIR1__ != none {
                    __ANYPAIR1__(e, none)
                    return
                }
                throw e
            }
        }
        """), any_match_value="__ANYTOK__",
        pair_match_prefix="__ANYPAIR")

        # Ensure trailing returns are handled fine:
        do_test(textwrap.dedent("""\
        func f {
            print("Hello")
            mycall(abc) later:
            print("Bla")
            return 5
        }"""
        ), textwrap.dedent("""\
        func f(__ANYPAIR1__) {
            do {
                print("Hello")
                func __ANYTOK__(__ANYTOK__, __ANYTOK__) {
                    do {
                        if __ANYPAIR2__ != none {
                            throw __ANYPAIR2__
                        }
                        print("Bla")
                        __ANYPAIR1__(none, 5)
                        return
                    } rescue any as e {
                        if __ANYPAIR1__ != none {
                            __ANYPAIR1__(e, none)
                            return
                        }
                        throw e
                    }
                }
                mycall(abc, __ANYTOK__)
                return
            } rescue any as e {
                if __ANYPAIR1__ != none {
                    __ANYPAIR1__(e, none)
                    return
                }
                throw e
            }
        }
        """
        ), any_match_value="__ANYTOK__",
        pair_match_prefix="__ANYPAIR")

        # Test that 'later ignore' works:
        do_test(textwrap.dedent("""\
        func xyz(args, thing=no) {
            return later "test"
        }
        func main {
            xyz([1, 2], thing=yes) later ignore
            print("Continuing, ignoring")
        }"""), textwrap.dedent(
        """\
        func xyz(args, __ANYPAIR1__, thing=no) {
            do {
                func __ANYPAIR3__ {
                    __ANYPAIR1__(none, "test")
                }
                _translator_runtime_helpers._async_delay_call(
                    __ANYPAIR3__, []
                )
                return
            } rescue any as e {
                if __ANYPAIR1 != none {
                    __ANYPAIR1__(e, none)
                    return
                }
                throw e
            }
        }
        func main {
            func __ANYTOK__(__ANYPAIR4__, __ANYTOK__) {
                if __ANYPAIR4__ != none {
                    print(__ANYTOK__ + __ANYPAIR4__)
                }
            }
            xyz([1, 2], thing=yes, __ANYTOK__)
            print("Continuing, ignoring")
        }"""), any_match_value="__ANYTOK__",
        pair_match_prefix="__ANYPAIR")


        # Ensure arguments aren't in wrong order:
        do_test(textwrap.dedent("""\
        func xyz(args, thing=no) {
            return later "test"
        }
        func main {
            var result = xyz([1, 2], thing=yes) later:
            await result
        }"""), textwrap.dedent(
        """\
        func xyz(args, __ANYPAIR1__, thing=no) {
            do {
                func __ANYPAIR3__ {
                    __ANYPAIR1__(none, "test")
                }
                _translator_runtime_helpers._async_delay_call(
                    __ANYPAIR3__, []
                )
                return
            } rescue any as e {
                if __ANYPAIR1 != none {
                    __ANYPAIR1__(e, none)
                    return
                }
                throw e
            }
        }
        func main(__ANYPAIR2__) {
            do {
                func __ANYTOK__(__ANYPAIR4__, result) {
                    do {
                        if __ANYPAIR4__ != none {
                            throw __ANYPAIR4__
                        }
                        __ANYPAIR2__(none, none)
                        return
                    } rescue any as e {
                        if __ANYPAIR2 != none {
                            __ANYPAIR2__(e, none)
                            return
                        }
                        throw e
                    }
                }
                xyz([1, 2], thing=yes, __ANYTOK__)
                return
            } rescue any as e {
                if __ANYPAIR2 != none {
                    __ANYPAIR2__(e, none)
                    return
                }
                throw e
            }
        }"""), any_match_value="__ANYTOK__",
        pair_match_prefix="__ANYPAIR")

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
        func f(__ANYPAIR1__) {
            do {  # Handles anything uncaught.
                # Definitions of rescue/finally disable vars and callbacks:
                var __ANYTOK__  # Disable var 1/2.
                var __ANYTOK__  # Disable var 2/2.
                var __ANYTOK__ = no  # Callback 1/2.
                var __ANYTOK__ = no  # Callback 2/2.
                do {  # Original user-written 'do'.
                    # Define & assign rescue/finally closure copies:
                    func __ANYTOK__(__ANYTOK__) {
                        print("Rescued!")
                    }
                    __ANYTOK__ = __ANYTOK__
                    func __ANYTOK__ {
                        print("Finally.")
                    }
                    __ANYTOK__ = __ANYTOK__
                    print("Hello")
                    # The callback for the first 'later':
                    func __ANYTOK__(__ANYTOK__, __ANYTOK__) {
                        do {  # Handles anything uncaught.
                            var __ANYTOK__ = no  # Local disable var 1/2.
                            var __ANYTOK__ = no  # Local disable var 2/2.
                            do {  # User-induced 'do'.
                                # Throw error since user didn't use
                                # await:
                                if __ANYPAIR2__ != none {
                                    throw __ANYPAIR2__
                                }
                                # Regular user code:
                                print("Bla")
                                # The callback for the second 'later':
                                func __ANYTOK__(__ANYTOK__, x) {
                                    do {  # Handles anything uncaught.
                                        var __ANYTOK__ = no  # Dsbl. var 1/2
                                        var __ANYTOK__ = no  # Dsbl. var 2/2
                                        do {  # User-induced 'do'.
                                            print("test")
                                            # 'await x' becomes error throw:
                                            if __ANYTOK__ != none {
                                                throw __ANYTOK__
                                            }
                                            # Final return:
                                            __ANYTOK__(none, none)
                                            # Disables 'rescue': ...
                                            __ANYTOK__ = yes
                                                # ...'finally' runs now.
                                            return
                                        } rescue any as e {
                                            if not __ANYTOK__ {
                                                # Call to 'rescue':
                                                __ANYTOK__(e)
                                            }
                                        } finally {
                                            if not __ANYTOK__ {
                                                # Call to 'finally':
                                                __ANYTOK__()
                                            }
                                        }
                                    } rescue any as e {
                                        # Uncaught error to cb:
                                        if __ANYPAIR1__ != none {
                                            __ANYPAIR__(e, none)
                                            return
                                        }
                                        throw e
                                    }
                                }
                                mycall2(__ANYTOK__, __ANYTOK__)
                                __ANYTOK__ = yes
                                __ANYTOK__ = yes
                                return
                            } rescue any as e {
                                if not __ANYTOK__ {
                                    __ANYTOK__(e)  # Call to 'rescue'.
                                }
                            } finally {
                                if not __ANYTOK__ {
                                    __ANYTOK__()  # Call to 'finally'.
                                }
                            }
                        } rescue any as e {
                            # Uncaught error to cb:
                            if __ANYPAIR1__ != none {
                                __ANYPAIR__(e, none)
                                return
                            }
                            throw e
                        }
                    }
                    # The actual call (the 'later' call):
                    mycall(abc, __ANYTOK__)
                    # Disable our own finally/rescue now:
                    __ANYTOK__ = yes
                    __ANYTOK__ = yes
                    return
                } rescue any {
                    if not __ANYTOK__ {  # Checks the disable var.
                        __ANYTOK__(none)  # Call to 'rescue'.
                    }
                } finally {
                    if not __ANYTOK__ {
                        __ANYTOK__()  # Call to 'finally'.
                    }
                }
            } rescue any as e {
                # Uncaught error to cb:
                if __ANYPAIR1__ != none {
                    __ANYPAIR__(e, none)
                    return
                }
                throw e
            }
            # Return for when we don't make it through any 'later'.
            # above:
            __ANYPAIR1__(none, none)
            return
        }
        """), any_match_value="__ANYTOK__",
        pair_match_prefix="__ANYPAIR")


if __name__ == '__main__':
    unittest.main()

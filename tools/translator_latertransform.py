#!/usr/bin/python3

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

VERSION="unknown"

import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap
import uuid

from translator_syntaxhelpers import (
    firstnonblank, firstnonblankidx,
    nextnonblank, nextnonblankidx,
    prevnonblank, prevnonblankidx,
    split_toplevel_statements, flatten,
    is_identifier, get_statement_block_ranges,
    is_whitespace_token, get_indent, tokenize,
    untokenize, is_whitespace_statement,
    tree_transform_statements,
)


translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)


def transform_later_to_closure_funccontents(
        sts, h64_indent="    ",
        outer_callback_name=None,
        callback_delayed_func_name=None,
        await_error_name=None,
        closest_scope_later_func_name=None
        ):
    assert(outer_callback_name != None)
    assert(callback_delayed_func_name != None)
    new_sts = []
    st_idx = -1
    for st in sts:
        st_idx += 1
        assert(type(st) == list and
            len(st) == 0 or type(st[0]) == str)

        # First, handle any 'return'/'return later':
        if firstnonblank(st) == "return":
            wrap_in_delay = False
            i = firstnonblankidx(st)
            returnidx = i
            if nextnonblank(st, i) == "later":
                wrap_in_delay = True
                i = nextnonblankidx(st, i)
            i += 1
            return_arg = st[i:]
            while (len(return_arg) > 0 and
                    return_arg[-1].strip(" \r\t\n") == ""):
                return_arg = return_arg[:-1]
            indent_tokens = st[:returnidx]
            _delayfuncname = None
            if wrap_in_delay:
                _delayfuncname = "_fdelay" + (
                    str(uuid.uuid4()).replace("-", "")
                )
                if "".join(return_arg).strip(" \t\r\n") == "":
                    return_arg = ["None"]
                new_sts.append(
                    indent_tokens + ["func", " ", _delayfuncname,
                    " ", "{", "\n"] +
                    indent_tokens + [h64_indent] + [
                    outer_callback_name, "(", "None", ","] +
                    return_arg + [")", "\n"] + indent_tokens +
                    ["}", "\n"]
                )
                delayed_call_tokens = callback_delayed_func_name
                if type(delayed_call_tokens) == str:
                    delayed_call_tokens = tokenize(delayed_call_tokens)
                new_sts.append(
                    indent_tokens + ["return", " "] +
                    delayed_call_tokens +
                    ["(", _delayfuncname, ",", "[", "]", ")"]
                )
            else:
                new_sts.append(
                    indent_tokens + [outer_callback_name, "("] +
                    ["None", ","] + return_arg + [")", "\n"]
                )
                new_sts.append(
                    indent_tokens + ["return", "\n"]
                )
            continue

        # Then, handle awaits:
        if firstnonblank(st) == "await":
            if await_error_name is None:
                # This is invalid code, ignore.
                new_sts.append(st)
                continue
            indent_tokens = st[:firstnonblankidx(st)]
            new_sts.append(
                indent_tokens + ["if", " ", "(",
                await_error_name, " ", "!=", " ", "none", ")", " ",
                 "{", "\n"] + indent_tokens + [h64_indent,
                "throw", " ", await_error_name, "\n"] +
                indent_tokens + ["}", "\n"]
            )
            continue

        # Not a 'return'/'return later'. Find other 'later' uses:
        later_indexes = []
        bracket_depth = 0
        i = -1
        for t in st:
            i += 1
            if t in {"(", "{", "["}:
                bracket_depth += 1
            elif t in {")", "}", "]"}:
                bracket_depth -= 1
            if t == "later" and bracket_depth == 0:
                later_indexes.append(i)

        if len(later_indexes) != 1:
            # Okay, just transform the inner blocks and be done:
            ranges = reversed(get_statement_block_ranges(st))
            for brange in ranges:
                st = (st[:brange[0]] +
                    flatten(transform_later_to_closure_funccontents(
                        split_toplevel_statements(
                            st[brange[0]:brange[1]]
                        ),
                        h64_indent=h64_indent,
                        outer_callback_name=outer_callback_name,
                        callback_delayed_func_name=
                            callback_delayed_func_name,
                        await_error_name=await_error_name,
                        closest_scope_later_func_name=
                            closest_scope_later_func_name
                    )) +
                    st[brange[1]:])
            new_sts.append(st)
            continue

        # Now we should have just one 'later' left if the
        # code is valid in the first place:
        later_index = later_indexes[0]
        if (not nextnonblank(st, later_index) in {":", "repeat"} or
                nextnonblank(st, later_index, no=2) != ""):
            # Invalid code. Just ignore.
            new_sts.append(st)
            continue
        is_a_repeat = (nextnonblank(st, later_index) == "repeat")

        # See where in the 'later'ed call to insert the callback:
        later_preceding_call_close = prevnonblankidx(st, later_index)
        if (later_preceding_call_close < 0 or
                st[later_preceding_call_close] != ")"):
            # Invalid code. Just ignore.
            new_sts.append(st)
            continue
        later_preceding_call_noargs = False
        later_preceding_call_args_have_trailing_comma = False
        if prevnonblank(st, later_index, no=2) == "(":
            later_preceding_call_noargs = True
        elif prevnonblank(st, later_index, no=2) == ",":
            later_preceding_call_args_have_trailing_comma = True

        # Get argument name from var/const declaration if any:
        vardef_at_start_idx = None
        vardef_past_eq_idx = None
        arg_name = None
        if firstnonblank(st) in {"var", "const"}:
            # Extract name and then get index where to cut it off:
            i2 = firstnonblankidx(st)
            vardef_at_start_idx = i2
            if is_identifier(nextnonblank(st, i2)):
                arg_name = nextnonblank(st, i2)
            i2 += 1  # Go past identifier.
            while i2 < len(st) and st[i2] != '=':
                i2 += 1
            if i2 >= len(st):
                new_sts.append(st)
                continue  # Invalid code.
            i2 += 1  # Move past '='.
            while i2 < len(st) and st[i2].strip(" \t\r\n") == "":
                i2 += 1
            if i2 >= len(st):
                new_sts.append(st)
                continue  # Invalid code.
            vardef_past_eq_idx = i2

        # Name for our new callback implicitly created by 'later',
        # as well as indent for the 'func ... {' opening line:
        funcname = None
        await_error_name = None
        if not is_a_repeat:
            funcname = "_" + str(uuid.uuid4()).replace("-", "")
            await_error_name = "_awerr" + str(uuid.uuid4()).replace("-", "")
        indent = get_indent(st)

        # Get all the statements after 'later' to pull into callback:
        func_inner_content_str = (
            untokenize(flatten(sts[st_idx + 1:])))
        func_inner_content_str = h64_indent + (
            ("\n" + h64_indent).join(
                func_inner_content_str.split("\n")
            ))
        func_inner_content = None
        if not is_a_repeat:
            func_inner_lines = (
                transform_later_to_closure_funccontents(
                    split_toplevel_statements(
                        tokenize(func_inner_content_str)
                    ),
                    h64_indent=h64_indent,
                    outer_callback_name=outer_callback_name,
                    callback_delayed_func_name=
                        callback_delayed_func_name,
                    await_error_name=await_error_name,
                    closest_scope_later_func_name=
                        funcname
                )
            )
            inner_indent = get_indent(st) + h64_indent
            assert(len(func_inner_lines) == 0 or
                type(func_inner_lines[0]) == list)

            # Check if it ends with a 'return':
            ends_in_return = False
            if len(func_inner_lines) > 0:
                inner_indent = get_indent(func_inner_lines[0])
                if inner_indent is None:
                    # Revert to working value.
                    inner_indent = get_indent(st) + h64_indent
                last_line = func_inner_lines[-1]
                while is_whitespace_statement(last_line):
                    func_inner_lines = func_inner_lines[:-1]
                    if len(func_inner_lines) <= 0:
                        break
                    last_line = func_inner_lines[-1]
                if ("".join(get_indent(last_line)) ==
                        inner_indent and
                        firstnonblank(last_line) == "return"):
                    ends_in_return = True

            # Now flatten function code:
            func_inner_content = flatten(func_inner_lines)

            # If new function doesn't have return at the end,
            # add a callback and return to make sure we bail:
            if not ends_in_return:
                func_inner_content += (
                    ["\n"] + ["\n", inner_indent,
                    outer_callback_name, "(",
                    "None", ",", "None", ")", "\n",
                    inner_indent, "return", "\n"])

        # Assemble callback statement and add it in:
        if not is_a_repeat:
            insert_st = ([indent, "func", " ",
                funcname, " ", "(", await_error_name])
            if arg_name != None:
                insert_st += [",", arg_name]
            else:
                insert_st += [",", "_unused" +
                    str(uuid.uuid4()).replace("-", "")]
            insert_st += [")", " "]
            insert_st += (["{", "\n"] +
                func_inner_content +
                ["\n"] + ([indent] if
                    indent != None and len(indent) > 0 else
                    []) +
                ["}", "\n"])
            new_sts.append(insert_st)

        # If this is a repeat, call back ourselves!
        call_to = funcname
        if is_a_repeat:
            assert(closest_scope_later_func_name != None)
            call_to = closest_scope_later_func_name

        # Now add the call that had the 'later', but stripped off:
        orig_st = list(st)
        st = st[:later_preceding_call_close]
        if (not later_preceding_call_noargs and
                not later_preceding_call_args_have_trailing_comma):
            st += [",", " "]
        st += [call_to] + [")", "\n"]
        new_sts.append(st)
        new_sts.append([indent, "return", "\n"])

        # Output some debug info:
        #print("CREATED STATEMENTS: " + str(new_sts[-3:]))
        #print("ORIGINAL ONE: " + str(orig_st))
        #print("TOKEN WHERE ORIG CALL ENDED: " +
        #    str(later_preceding_call_close))
        #print("ARG START:ARG_END FOR 'later': " +
        #    str(orig_st[arg_start:arg_end]))
        break
    return new_sts


def is_func_a_later_func(st):
    if type(st) == str:
        st = tokenize(St)
    assert(type(st) in {tuple, list})
    assert(len(st) == 0 or type(st[0]) == str)

    if (firstnonblank(st) != "func" or
            not "later" in st):
        return False

    def scan_inner_stmts(sts):
        for st in sts:
            if firstnonblank(st) == "func":
                continue
            if firstnonblank(st) == "return":
                if (nextnonblank(st, firstnonblankidx(st)) ==
                        "later"):
                    return True
                continue
            elif (is_identifier(firstnonblank(st)) or
                    firstnonblank(st) in {"var", "const"}):
                i = firstnonblankidx(st) + 1
                bracket_depth = 0
                while i < len(st):
                    if st[i] in {"(", "{", "["}:
                        bracket_depth += 1
                    elif st[i] in {")", "}", "]"}:
                        bracket_depth -= 1
                    if (bracket_depth == 0 and
                            st[i] == "later"):
                        return True
                    i += 1
                continue
            assert(type(st) == list)
            assert(len(st) == 0 or type(st[0]) == str)
            ranges = get_statement_block_ranges(st)
            for block_range in ranges:
                if scan_inner_stmts(
                        split_toplevel_statements(
                        st[block_range[0]:block_range[1]]
                        )):
                    return True
        return False
    ranges = get_statement_block_ranges(st)
    for block_range in ranges:
        if scan_inner_stmts(
                split_toplevel_statements(
                st[block_range[0]:block_range[1]]
                )):
            return True
    return False


def transform_later_to_closure_unnested(
        sts, h64_indent="    ",
        callback_delayed_func_name=None
        ):
    new_sts = []
    st_idx = -1
    for st in sts:
        st_idx += 1

        if not is_func_a_later_func(st):
            new_sts.append(st)
            continue
        callback_name = ("_later_cb" +
            str(uuid.uuid4()).replace("-", ""))

        # Go from 'func' past until arg or code block start:
        i = firstnonblankidx(st)
        if i >= len(st) or st[i] != "func":
            new_sts.append(st)
            continue  # Invalid code!
        i += 1  # Past 'func'.
        while i < len(st) and st[i].strip(" \r\n\t") == "":
            i += 1
        if i >= len(st) or not is_identifier(st[i]):
            new_sts.append(st)
            continue  # Invalid code!
        i += 1  # Past func name.
        arg_start = i
        while (i < len(st) and
                st[i] != "(" and st[i] != "{"):
            i += 1
        if i >= len(st):
            new_sts.append(st)
            continue  # Invalid code!

        # We're at either code or args now. Check args if present:
        code_block_open_bracket = None
        arg_list_start = None
        last_nonkw_arg_end = None
        if st[i] == "{":
            code_block_open_bracket = i
        elif st[i] == "(":
            # We got function arguments! Find our insert point:
            i += 1  # Past the '('.
            arg_list_start = i
            current_arg_start = i
            current_arg_had_assign = False
            bracket_depth = 1
            while i < len(st) and (
                    bracket_depth > 0 or
                    is_h64op_with_righthand(
                        prevnonblank(st, i)) or
                    prevnonblank(st, i) == "," or
                    prevnonblank(st, i) == "("):
                are_at_bail_bracket = False
                if st[i] in {"(", "{", "["}:
                    bracket_depth += 1
                elif st[i] in {")", "}", "]"}:
                    bracket_depth -= 1
                    if st[i] == ")" and bracket_depth <= 0:
                        are_at_bail_bracket = True
                # See if we reached end of arg list, or end of arg:
                if are_at_bail_bracket or (st[i] == "," and
                        nextnonblank(st, i) == ")" and
                        bracket_depth <= 1):
                    if st[i] == ",":
                        inext = nextnonblank(st, i)
                        st[i] == " "
                        i = inext
                    if not current_arg_had_assign:
                        last_nonkw_arg_end = i
                    break
                elif st[i] == "=" and bracket_depth <= 1:
                    current_arg_had_assign = True
                elif st[i] == "," and bracket_depth <= 1:
                    if not current_arg_had_assign:
                        last_nonkw_arg_end = i
                    current_arg_start = i + 1
                    current_arg_had_assign = False
                i += 1

            # We're at the end of the arguments. Go to code block:
            if i >= len(st) or st[i] != ")":
                new_sts.append(st)
                continue  # Invalid code!
            i += 1  # Past closing ')'.
            while i < len(st) and st[i].strip(" \r\t\n") == "":
                i += 1
            if i >= len(st) or st[i] != "{":
                new_sts.append(st)
                continue  # Invalid code
            code_block_open_bracket = i
        assert(code_block_open_bracket != None)
        if last_nonkw_arg_end != None:
            st = (st[:last_nonkw_arg_end] + [",",
                callback_name] +
                st[last_nonkw_arg_end:])
        else:
            st = (st[:code_block_open_bracket] +
                ["(", callback_name, ")", " "] +
                st[code_block_open_bracket:])

        # Get the block ranges, to transform our code contents:
        ranges = get_statement_block_ranges(st)
        assert(len(ranges) == 1), (
            "transformed statement in "
            "transform_later_to_closure_unnested() "
            "after inserting callback arg no longer "
            "has a block range??? st=" + str(st))
        block_range = ranges[0]
        inner_statements = split_toplevel_statements(
            st[block_range[0]:block_range[1]]
        )
        inner_indent = None
        if len(inner_statements) > 0:
            inner_indent = get_indent(inner_statements[0])
        if inner_indent == 0:
            inner_indent = get_indent(st) + h64_indent

        # Actually transform our inner function code:
        inner_code_lines = (
            transform_later_to_closure_funccontents(
                inner_statements,
                h64_indent=h64_indent,
                callback_delayed_func_name=
                    callback_delayed_func_name,
                outer_callback_name=callback_name
            ))
        ends_in_return = False
        if len(inner_code_lines) > 0:
            last_line = inner_code_lines[-1]
            while is_whitespace_statement(last_line):
                inner_code_lines = inner_code_lines[:-1]
                if len(inner_code_lines) <= 0:
                    break
                last_line = inner_code_lines[-1]
            if ("".join(get_indent(last_line)) ==
                    inner_indent and
                    firstnonblank(last_line) == "return"):
                ends_in_return = True

        # Put together a new statement around the code:
        outer_indent = get_indent(st)
        if outer_indent == None:
            outer_indent = ""
        newst = (st[:block_range[0]] + ["\n"] +
            flatten(inner_code_lines))  # Old "header" + inner code
        while (len(newst) > 0 and
                newst[-1].strip(" \r\n\t") == ""):
            newst = newst[:-1]
        if not ends_in_return:
            # If new function doesn't have return at the end,
            # add a callback and return to make sure we bail:
            newst += (["\n"] + ["\n", inner_indent,
                callback_name, "(",
                "None", ",", "None", ")", "\n",
                inner_indent, "return", "\n"])
        # Add the closing stuff to our func, ensure right indent:
        def _trimindent(_st):
            while len(_st) > 0 and _st[0].strip(" \r\t\n") == "":
                _st = _st[:1]
            return _st
        newst += (["\n", outer_indent] + _trimindent(
            st[block_range[1]:] + ["\n"]))
        # Ok done, add our reformatted function:
        new_sts.append(newst)
    return new_sts


def transform_later_to_closures(
        s, callback_delayed_func_name=None):
    assert(type(callback_delayed_func_name) in {str, list})
    def do_transform_later(sts):
        return transform_later_to_closure_unnested(
            sts, callback_delayed_func_name=
                callback_delayed_func_name)
    s = tree_transform_statements(s, do_transform_later)
    return s


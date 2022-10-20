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
    token_outside_brackets_idx,
    split_toplevel_statements, flatten,
    increase_indent,
    is_h64op_with_righthand,
    adjust_to_absolute_indent,
    cut_tokens_after_lineend,
    is_identifier, get_statement_block_ranges,
    is_whitespace_token, get_indent, tokenize,
    untokenize, is_whitespace_statement,
    tree_transform_statements,
)


translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)


DEBUG_LATER_TRANSFORM_INSERT = False


class CleanupCodeInsertInfo:
    def __init__(self):
        self.cleanup_blocks = []
        self.rescue_disablers = []
        self.finally_disablers = []


def _func_sts_end_in_return(sts):
    if type(sts) == list and \
            len(sts) > 0 and \
            type(sts[0]) == str:
        sts = split_toplevel_statements(sts)
    if len(sts) == 0:
        return False
    i = len(sts) - 1
    while (i > 0 and
            is_whitespace_statement(sts[i])):
        i -= 1
    if firstnonblank(sts[i]) == "return":
        return True
    return False


def wrap_later_func_for_global_rescue(
        s, exit_callback_name,
        h64_indent="    ",
        ):
    assert(type(s) == list and (
        len(s) == 0 or type(s[0]) == str))

    orig_indent = get_indent(s)
    if orig_indent == None:
        # It's empty anyway, can't error.
        return s
    new_s = increase_indent(s, added=h64_indent)
    new_s = ([orig_indent, "do", " ", "{", "\n"] +
        new_s +
        [orig_indent, "}", " ", "rescue", " ",
        "any", " ", "as", " ", "e", " ", "{", "\n"])
    if exit_callback_name != None:
        new_s += ([orig_indent + h64_indent,
            "if", " ", exit_callback_name, " ",
            "!=", " ", "none", " ", "{", "\n"])
        new_s += ([orig_indent + h64_indent + h64_indent,
            exit_callback_name, "(", "e", ",",
            "none", ")", "\n"])
        new_s += ([orig_indent + h64_indent + h64_indent,
            "return", "\n"])
        new_s += ([orig_indent + h64_indent, "}", "\n"])
    new_s += ([orig_indent + h64_indent,
        "throw", " ", "e", "\n"])
    new_s += [orig_indent, "}", "\n"]
    return new_s


def wrap_later_func_for_user_rescue(
        s, outer_indent="",
        h64_indent="    ",
        rescue_disablers_pre_descent_len=None,
        finally_disablers_pre_descent_len=None,
        cleanup_code_insert_info=None,
        ):
    assert(type(s) == list and (
        len(s) == 0 or type(s[0]) == str))

    cinfo = cleanup_code_insert_info
    if (cinfo == None or
            len(cinfo.cleanup_blocks) == 0):
        return s

    rescue_disbl_len = rescue_disablers_pre_descent_len
    if rescue_disbl_len is None:
        rescue_disbl_len = len(cinfo.rescue_disablers)
    finally_disbl_len = finally_disablers_pre_descent_len
    if finally_disbl_len is None:
        finally_disbl_len = len(cinfo.finally_disablers)

    func_code_indent = get_indent(s)
    target_inner_indent = outer_indent + h64_indent
    assert(func_code_indent != None)
    if func_code_indent != target_inner_indent:  # Adjust indent:
        #print("TARGET INDENT: '" + str(
        #    target_inner_indent) + "'")
        #print("FUNC INDENT: '" + str(func_code_indent) + "'")
        #print("FUNC:\n" + str(untokenize(s)))
        assert(len(func_code_indent) <
            len(target_inner_indent))
        s = increase_indent(s, added=(
            target_inner_indent[len(func_code_indent):]))
        func_code_indent = target_inner_indent

    # First, wrap in do/rescue:
    had_any_rescue = False
    had_any_finally = False
    old_indent = func_code_indent
    func_code_indent += h64_indent
    i = len(cinfo.cleanup_blocks)
    while i - 1 >= 0:
        i -= 1
        cleanup_block = cinfo.cleanup_blocks[i]
        s = increase_indent(s, added=h64_indent)
        s = [old_indent, "do", " ", "{",
            "\n"] + s
        if cleanup_block[0] != None:
            had_any_rescue = True
            s += ([old_indent, "}", " ", "rescue",
                " "] + cleanup_block[0][2] +
                [" ", "as", " ", "e"])
            s += [" ", "{", "\n"]
            s += [func_code_indent, "if", " ", "not", " ",
                cinfo.rescue_disablers[
                    rescue_disbl_len - 1], " ", "{", "\n"]
            s += [func_code_indent + h64_indent,
                cleanup_block[0][0], "(", "e", ")", "\n"]
            s += [func_code_indent, "}", "\n"]
        if cleanup_block[1] != None:
            had_any_finally = True
            s += [old_indent, "}", " ", "finally",
                " ", "{", "\n"]
            s += [func_code_indent, "if", " ", "not", " ",
                cinfo.finally_disablers[
                    finally_disbl_len - 1], " ", "{", "\n"]
            s += [func_code_indent + h64_indent,
                cleanup_block[1][0], "(", ")", "\n"]
            s += [func_code_indent, "}", "\n"]
        s += [old_indent, "}", "\n"]

    # Second, prepend the new rescue/finally disablers for this level:
    if had_any_rescue:
        assert(cinfo.rescue_disablers[
            rescue_disbl_len - 1] != None)
        s = [old_indent, "var", " ",
            cinfo.rescue_disablers[
            rescue_disbl_len - 1],
            " ", "=", " ", "no", "\n"] + s
    if had_any_finally:
        assert(cinfo.finally_disablers[
            finally_disbl_len - 1] != None)
        s = [old_indent, "var", " ",
            cinfo.finally_disablers[
            finally_disbl_len - 1],
            " ", "=", " ", "no", "\n"] + s

    return s


def add_wrapped_later_call_for_rescue(
        indent, call_name=None,
        call_stmt=None, h64_indent="    ",
        rescue_disablers_pre_descent_len=None,
        finally_disablers_pre_descent_len=None,
        call_error_expr=None,
        call_result_expr=None,
        cleanup_code_insert_info=None,
        let_finally_run=False,
        is_later_ignore=False,
        ):
    assert(type(indent) == str)
    sts = []
    assert((call_stmt != None or call_name != None) and
        (call_stmt == None or call_name == None))
    if (type(call_stmt) == list and len(call_stmt) > 0 and
            type(call_stmt[0]) == list):
        call_stmt = flatten(call_stmt)
    if call_error_expr is None:
        call_error_expr = ["none"]
    if call_result_expr is None:
        call_result_expr = ["none"]
    cinfo = cleanup_code_insert_info
    if (cinfo != None and
            rescue_disablers_pre_descent_len == None):
        rescue_disablers_pre_descent_len = len(
            cinfo.rescue_disablers)
    if (cinfo != None and
            finally_disablers_pre_descent_len == None):
        finally_disablers_pre_descent_len = len(
            cinfo.finally_disablers)

    # Add the actual call:
    return_stmt = [indent, "return", "\n"]
    if is_later_ignore:
        return_stmt = None
    if call_stmt != None:
        if _func_sts_end_in_return(call_stmt):
            assert(not is_later_ignore)
            # Our call already has a return. Extract it:
            i = len(call_stmt) - 1
            while i > 0 and call_stmt[i] != "return":
                i -= 1
            if call_stmt[i] == "return":
                return_stmt = [indent] + call_stmt[i:]
                i -= 1  # Go to before 'return'.
                while i > 0 and is_whitespace_token(call_stmt[i]):
                    i -= 1
                call_stmt = call_stmt[:i + 1] + ["\n"]
        adjusted = adjust_to_absolute_indent(
            call_stmt, indent=indent)
        assert(type(adjusted) == list and (len(adjusted) > 0
            and type(adjusted[0]) == str))
        sts.append(adjusted)
    else:
        sts.append([indent, call_name, "("] +
            call_result_expr + [","] +
            call_error_expr + [")", "\n"])
    if cinfo != None:
        # Disable our rescue and finally handlers:
        rescue_var_idx = rescue_disablers_pre_descent_len
        finally_var_idx = finally_disablers_pre_descent_len
        for cleanup_var in cinfo.rescue_disablers[
                rescue_var_idx - 1:rescue_var_idx]:
            sts.append([indent,
                cleanup_var, " ", "=", " ",
                "yes", "\n"])
        if not let_finally_run:
            for cleanup_var in cinfo.finally_disablers[
                    finally_var_idx - 1:finally_var_idx]:
                sts.append([indent,
                    cleanup_var, " ", "=", " ",
                    "yes", "\n"])
    # Add final return after call:
    if return_stmt != None:
        sts.append(return_stmt)
    return sts


def return_style_call_as_call_stmts(
        name, return_arg_tokens=None, delayed=True,
        indent="", h64_indent="    ",
        callback_delayed_func_name=None,
        ):
    assert(callback_delayed_func_name != None)
    assert(return_arg_tokens != None)
    return_arg_tokens = list(return_arg_tokens)
    while (len(return_arg_tokens) > 0 and
            return_arg_tokens[-1].strip(" \r\t\n") == ""):
        return_arg_tokens = return_arg_tokens[-1]
    if "".join(return_arg_tokens).strip(" \t\r\n") == "":
        return_arg_tokens = ["none"]

    # Now, insert the call:
    call_stmts = []
    if delayed:
        _delayfuncname = "_fdelay" + (
            str(uuid.uuid4()).replace("-", "")
        )
        call_stmts.append(
            [indent] + ["func", " ", _delayfuncname,
            " ", "{", "\n"] +
            [indent] + [h64_indent] + [
            name, "(", "none", ","] +
            return_arg_tokens + [")", "\n"] +
            [indent] + ["}", "\n"]
        )
        delayed_call_tokens = callback_delayed_func_name
        if type(delayed_call_tokens) == str:
            delayed_call_tokens = tokenize(
                delayed_call_tokens
            )
        call_stmts.append(
            [indent] +
            delayed_call_tokens +
            ["(", _delayfuncname, ",", "[", "]", ")", "\n"]
        )
        call_stmts.append(
            [indent] + ["return", "\n"])
    else:
        call_stmts.append([indent] +
            [name, "("] +
            ["none", ","] + return_arg_tokens + [")", "\n"])
        call_stmts.append(
            [indent] + ["return", "\n"]
        )
    return call_stmts


def transform_later_to_closure_funccontents(
        sts, h64_indent="    ",
        outer_callback_name=None,
        callback_delayed_func_name=None,
        await_error_name=None,
        closest_scope_later_func_name=None,
        cleanup_code_insert_info=None,
        ignore_erroneous_code=True,
        ):
    # XXX: outer_callback_name and callback_delayed_func_name
    # are None if we're inside a func only using 'later ignore'.
    # Otherwise they must be set.

    new_sts = []
    st_idx = -1
    for st in sts:
        st_idx += 1
        assert(type(st) == list and
            len(st) == 0 or type(st[0]) == str)
        st = list(st)
        st_orig = list(st)

        # First, handle any 'return'/'return later':
        if (firstnonblank(st) == "return" and
                outer_callback_name != None):
            # (outer_callback_name set when we're in a function
            # with true 'later' use, not just 'later ignore'!)

            # Extact all needed info first:
            wrap_in_delay = False
            i = firstnonblankidx(st)
            returnidx = i
            if nextnonblank(st, i) == "later":
                wrap_in_delay = True
                i = nextnonblankidx(st, i)
            if outer_callback_name != None:
                wrap_in_delay = True
            i += 1
            return_arg = st[i:]
            while (len(return_arg) > 0 and
                    return_arg[-1].strip(" \r\t\n") == ""):
                return_arg = return_arg[:-1]
            indent_tokens = st[:returnidx]
            indent = "".join(indent_tokens)
            _delayfuncname = None

            # Now, insert the call:
            call_stmts = return_style_call_as_call_stmts(
                outer_callback_name,
                return_arg_tokens=return_arg,
                delayed=wrap_in_delay,
                indent=indent, h64_indent=h64_indent,
                callback_delayed_func_name=
                    callback_delayed_func_name)
            if cleanup_code_insert_info:
                # Nothing special here, just add the call:
                new_sts += call_stmts
            else:
                call_stmts = (add_wrapped_later_call_for_rescue(
                    "".join(indent_tokens),
                    call_stmt=call_stmts,
                    h64_indent=h64_indent,
                    rescue_disablers_pre_descent_len=None,  # All.
                    finally_disablers_pre_descent_len=None,  # All.
                    cleanup_code_insert_info=
                        cleanup_code_insert_info,
                    let_finally_run=True,  # Return = bail! It's ok.
                ))
                assert(type(call_stmts) == list and
                    (len(call_stmts) == 0 or
                    type(call_stmts[0]) == list))
                new_sts += call_stmts
            continue

        # Then, handle 'do'/'rescue':
        if firstnonblank(st) == "do":
            rescueidx = token_outside_brackets_idx(
                st, "rescue", startidx=firstnonblankidx(st) + 1
            )
            rescue_expr = None
            rescue_lbl = None
            if rescueidx >= 0:
                k = nextnonblankidx(st, rescueidx)
                korig = k
                bdepth = 0
                while k < len(st) and (
                        k == 0 or  # (=the expr non-blank start)
                        (st[k] != "as" and st[k] != "{") or
                        bdepth > 0 or
                        is_h64op_with_righthand(st[k - 1])):
                    if st[k] in {"{", "[", "("}:
                        bdepth += 1
                    if st[k] in {"}", "]", ")"}:
                        bdepth -= 1
                    k += 1
                if k >= len(st) or not st[k] in {"as", "{"}:
                    if not ignore_erroneous_code:
                        raise ValueError("Failed to parse 'do' "
                            "statement, its 'rescue' block is faulty.")
                    new_sts.append(st)
                    continue
                rescue_expr = st[korig:k]
                if st[k] == "as":
                    rescue_lbl = nextnonblank(st, k)
            finallyidx = token_outside_brackets_idx(
                st, "finally", startidx=firstnonblankidx(st) + 1
            )
            if ((rescueidx < 0 and finallyidx < 0) or
                    not stmt_inner_blocks_use_later(st,
                        including_later_ignore=False)):
                # Good, not much to do. However, we still have to
                # transform our insides (they might still contain
                # 'await' or 'later ignore'):
                ranges = reversed(get_statement_block_ranges(st))
                for brange in ranges:
                    st = (st[:brange[0]] + flatten(
                        transform_later_to_closure_funccontents(
                            split_toplevel_statements(
                                st[brange[0]:brange[1]]
                            ),
                            h64_indent=h64_indent,
                            outer_callback_name=outer_callback_name,
                            callback_delayed_func_name=
                                callback_delayed_func_name,
                            await_error_name=await_error_name,
                            closest_scope_later_func_name=
                                closest_scope_later_func_name,
                            cleanup_code_insert_info=
                                cleanup_code_insert_info,
                            ignore_erroneous_code=
                                ignore_erroneous_code,
                        )) +
                        st[brange[1]:])
                new_sts.append(st)
                continue

            # Rewrite blocks for inclusion inside inner functions:
            blocks = get_statement_block_ranges(st)
            disable_rescue_name = "_rescuedisable_" + str(
                uuid.uuid4()).replace("-", "")
            disable_finally_name = "_finallydisable_" + str(
                uuid.uuid4()).replace("-", "")
            indent_outer = get_indent(st)
            indent_inner = get_indent(st) + h64_indent
            cinfo = cleanup_code_insert_info
            if cinfo is None:
                cinfo = CleanupCodeInsertInfo()
            cinfo_insert = [None, None]
            cinfo_range = [None, None]
            do_range = None
            for brange in blocks:
                if len(brange) >= 3 and brange[2] == "do":
                    do_range = brange
                if len(brange) >= 3 and brange[2] == "rescue":
                    cinfo_insert[0] = (
                        "_rescuefun" + str(
                            uuid.uuid4()).replace("-", ""),
                        increase_indent(
                            st[brange[0]:brange[1]],
                            added=h64_indent),
                        rescue_expr,
                        rescue_lbl)
                    cinfo_range[0] = brange
                if len(brange) >= 3 and brange[2] == "finally":
                    cinfo_insert[1] = (
                        "_finallyfun" +
                            str(uuid.uuid4()).replace("-", ""),
                        increase_indent(
                        st[brange[0]:brange[1]],
                        added=h64_indent))
                    cinfo_range[1] = brange
            if cinfo_insert[0] == None:
                disable_rescue_name = None
            elif cinfo_insert[1] == None:
                disable_finally_name = None
            cinfo.cleanup_blocks.append(cinfo_insert)
            if disable_rescue_name != None:
                cinfo.rescue_disablers.append(disable_rescue_name)
            if disable_finally_name != None:
                cinfo.finally_disablers.append(disable_finally_name)
            cleanup_code_insert_info = cinfo

            # We want to call into our prepared functions with 'if'
            # guards rather than the original 'rescue'/... code,
            # change that in our blocks:
            if cinfo_insert[1] != None:
                # 'finally' first, since it's later and this shifts
                # indexes:
                assert(disable_finally_name != None)
                _st = (st[:cinfo_range[1][0]])
                _st += [indent_inner, "if",
                    " ", "not", disable_finally_name, " ", "{",
                    "\n", indent_inner + h64_indent,
                    cinfo_insert[1][0],
                    "(", ")", "\n",
                    indent_inner, "}", "\n"]
                _st += st[cinfo_range[1][1]:]
                st = _st
            if cinfo_insert[0] != None:
                # Now 'rescue':
                assert(disable_rescue_name != None)
                _st = (st[:cinfo_range[0][0]])
                _st += [indent_inner, "if",
                    " ", "not", disable_rescue_name, " ", "{",
                    "\n", indent_inner + h64_indent,
                    cinfo_insert[0][0], "("]
                _st += [rescue_lbl if rescue_lbl != None else "none"]
                _st += [")", "\n", indent_inner, "}", "\n"]
                _st += st[cinfo_range[0][1]:]
                st = _st

            # Process our 'do' block now, last, since it has lowest
            # indexes:
            if do_range != None:
                do_block_sts = split_toplevel_statements(
                    st[do_range[0]:do_range[1]]
                )
                do_block_indent = get_indent(do_block_sts)
                if do_block_indent == None:
                    do_block_indent = indent_outer + h64_indent

                # Also, insert our 'rescue'/'finally' original code (that
                # we replaced above with calls) as new closure definitions.
                # We can do that right after 'do'/inside our block,
                # since due to scope rules they aren't supposed to access
                # anything later inside the do { ... } block anyway.
                added_sts = []
                if cinfo_insert[0] != None:  # 'rescue' func.
                    name = cinfo_insert[0][0]
                    code = cinfo_insert[0][1]
                    new_temp_name = ("_assignfunc" +
                        str(uuid.uuid4()).replace("-", ""))
                    added_sts.append([
                        do_block_indent, "func", " ",
                        new_temp_name, " ", "("] + ([
                            rescue_lbl] if rescue_lbl != None else
                            ["_unused" + str(uuid.uuid4()).
                                replace("-", "")]) +
                        [")", " ", "{", "\n"] +
                        adjust_to_absolute_indent(code,
                            indent=(do_block_indent + h64_indent)) +
                        ["\n", do_block_indent, "}", "\n"]
                    )
                    added_sts.append([
                        do_block_indent, name, " ",
                        "=", " ", new_temp_name, "\n"
                    ])
                if cinfo_insert[1] != None:  # 'finally' func.
                    name = cinfo_insert[1][0]
                    code = cinfo_insert[1][1]
                    new_temp_name = ("_assignfunc" +
                        str(uuid.uuid4()).replace("-", ""))
                    added_sts.append([
                        do_block_indent, "func", " ",
                        new_temp_name, " ", "{", "\n"] +
                        adjust_to_absolute_indent(code,
                            indent=(do_block_indent + h64_indent)) +
                        ["\n", do_block_indent, "}", "\n"]
                    )
                    added_sts.append([
                        do_block_indent, name, " ",
                        "=", " ", new_temp_name, "\n"
                    ])


                do_block_sts = added_sts + do_block_sts
                # Do actual transformation & reinsert of do block:
                st = (st[:do_range[0]] + flatten(
                    transform_later_to_closure_funccontents(
                        do_block_sts,
                        h64_indent=h64_indent,
                        outer_callback_name=outer_callback_name,
                        callback_delayed_func_name=
                            callback_delayed_func_name,
                        await_error_name=await_error_name,
                        closest_scope_later_func_name=
                            closest_scope_later_func_name,
                        cleanup_code_insert_info=
                            cleanup_code_insert_info,
                        ignore_erroneous_code=
                            ignore_erroneous_code,
                    )) +
                    st[do_range[1]:])
                # Done with do block.

            # Insert the result along with our new required vars:
            if cinfo_insert[0] != None:
                new_sts.append([indent_outer, "var", " ",
                    cinfo_insert[0][0], "\n"])
            if cinfo_insert[1] != None:
                new_sts.append([indent_outer, "var", " ",
                    cinfo_insert[1][0], "\n"])
            if disable_rescue_name != None:
                new_sts.append([indent_outer, "var", " ",
                    disable_rescue_name, " ", "=", " ", "no", "\n"])
            if disable_finally_name != None:
                new_sts.append([indent_outer, "var", " ",
                    disable_finally_name, " ", "=", " ", "no", "\n"])
            new_sts.append(st)
            continue

        # Then, handle 'await's:
        if firstnonblank(st) == "await":
            if await_error_name is None:
                if not ignore_erroneous_code:
                    raise ValueError("Found 'await' "
                        "in forbidden location.")
                new_sts.append(st)
                continue
            indent_tokens = st[:firstnonblankidx(st)]
            new_sts.append(
                indent_tokens + ["if", " ",
                await_error_name, " ", "!=", " ", "none", " ",
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
                st = (st[:brange[0]] + flatten(
                    transform_later_to_closure_funccontents(
                        split_toplevel_statements(
                            st[brange[0]:brange[1]]
                        ),
                        h64_indent=h64_indent,
                        outer_callback_name=outer_callback_name,
                        callback_delayed_func_name=
                            callback_delayed_func_name,
                        await_error_name=await_error_name,
                        closest_scope_later_func_name=
                            closest_scope_later_func_name,
                        cleanup_code_insert_info=
                            cleanup_code_insert_info,
                        ignore_erroneous_code=
                            ignore_erroneous_code,
                    )) +
                    st[brange[1]:])
            new_sts.append(st)
            continue

        # Now we should have just one 'later' left if the
        # code is valid in the first place:
        later_index = later_indexes[0]
        if (not nextnonblank(st, later_index) in {
                ":", "repeat", "ignore"} or
                nextnonblank(st, later_index, no=2) != ""):
            if not ignore_erroneous_code:
                raise ValueError("Found invalid 'later' "
                    "not followed by ':' or 'repeat'.")
            new_sts.append(st)
            continue
        is_a_repeat = (nextnonblank(st, later_index) == "repeat")
        is_an_ignore = (nextnonblank(st, later_index) == "ignore")

        # Store info we will need later:
        rescue_disablers_OUTERCALL_len = None
        finally_disablers_OUTERCALL_len = None
        rescue_disablers_INNERFUNC_len = None
        finally_disablers_INNERFUNC_len = None
        disable_rescue_name = None
        disable_finally_name = None
        if cleanup_code_insert_info != None:
            cinfo = cleanup_code_insert_info
            rescue_disablers_OUTERCALL_len = (
                len(cinfo.rescue_disablers)
            )
            finally_disablers_OUTERCALL_len = (
                len(cinfo.finally_disablers)
            )
            disable_rescue_name = ("_rescuedisable1_" +
                str(uuid.uuid4()).replace("-", ""))
            disable_finally_name = ("_finallydisable1_" +
                str(uuid.uuid4()).replace("-", ""))
            cinfo.rescue_disablers.append(disable_rescue_name)
            cinfo.finally_disablers.append(disable_finally_name)
            rescue_disablers_INNERFUNC_len = (
                len(cinfo.rescue_disablers)
            )
            finally_disablers_INNERFUNC_len = (
                len(cinfo.finally_disablers)
            )

        # See where in the 'later'ed call to insert the callback:
        later_preceding_call_close = prevnonblankidx(st, later_index)
        if (later_preceding_call_close < 0 or
                st[later_preceding_call_close] != ")"):
            if not ignore_erroneous_code:
                raise ValueError("Found invalid 'later' "
                    "placed somewhere else than after a ')' of "
                    "a call.")
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
            # First, this isn't allowed with 'later ignore':
            if is_an_ignore:
                if not ignore_erroneous_code:
                    raise ValueError("Found 'later ignore' with "
                        "return value assignment, this is "
                        "forbidden.")
                new_sts.append(st)
                continue
            # Extract name and then get index where to cut it off:
            i2 = firstnonblankidx(st)
            vardef_at_start_idx = i2
            if is_identifier(nextnonblank(st, i2)):
                arg_name = nextnonblank(st, i2)
            i2 += 1  # Go past identifier.
            while i2 < len(st) and st[i2] != '=':
                i2 += 1
            if i2 >= len(st):
                if not ignore_erroneous_code:
                    raise ValueError("Found 'var' with 'later' "
                        "line lacking the expected '='.")
                new_sts.append(st)
                continue
            i2 += 1  # Move past '='.
            while i2 < len(st) and st[i2].strip(" \t\r\n") == "":
                i2 += 1
            if i2 >= len(st):
                if not ignore_erroneous_code:
                    raise ValueError("Found 'var' with 'later' "
                        "line but 'later' isn't after the '=' "
                        "but somewhere earlier, this is invalid.")
                new_sts.append(st)
                continue
            vardef_past_eq_idx = i2

        # Name for our new callback implicitly created by 'later',
        # as well as indent for the 'func ... {' opening line:
        funcname = None
        await_error_name = None
        if not is_a_repeat:
            funcname = "_" + str(uuid.uuid4()).replace("-", "")
            await_error_name = ("_awerr" +
                str(uuid.uuid4()).replace("-", ""))
        indent = get_indent(st)
        inner_indent = None

        # Get all the statements after 'later' to pull into callback:
        func_inner_content_str = (
            untokenize(flatten(sts[st_idx + 1:])))
        func_inner_content_str = h64_indent + (
            ("\n" + h64_indent).join(
                func_inner_content_str.split("\n")
            ))
        func_inner_content = None
        if not is_a_repeat and not is_an_ignore:
            has_await = (stmt_list_uses_await_before_later(
                sts[st_idx + 1:]
            ) is True)  # (can return True, False, None)
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
                        funcname,
                    cleanup_code_insert_info=
                        cleanup_code_insert_info,
                    ignore_erroneous_code=
                        ignore_erroneous_code,
                )
            )
            inner_indent = get_indent(st) + h64_indent
            assert(len(func_inner_lines) == 0 or
                type(func_inner_lines[0]) == list), ("oops, invalid "
                "inner code: " + str(func_inner_lines))

            # If the 'later' is stored in 'var', it NEEDS an 'await',
            # otherwise it MUST NOT have one:
            if arg_name == None and has_await:
                if not ignore_erroneous_code:
                    raise ValueError("Found invalid 'await' "
                        "following a 'later' with no return value.")
                new_sts.append(st)
                continue
            elif arg_name != None and not has_await:
                if not ignore_erroneous_code:
                    raise ValueError("Didn't find valid 'await' "
                        "following a 'later' with a return value.")
                new_sts.append(st)
                continue

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
                if _func_sts_end_in_return(last_line):
                    ends_in_return = True

            # Now flatten function code:
            func_inner_content = flatten(func_inner_lines)

            # Use collected info to wrap this for 'rescue':
            cinfo = cleanup_code_insert_info

            # If new function doesn't have return at the end,
            # add a callback and return to make sure we bail:
            if not ends_in_return:
                call_stmts = return_style_call_as_call_stmts(
                    outer_callback_name,
                    return_arg_tokens=["none"],
                    delayed=True,
                    indent=indent, h64_indent=h64_indent,
                    callback_delayed_func_name=
                        callback_delayed_func_name)
                func_inner_content += flatten(
                    add_wrapped_later_call_for_rescue(
                        inner_indent,
                        call_stmt=call_stmts,
                        h64_indent=h64_indent,
                        rescue_disablers_pre_descent_len=
                            rescue_disablers_INNERFUNC_len,
                        finally_disablers_pre_descent_len=
                            rescue_disablers_INNERFUNC_len,
                        cleanup_code_insert_info=
                            cleanup_code_insert_info,
                        let_finally_run=True,  # End of function! It's ok.
                    ))

            # If not assigned to a 'var' with 'await', bubble up
            # error right at the start:
            if arg_name is None:
                func_inner_content = [
                    inner_indent, "if", " ", await_error_name,
                        " ", "!=", " ", "none", " ", "{", "\n",
                    inner_indent + h64_indent, "throw", " ",
                        await_error_name, "\n",
                    inner_indent, "}", "\n"
                ] + func_inner_content

            # Wrap everything in 'do'/'rescue' if needed:
            func_inner_content = wrap_later_func_for_user_rescue(
                func_inner_content,
                outer_indent=indent,
                h64_indent="    ",
                rescue_disablers_pre_descent_len=
                    rescue_disablers_INNERFUNC_len,
                finally_disablers_pre_descent_len=
                    finally_disablers_INNERFUNC_len,
                cleanup_code_insert_info=
                    cleanup_code_insert_info,
            )

            # Then, wrap it again for global error forward:
            func_inner_content = (
                wrap_later_func_for_global_rescue(
                    func_inner_content, outer_callback_name,
                    h64_indent=h64_indent,
                ))
            # Done assembling function code!
        # Assemble callback statement and add it in:
        new_sts_inserted = 0
        if not is_a_repeat and not is_an_ignore:
            # Add the closure based on all follow-up code:
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
            new_sts_inserted += 1
            new_sts.append(insert_st)
        elif is_an_ignore:
            # Add a closure that takes & ignores the error:
            assert(arg_name is None)
            insert_st = ([indent, "func", " ",
                funcname, " ", "(", await_error_name])
            insert_st += [",", "_unused" +
                str(uuid.uuid4()).replace("-", "")]
            insert_st += [")", " ", "{", "\n"]
            insert_st += [indent + h64_indent,
                "if", " ", await_error_name, " ",
                "!=", " ", "none", " ", "{", "\n"]
            insert_st += [indent + h64_indent + h64_indent,
                "print", "(", '"Unhandled error in '
                '\'later ignore\': "', " ", "+", " ",
                await_error_name, ".", "as_str", "(", ")",
                ")", "\n"]
            insert_st += [indent + h64_indent, "}", "\n"]
            insert_st += [indent, "}", "\n"]
            new_sts_inserted += 1
            new_sts.append(insert_st)

        # If this is a repeat, call back ourselves!
        call_to = funcname
        if is_a_repeat:
            assert(closest_scope_later_func_name != None)
            call_to = closest_scope_later_func_name

        # Now add the call that had the 'later', but stripped off:
        orig_st = list(st)
        if vardef_past_eq_idx != None:
            st = st[vardef_past_eq_idx:
                later_preceding_call_close]
        else:
            st = st[:later_preceding_call_close]
        if (not later_preceding_call_noargs and
                not later_preceding_call_args_have_trailing_comma):
            st += [",", " "]
        st += [call_to] + [")", "\n"]
        new_sts_inserted += 1
        new_sts_added = (
            add_wrapped_later_call_for_rescue(
                indent, call_stmt=st,
                h64_indent=h64_indent,
                rescue_disablers_pre_descent_len=
                    rescue_disablers_OUTERCALL_len,
                finally_disablers_pre_descent_len=
                    finally_disablers_OUTERCALL_len,
                cleanup_code_insert_info=
                    cleanup_code_insert_info,
                is_later_ignore=is_an_ignore))
        new_sts_inserted = len(new_sts_added)
        assert(type(new_sts_added) == list and
            (len(new_sts_added) == 0 or
            type(new_sts_added[0]) == list))
        new_sts += new_sts_added

        # Output some debug info:
        if DEBUG_LATER_TRANSFORM_INSERT:
            print("transform_later_to_closure_funccontents(): " +
                "DID REPLACEMENT FOR STATEMENT:\n" + str(st_orig) +
                "\nINSERTED:\n" +
                str(new_sts[-new_sts_inserted:]))
        #print("ORIGINAL ONE: " + str(orig_st))
        #print("TOKEN WHERE ORIG CALL ENDED: " +
        #    str(later_preceding_call_close))
        #print("ARG START:ARG_END FOR 'later': " +
        #    str(orig_st[arg_start:arg_end]))

        # If this wasn't 'later ignore', don't keep going:
        if not is_an_ignore:
            break

        # Otherwise, keep processing follow-up contents normally:
        continue

    # Make sure we have a proper bail call at the end:
    first_st_indent = None
    if len(new_sts) > 0:
        first_st_indent = get_indent(new_sts[0])
    if first_st_indent != None and \
            cleanup_code_insert_info != None and False:
        new_sts.append([first_st_indent, "ASS2", "\n"])
    return new_sts


def stmt_inner_blocks_use_await_before_later(st):
    ranges = get_statement_block_ranges(st)
    for block_range in ranges:
        sts = split_toplevel_statements(
            st[block_range[0]:block_range[1]]
        )
        result = stmt_list_uses_await_before_later(sts)
        if result != None:
            return result
    return False


def stmt_has_later(st):
    assert(type(st) == list and (
        len(st) == 0 or type(st[0]) == str))
    bdepth = 0
    i = 0
    while i < len(st):
        if st[i] == "later" and bdepth == 0:
            return True
        if st[i] in {"[", "(", "{"}:
            bdepth += 1
        elif st[i] in {"]", ")", "}"}:
            bdepth -=1
        i += 1
    return False


def stmt_list_uses_await_before_later(sts):
    if (type(sts) == list and len(sts) > 0 and
            type(sts[0]) == str):
        sts = split_toplevel_statements(
            sts
        )
    assert(type(sts) == list and (
           len(sts) == 0 or (type(sts[0]) == list and (
           len(sts[0]) == 0 or type(sts[0][0]) == str))))
    for st in sts:
        assert(type(st) == list and
            (len(st) == 0 or type(st[0]) == str))
        if firstnonblank(st) == "func":
            continue
        if firstnonblank(st) == "return":
            continue
        elif stmt_has_later(st):
            return False
        elif firstnonblank(st) == "await":
            return True
        assert(type(st) == list)
        assert(len(st) == 0 or type(st[0]) == str)
        if stmt_inner_blocks_use_await_before_later(st):
            return True
    return None


def stmt_inner_blocks_use_later(
        st, including_later_ignore=True
        ):
    sts = []
    ranges = get_statement_block_ranges(st)
    for block_range in ranges:
        sts = split_toplevel_statements(
            st[block_range[0]:block_range[1]]
        )
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
                            (st[i] == "later" and
                            (including_later_ignore or
                            nextnonblank(st, i + 1)
                            != "ignore"))):
                        return True
                    i += 1
                continue
            assert(type(st) == list)
            assert(len(st) == 0 or type(st[0]) == str)
            if stmt_inner_blocks_use_later(
                    st, including_later_ignore=
                        including_later_ignore
                    ):
                return True
    return False

 
def is_func_a_later_func(
        st, including_later_ignore=False
        ):
    if type(st) == str:
        st = tokenize(St)
    if (type(st) == list and
            len(st) > 0 and type(st[0]) == list):
        st = flatten(st)
    assert(type(st) in {tuple, list})
    assert(len(st) == 0 or type(st[0]) == str)

    if (firstnonblank(st) != "func" or
            not "later" in st):
        return False
    return stmt_inner_blocks_use_later(
        st, including_later_ignore=
            including_later_ignore
    )


def transform_later_to_closure_unnested(
        sts, h64_indent="    ",
        callback_delayed_func_name=None,
        ignore_erroneous_code=True,
        ):
    new_sts = []
    st_idx = -1
    for st in sts:
        st_idx += 1
        st = list(st)
        st_orig = list(st)

        if not is_func_a_later_func(st,
                including_later_ignore=True):
            new_sts.append(st)
            continue
        callback_name = ("_later_cb" +
            str(uuid.uuid4()).replace("-", ""))

        is_true_later_func = (
            is_func_a_later_func(st,
                including_later_ignore=False))

        # Go from 'func' past until arg or code block start:
        i = firstnonblankidx(st)
        if i >= len(st) or st[i] != "func":
            if not ignore_erroneous_code:
                raise ValueError("Failed to find "
                    "'func' in function statement.")
            new_sts.append(st)
            continue
        i += 1  # Past 'func'.
        while i < len(st) and st[i].strip(" \r\n\t") == "":
            i += 1
        if i >= len(st) or not is_identifier(st[i]):
            if not ignore_erroneous_code:
                raise ValueError("Can't find "
                    "'func' name.")
            new_sts.append(st)
            continue
        i += 1  # Past func name.
        arg_start = i
        while (i < len(st) and
                st[i] != "(" and st[i] != "{"):
            i += 1
        if i >= len(st):
            if not ignore_erroneous_code:
                raise ValueError("Didn't find end "
                    "of function arguments.")
            new_sts.append(st)
            continue

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
                if not ignore_erroneous_code:
                    raise ValueError("Didn't find ')' after "
                        "function arguments.")
                new_sts.append(st)
                continue
            i += 1  # Past closing ')'.
            while i < len(st) and st[i].strip(" \r\t\n") == "":
                i += 1
            if i >= len(st) or st[i] != "{":
                if not ignore_erroneous_code:
                    raise ValueError("Failed to find '{' "
                        "to start function code block.")
                new_sts.append(st)
                continue
            code_block_open_bracket = i
        assert(code_block_open_bracket != None)
        if is_true_later_func:
            # This actually behaves async on its own, so we need
            # callback parameter:
            if last_nonkw_arg_end != None:
                # Put it before the keyword args.
                st = (st[:last_nonkw_arg_end] + [",",
                    callback_name] +
                    st[last_nonkw_arg_end:])
            else:
                # No keyword args, just bolt on at the end.
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
        assert(block_range[0] <= block_range[1])
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
                outer_callback_name=(
                    callback_name if is_true_later_func else
                    None),
                cleanup_code_insert_info=None,
                ignore_erroneous_code=
                    ignore_erroneous_code,
            ))
        ends_in_return = False
        if len(inner_code_lines) > 0:
            last_line = inner_code_lines[-1]
            while is_whitespace_statement(last_line):
                inner_code_lines = inner_code_lines[:-1]
                if len(inner_code_lines) <= 0:
                    break
                last_line = inner_code_lines[-1]
            if _func_sts_end_in_return(last_line):
                ends_in_return = True

        # Wrap all func code for global error handling:
        if is_true_later_func:
            inner_code_flat = wrap_later_func_for_global_rescue(
                flatten(inner_code_lines), callback_name,
                h64_indent=h64_indent,
            )
        else:
            # We're only using 'later ignore', no error handling.
            inner_code_flat = flatten(inner_code_lines)

        # Put together a new statement around the code:
        outer_indent = get_indent(st)
        if outer_indent == None:
            outer_indent = ""
        newst = (st[:block_range[0]] +
            inner_code_flat)  # Old "header" + inner code
        if not ends_in_return and is_true_later_func:
            # If new function doesn't have return at the end,
            # add a callback and return to make sure we bail:
            newst += ([inner_indent,
                callback_name, "(",
                "none", ",", "none", ")", "\n",
                inner_indent, "return", "\n"])
        # Add the closing stuff to our func, ensure right indent:
        def _trimindent(_st):
            while len(_st) > 0 and _st[0].strip(" \r\t\n") == "":
                _st = _st[1:]
            return _st
        newst += ([outer_indent] + _trimindent(
            st[block_range[1]:] + ["\n"]))
        # Ok done, add our reformatted function:
        new_sts.append(newst)

        if DEBUG_LATER_TRANSFORM_INSERT:
            print("transform_later_to_closure_funccontents(): " +
                "DID REPLACEMENT FOR STATEMENT:\n" + str(st_orig) +
                "\nINSERTED:\n" +
                str(new_sts[-1:]))
    assert(type(new_sts) == list and
        (len(new_sts) == 0 or (type(new_sts[0]) == list and
        (len(new_sts[0]) == 0 or type(new_sts[0][0]) == str))))
    return new_sts


def transform_later_to_closures(
        s, callback_delayed_func_name=None,
        ignore_erroneous_code=True):
    assert(type(callback_delayed_func_name) in {str, list})
    def do_transform_later(sts):
        return transform_later_to_closure_unnested(
            sts, callback_delayed_func_name=
                callback_delayed_func_name,
            ignore_erroneous_code=ignore_erroneous_code)
    s = tree_transform_statements(s, do_transform_later)
    return s


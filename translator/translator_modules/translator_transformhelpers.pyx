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

#cython: language_level=3, boundscheck=True, infer_types=True, cdivision=True, overflowcheck=False

import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap
import traceback

from translator_syntaxhelpers cimport (
    is_identifier, identifier_or_keyword,
    nextnonblank, nextnonblankidx,
    firstnonblank, firstnonblankidx,
    prevnonblank, prevnonblankidx,
    get_next_token
)
from translator_syntaxhelpers import (
    tokenize, untokenize, get_indent,
    as_escaped_code_string,
    mirror_brackets,
    is_whitespace_token,
    split_toplevel_statements, 
    get_next_statement,
    sanity_check_h64_codestring,
    separate_out_inline_funcs,
    is_h64op_with_righthand,
    is_number_token, find_start_of_call_index_chain
)

from translator_scopehelpers import (
    get_global_standalone_func_names,
)


## This is a helper function to work on a Horse64 func arg list,
## where it'll go to past the last non-positional argument.
## It's meant for the Horse64 subset for Python translation
## where positional args all come before keyword args, which
## isn't required in normal Horse64.
def func_args_find_last_positional(st, i):
    bracketless_args = True  # For inline funcs
    if i < len(st) and st[i] == "(":
        bracketless_args = False
        i += 1
    had_any_positional_arg = False
    current_arg_nonempty = False
    current_arg_had_assign = False
    current_arg_start = i
    last_nonkw_arg_end = i
    bracket_depth = 0
    while True:
        are_at_bail_bracket = False
        if i >= len(st):
            are_at_bail_bracket = True
        else:
            if st[i] in {"(", "{", "["}:
                bracket_depth += 1
                if (st[i] == "{" and bracket_depth <= 1 and
                        i > 0 and
                        not is_h64op_with_righthand(
                            prevnonblank(st, i)) and
                        prevnonblank(st, i) not in {"=", ","}):
                    are_at_bail_bracket = True
            elif st[i] in {")", "}", "]"}:
                bracket_depth -= 1
                if st[i] == ")" and bracket_depth < 0:
                    are_at_bail_bracket = True
        # See if we reached end of arg list, or end of arg:
        if are_at_bail_bracket or (st[i] == "," and
                nextnonblank(st, i) == ")" and
                bracket_depth <= 0):
            if i < len(st) and st[i] == ",":
                inext = nextnonblankidx(st, i)
                st[i] == " "
                i = inext
            if not current_arg_had_assign:
                last_nonkw_arg_end = i
                if current_arg_nonempty:
                    had_any_positional_arg = True
            break
        elif st[i] == "=" and bracket_depth <= 0:
            current_arg_had_assign = True
            current_arg_nonempty = True
        elif st[i] == "," and bracket_depth <= 0:
            if not current_arg_had_assign:
                last_nonkw_arg_end = i
                had_any_positional_arg = True
            current_arg_start = i + 1
            current_arg_had_assign = False
            current_arg_nonempty = False
        elif is_identifier(st[i]):
            current_arg_nonempty = True
        i += 1
    if (i < len(st) and st[i] == ")" and
            not bracketless_args):
        i += 1
    return (last_nonkw_arg_end, had_any_positional_arg, i)


def is_problematic_identifier_name(s,
        h64_problematic_only=False,
        python_problematic_only=False):
    """ Returns True if the identifier is either not valid
    in Horse64 to redeclare like "base", or valid in Horse64
    but going to break after translation in Python like "super"."""
    horse64_nope = {"base"}
    if not python_problematic_only and s in horse64_nope:
        return True
    python_nope = {"super", "class",
        "sorted", "reversed", "len", "def",
        "yield", "async", "elif", "lambda",
        "pass", "await", "global", "globals",
        "locals", "copy", "del", "raise", "True", "False",
        "nonlocal", "str", "dict", "set",
        "object"}
    if not h64_problematic_only and s in python_nope:
        return True
    return False

def transform_h64_with_to_do_rescue(s):
    was_string = False
    tokens = None
    if type(s) != list:
        assert(type(s) == str)
        was_string = True
        s = tokenize(
            s.replace("\r\n", "\n").replace("\r", "\n")
        )
    else:
        s = list(s)  # We need a deep copy, we'll modify it.
    def find_previous_block_opener(pos):
        bdepth = 0
        i = pos - 1
        while i >= 0:
            if s[i] in {"}", ")", "]"}:
                bdepth += 1
            elif s[i] in {"{", "(", "["}:
                bdepth -= 1
                if bdepth < 0 :
                    if s[i] != "{":
                        return None
                    bdepth = 0
                    i2 = i - 1
                    while i2 >= 0 and (s[i2] not in {"func",
                            "do", "if", "with", "type",
                            "for", "enum", "else", "elseif",
                            "finally", "rescue",
                            "var", "const", "="} or
                            bdepth > 0) and bdepth >= 0:
                        if s[i2] in {"}", ")", "]"}:
                            bdepth += 1
                        elif s[i2] in {"{", "(", "["}:
                            bdepth -= 1
                        i2 -= 1
                    if (i2 >= 0 and bdepth >= 0 and
                            s[i2] != "="):
                        return i2
                    return None
            i -= 1
        return None
    new_tokens = []
    current_indent = ""
    i = 0
    slen = len(s)
    while i < slen:
        if s[i].startswith("\n") or s[i].endswith("\n"):
            assert(s[i].strip("\n\r ") == "")
            current_indent = s[i].rpartition("\n")[2]
        elif s[i].endswith(" "):
            assert(s[i].strip(" ") == "")
            current_indent = s[i]
        if s[i] == "with":
            with_idx = i
            in_block_idx = find_previous_block_opener(i)

            # Only supporting 'with' directly in 'func' or inside
            # outer 'do':
            if (in_block_idx == None or
                    s[in_block_idx] not in {"func", "do"} or
                    (s[in_block_idx] == "do" and (
                    find_previous_block_opener(in_block_idx) == None or
                    s[find_previous_block_opener(in_block_idx)] != "func"))):
                raise NotImplementedError("Found a 'with' "
                    "not inside 'func', or 'func'+'do'. "
                    "This is unsupported.")
            block_indent = max(0, len(current_indent) - 4) * " "

            # Get info about the 'do' statement we're in:
            in_do_stmt = (s[in_block_idx] == "do")
            do_inner_code_closing_bracket = None
            finally_kw_idx = None
            finally_first_code_line_idx = None
            finally_code_closing_bracket_idx = None
            rescue_kw_idx = []
            rescue_first_code_line_idx = []
            rescue_code_closing_bracket_idx = []
            past_first_code_line_idx = None
            if in_do_stmt:
                bdepth = 0
                k = in_block_idx + 1
                while (k < slen and (bdepth > 0 or
                        s[k] not in {"do", "if", "func",
                        "type", "import", "var", "const"})):
                    if s[k] in {"(", "{", "["}:
                        bdepth += 1
                    elif s[k] in {")", "}", "]"}:
                        bdepth -= 1
                        if (bdepth == 0 and s[k] == "}" and
                                    nextnonblank(s, k) not in
                                    {"finally", "rescue"}):
                            if do_inner_code_closing_bracket is None:
                                do_inner_code_closing_bracket = k
                            k += 1
                            while s[k].strip(" \t") == "":
                                k += 1
                            if s[k].strip("\r\n") == "":
                                k += 1
                            past_first_code_line_idx = k
                            break
                        elif (bdepth == 0 and s[k] == "}" and
                                nextnonblank(s, k) in {"finally",
                                "rescue"}):
                            if do_inner_code_closing_bracket is None:
                                do_inner_code_closing_bracket = k
                            is_finally = (nextnonblank(s, k) == "finally")
                            k = nextnonblankidx(s, k)
                            if is_finally:
                                finally_kw_idx = k
                            else:
                                rescue_kw_idx.append(k)
                            k += 1
                            while (s[k] != "{" or
                                    prevnonblank(s,k) in ("{", "(", "=",
                                    "+")):
                                k += 1
                            assert(s[k] == "{")
                            k += 1
                            while s[k].strip(" \t") == "":
                                k += 1
                            if s[k].strip("\r\n") == "":
                                k += 1
                            if is_finally:
                                finally_first_code_line_idx = k
                            else:
                                rescue_first_code_line_idx.append(k)
                            assert(bdepth == 0)
                            bdepth = 1
                            while k < slen:
                                if s[k] in {"(", "[", "{"}:
                                    bdepth += 1
                                elif s[k] in {")", "]", "}"}:
                                    bdepth -= 1
                                    if bdepth <= 0:
                                        assert(s[k] == "}")
                                        break
                                k += 1
                            assert(s[k] == "}")
                            if is_finally:
                                finally_code_closing_bracket_idx = k
                            else:
                                rescue_code_closing_bracket_idx.\
                                    append(k)
                            if nextnonblank(s, k) not in ["finally",
                                    "rescue"]:
                                k += 1
                                while s[k].strip(" \t") == "":
                                    k += 1
                                if s[k] == "\n":
                                    k += 1
                                past_first_code_line_idx = k
                                break
                            bdepth = 1
                            continue
                    k += 1
                assert(past_first_code_line_idx != None)

            # Now find with expression and label:
            expr_with = []
            i += 1
            has_later = False
            bdepth = 0
            while i < slen and (
                    bdepth > 0 or s[i] != "as"
                    ):
                if s[i] in {"(", "{", "["}:
                    bdepth += 1
                if s[i] in {")", "}", "]"}:
                    bdepth -= 1
                    assert(bdepth >= 0)
                if s[i] == "later" and bdepth == 0:
                    has_later = True
                    i += 1
                    while i < slen and s[i].strip("\r\n ") == "":
                        i += 1
                    assert(s[i] == "as")
                    break
                expr_with.append(s[i])
                i += 1
            assert(s[i] == "as")
            while (len(expr_with) > 0 and
                    expr_with[0].strip("\r\n ") == ""):
                expr_with = expr_with[1:]
            while (len(expr_with) > 0 and
                    expr_with[-1].strip("\r\n ") == ""):
                expr_with = expr_with[:-1]
            i += 1
            while i < slen and s[i].strip("\r\n ") == "":
                i += 1
            assert(i < slen)
            label_name = s[i]
            i += 1
            while i < slen and s[i].strip("\r\n ") == "":
                i += 1
            assert(s[i] == "{")
            i += 1

            # Now we're at the first token inside the 'with',
            # and we got all the data we need to make this happen.

            append_for_do = []
            if in_do_stmt:
                # First, instrument our pre-existing do's finally clause:
                assert(len(rescue_kw_idx) == 0 or
                    finally_kw_idx == None or
                    finally_kw_idx > rescue_kw_idx[-1])
                assert(do_inner_code_closing_bracket != None)
                insert_tok = [current_indent, "if", " ",
                    label_name, " ", "!=", " ", "none", " ",
                    "and", " ", "has_attr", "(", label_name,
                    ",", "\"close\"", ")", " ", "{", "\n",
                    current_indent + "    ", label_name,
                    ".", "close", "(", ")", "\n",
                    current_indent, "}","\n"]
                if finally_kw_idx != None:
                    assert(s[finally_kw_idx] == "finally")
                    s = s[:finally_first_code_line_idx] +\
                        insert_tok + s[finally_first_code_line_idx:]
                    past_first_code_line_idx += len(insert_tok)
                    slen += len(insert_tok)
                    assert(len(s) == slen)
                else:
                    #print("PRE FINALLY INSERT: " + str(untokenize(s)))
                    finally_kw_idx = past_first_code_line_idx - 1
                    #print("TOK PAST FIRST CODE LINE: " + str(s[finally_kw_idx:]))
                    insert_at = finally_kw_idx
                    while s[insert_at] != "}":
                        insert_at -= 1
                    insert_at += 1
                    finally_kw_idx = insert_at + 1
                    insert_tok2 = [" ", "finally", " ",
                        "{", "\n"] + insert_tok + [current_indent[:-4],
                        "}"]
                    finally_first_code_line_idx = (
                        past_first_code_line_idx + len(insert_tok2) + 1
                    )
                    s = s[:insert_at] +\
                        insert_tok2 + s[insert_at:]
                    slen += len(insert_tok2)
                    past_first_code_line_idx += len(insert_tok2)
                    #print("POST FINALLY INSERT: " + str(untokenize(s)))
                z = len(rescue_kw_idx)
                while z >= 1:
                    z -= 1
                    s = (s[:rescue_first_code_line_idx[z]] +
                        insert_tok +
                        s[rescue_first_code_line_idx[z]:])
                    slen += len(insert_tok)
                    past_first_code_line_idx += len(insert_tok)
                    z2 = z + 1
                    while z2 < len(rescue_kw_idx):
                        rescue_kw_idx[z] += len(insert_tok)
                        rescue_code_closing_bracket_idx[z] += len(
                            insert_tok
                        )
                        z2 += 1
                var_insert = ["var", " ", label_name, "\n",
                    current_indent[:-4]]
                diff = (len(new_tokens) - with_idx)
                assert(s[in_block_idx] == "do")
                assert(new_tokens[in_block_idx + diff] == "do")
                s = s[:in_block_idx] + var_insert +\
                    s[in_block_idx:]
                i += len(var_insert)
                slen += len(var_insert)
                assert(len(s) == slen)
                new_tokens = new_tokens[:in_block_idx + diff] +\
                    var_insert + new_tokens[in_block_idx + diff:]

            assert(s[i].startswith("\n"))
            new_tokens += (["var", " "] if
                not in_do_stmt else []) + [
                label_name, " ", "=", " "] + expr_with
            if has_later:
                new_tokens += [
                    " ", "later", ":", "\n",
                    current_indent, "await", " ",
                    label_name]
            adjust_indent = 0
            if not in_do_stmt:
                new_tokens += ["\n", current_indent,
                    "do", " ", "{"]
            else:
                adjust_indent = -4
            bdepth = 1
            while i < slen:
                if s[i] in {"(", "{", "["}:
                    bdepth += 1
                if s[i] in {")", "}", "]"}:
                    bdepth -= 1
                    if bdepth == 0:
                        break
                if (s[i].strip(" \t") == "" and
                        i > 0 and s[i - 1] == "\n" and
                        adjust_indent < 0):
                    new_tokens.append(s[i][:adjust_indent])
                else:
                    new_tokens.append(s[i])
                i += 1
            assert(s[i] == "}")
            i += 1
            if not in_do_stmt:
                new_tokens += ["}", " ", "finally", " ", "{", "\n",
                    current_indent + "    ",
                    "if", " ", "has_attr", "(", label_name,
                    ",", "\"close\"", ")", " ", "{", "\n",
                    current_indent + "        ",
                    label_name, ".", "close",
                    "(", ")", "\n",
                    current_indent + "    ", "}", "\n",
                    current_indent, "}"]
            else:
                while s[i].strip(" \t") == "":
                    i += 1
                if s[i] == "\n":
                    i += 1
                new_tokens += ["\n", current_indent,
                    "var", " ", "_closevar", " ", "=",
                    " ", label_name, "\n", current_indent,
                    label_name, " ", "=", " ", "none",
                    "\n", current_indent, "_closevar",
                    ".", "close", "(", ")", "\n"]
            continue
        new_tokens.append(s[i])
        i += 1
    if was_string:
        new_tokens = untokenize(new_tokens)
    return new_tokens

def is_isolated_pure_assign(
        t, allow_these_local_globals=None,
        debug=False
        ):
    if type(t) == str:
        t = tokenize(t)
    assert(type(t) == list and (
        len(t) == 0 or type(t[0]) == str))
    if not "=" in t:
        return True
    eqidx = t.index("=")
    assert(eqidx > 0)
    bdepth = 0
    i = eqidx + 1
    starti = i
    while i <= len(t):
        if i >= len(t) or (bdepth == 0 and t[i] == ","):
            if not is_isolated_pure_expression(t[starti:i],
                    allow_these_local_globals=\
                        allow_these_local_globals,
                    debug=debug):
                return False
            starti = i + 1
            i += 1
            continue
        if t[i] in {"(", "[", "{"}:
            bdepth += 1
        elif t[i] in {")", "]", "}"}:
            bdepth -= 1
        i += 1
    return True

def get_declared_local_globals_simple(t):
    names = []
    bdepth = 0
    i = 0
    while i < len(t):
        if t[i] in {"(", "[", "{"}:
            bdepth += 1
            i += 1
            continue
        elif t[i] in {")", "]", "}"}:
            bdepth = max(0, bdepth - 1)
            i += 1
            continue
        elif (bdepth == 0 and
                t[i] in {"const", "var"}):
            nameidx = nextnonblankidx(t, i)
            name = t[nameidx]
            if nextnonblank(t, nameidx) == "=":
                expr_start = nextnonblankidx(t,
                    nextnonblankidx(t, nameidx))
                i = expr_start
                while (i < len(t) and
                        (bdepth > 0 or
                        t[i].strip(" \t\r") != "\n")):
                    if t[i] in {"(", "[", "{"}:
                        bdepth += 1
                    elif t[i] in {")", "]", "}"}:
                        bdepth = max(0, bdepth - 1)
                    i += 1
                if is_isolated_pure_expression(
                        t[expr_start:i]):
                    names.append(name)
        i += 1
    return names

def is_isolated_pure_expression(
        t, allow_these_local_globals=None,
        debug=False
        ):
    if len(t) == 0:
        return True
    known_ops = ["+", "*", "/", "&", "|", "~",
        "and", "or", "-", "not", "^", "**"]

    # Isolate actual expression without whitespace or brackets:
    start_idx = 0
    end_idx = len(t)
    while True:
        while (start_idx < len(t) and
                t[start_idx].strip(" \t\r\n") == ""):
            start_idx += 1
        if start_idx >= end_idx:
            return True
        while (end_idx > 0 and
                end_idx > start_idx and
                t[end_idx - 1].strip(" \t\r\n") == ""):
            end_idx -= 1
        removed_bracket = False
        while (start_idx < len(t) and
                end_idx > start_idx + 1 and
                t[start_idx] == "(" and
                t[end_idx - 1] == ")"):
            start_idx += 1
            end_idx -= 1
            removed_bracket = True
        if not removed_bracket:
            break
    assigned_expr = t[start_idx:end_idx]
    if len(assigned_expr) == 0:
        return True

    # Creating locks can be done early & isolated no problem:
    if "".join(assigned_expr).strip() == "threading.make_lock()":
        return True

    # Handle trailing ops like `-(x)` or `not x`:
    for op in known_ops:
        if assigned_expr[:1] == [op]:
            return is_isolated_pure_expression(
                assigned_expr[1:]
            )

    # Handle combining ops like `x + y`:
    bdepth = 0
    k = 0
    while k < len(assigned_expr):
        if (bdepth == 0 and
                assigned_expr[k] in known_ops):
            return is_isolated_pure_expression(
                assigned_expr[:k],
                allow_these_local_globals=\
                    allow_these_local_globals
            ) and is_isolated_pure_expression(
                assigned_expr[k + 1:],
                allow_these_local_globals=\
                    allow_these_local_globals
            )
        if assigned_expr[k] in {"(", "[", "{"}:
            bdepth += 1
        elif assigned_expr[k] in {")", "]", "}"}:
            bdepth -= 1
        k += 1

    # Handle needless brackets:
    if (len(assigned_expr) >= 2 and
            assigned_expr[0] == "(" and
            assigned_expr[-1] == ")"):
        return is_isolated_pure_expression(
            assigned_expr[1:-1], allow_these_local_globals=\
                allow_these_local_globals
        )

    # Handle local globals if we're allowed:
    if (allow_these_local_globals != None and
            len(assigned_expr) == 1 and
            assigned_expr[0] in allow_these_local_globals):
        return True

    # Handle all the other things we know to be without side
    # effects or dependency:
    if (len(assigned_expr) == 1 and
            len(assigned_expr[0]) >= 1):
        if assigned_expr[0] in {"yes", "no", "none"}:
            return True
        if (ord(assigned_expr[0][0]) >= ord('0') and
                ord(assigned_expr[0][0]) <= ord('9')):
            return True
        if (assigned_expr[0][0] == '-' and
                len(assigned_expr[0]) > 1 and
                ord(assigned_expr[0][1]) >= ord('0') and
                ord(assigned_expr[0][1]) <= ord('9')):
            return True
        if assigned_expr[0][0] in {'"', "'"}:
            return True
    elif (len(assigned_expr) > 1 and
            ((assigned_expr[0] == "[" and
            assigned_expr[-1] == "]") or
            (assigned_expr[0] == "{" and
            assigned_expr[-1] == "}"))):
        bdepth = 0
        item_start = 1
        i = 1
        while i < len(assigned_expr):
            if bdepth == 0 and (assigned_expr[i] == "," or
                    assigned_expr[i] in {"]", "}"}):
                if not is_isolated_pure_expression(
                        assigned_expr[item_start:i],
                        allow_these_local_globals=\
                            allow_these_local_globals):
                    return False
                item_start = i + 1
                if assigned_expr[i] != ",":
                    return True
                i += 1
                continue
            if assigned_expr[i] in {"(", "[", "{"}:
                bdepth += 1
            elif assigned_expr[i] in {")", "]", "}"}:
                bdepth -= 1
            i += 1
        raise ValueError("expression has nesting error")
    return False


def make_string_literal_python_friendly(t):
    was_str = False
    if type(t) == str:
        was_str = True
        t = [t]
    assert(type(t) in {list, tuple})
    is_escaped = False
    result = []
    i = 0
    while i < len(t):
        if (not t[i].startswith("'") and
                not t[i].startswith('"') and
                not t[i].startswith("b'") and
                not t[i].startswith('b"')) or (
                "\n" not in t[i] and
                "\r" not in t[i]):
            result.append(t[i])
            i += 1
            continue
        s = t[i]
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        is_escaped = False
        k = 0
        while k < len(s):
            if s[k] == "\\" and not is_escaped:
                is_escaped = True
                i += 1
                continue
            if s[k] == "\n":
                if is_escaped:
                    is_escaped = False
                    k += 1
                    continue
                s = s[:k] + "\\n" + s[k + 1:]
                k += 2
                continue
            is_escaped = False
            k += 1
        result.append(s)
        i += 1
    if was_str:
        return result[0]
    return result


def transform_h64_misc_inline_to_python(s):
    was_str = False
    if type(s) == str:
        was_str = True
        s = tokenize(s)
    # Translate XYZ.as_str()/XYZ.len to str(XYZ)/len(XYZ),
    # important (!!!) this needs to be BEFORE remapping functions.
    replaced_one = True
    while replaced_one:
        replaced_one = False
        i = 0
        while i < len(s):
            if (s[i] == "copy" and nextnonblank(s, i) == "(" and
                    prevnonblank(s, i) == "." and
                    prevnonblank(s, i, no=2) == "base"):
                base_idx = prevnonblankidx(s,i, no=2)
                bracket_idx = nextnonblankidx(s, i)
                s = s[:base_idx] + ["_translator_runtime_helpers",
                    ".", "_container_copy_on_base", "(", "self",
                    ",", "__h64_cls_ref__"] +\
                    s[bracket_idx + 1:]
                i = bracket_idx + 4
                continue
            elif (s[i] == "copy" and nextnonblank(s, i) == "(" and
                    prevnonblank(s, i) == "." and
                    prevnonblank(s, i, no=2) == ")" and
                    prevnonblank(s, i, no=3) == "(" and
                    prevnonblank(s, i, no=4) == "super"):
                base_idx = prevnonblankidx(s,i, no=4)
                bracket_idx = nextnonblankidx(s, i)
                s = s[:base_idx] + ["_translator_runtime_helpers",
                    ".", "_container_copy_on_base", "(", "self",
                    ",", "__h64_cls_ref__"] +\
                    s[bracket_idx + 1:]
                i = base_idx + 4
                continue
            cmd = None
            if (prevnonblank(s, i) == "." and (
                    s[i] in ("len", "glyph_len") or (
                    s[i] in ("as_str", "as_bytes", "to_num",
                            "as_list", "as_set",
                            "as_hex", "keys", "values") and
                        nextnonblank(s, i) == "(" and
                        nextnonblank(s, i, no=2) == ")") or (
                    s[i] in ("add", "sort", "trim", "find",
                        "ltrim", "pop_at", "rtrim", "rfind", "value",
                        "copy", "add_at",
                        "reverse", "sublast", "subfirst",
                        "last", "first", "del", "insert",
                        "join", "glyph_sub", "sub", "rep") and
                        nextnonblank(s, i) == "("
                    ))):
                cmd = s[i]
            elif (s[i] == "[" and (
                    prevnonblank(s, i) in {")", "]", "}"} or
                    is_identifier(prevnonblank(s, i)) or
                    prevnonblank(s, i)[:1] in {"'", '"'} or
                    prevnonblank(s, i)[:2] in {"b'", 'b"'})):
                cmd = "["
            else:
                i += 1
                continue
            if (s[i] == "join" and
                    prevnonblank(s, i) == "." and
                    prevnonblank(s, i, no=2) == "path"):
                i += 1
                continue
            if (s[i] == "copy" and
                    prevnonblank(s, i) == "." and
                    prevnonblank(s, i, no=2) == "base"):
                i += 1
                continue
            replaced_one = True
            insert_call = ["_translator_runtime_helpers",
                ".", "_value_to_str"]
            if cmd == "len" or cmd == "glyph_len":
                insert_call = ["len"]
            elif cmd == "as_bytes":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_value_as_bytes"]
            elif cmd == "as_hex":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_as_hex"]
            elif cmd == "as_list":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_as_list"]
            elif cmd == "as_set":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_as_set"]
            elif cmd == "values":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_get_values"]
            elif cmd == "keys":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_get_keys"]
            elif cmd == "pop_at":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_pop_at"]
            elif cmd == "insert":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_insert"]
            elif cmd == "copy":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_copy"]
            elif cmd == "del":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_del"]
            elif cmd == "value":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_value"]
            elif cmd == "to_num":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_to_num"]
            elif cmd == "sublast":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_sublast"]
            elif cmd == "subfirst":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_subfirst"]
            elif cmd == "last":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_last"]
            elif cmd == "first":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_first"]
            elif cmd == "add":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_add"]
            elif cmd == "add_at":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_add_at"]
            elif cmd == "join":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_join"]
            elif cmd == "trim":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_trim"]
            elif cmd == "ltrim":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_ltrim"]
            elif cmd == "rtrim":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_rtrim"]
            elif cmd == "rfind":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_rfind"]
            elif cmd == "rep":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_repeat"]
            elif cmd == "sub" or cmd == "glyph_sub":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_sub"]
            elif cmd == "find":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_find"]
            elif cmd == "sort":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_sort"]
            elif cmd == "reverse":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_reverse"]
            elif cmd == "[":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_squarebracketaccess"]
            def is_keyword_or_idf(s):
                if len(s) == 0:
                    return False
                if (s[0] == "_" or(ord(s[0]) >= ord("A") and
                        ord(s[0]) <= ord("Z")) or
                        (ord(s[0]) >= ord("a") and
                        ord(s[0]) <= ord("z"))):
                    return True
                return False
            replaced_one = True
            old_s = s
            if cmd in ("len", "glyph_len"):
                # Add in a ")":
                s = s[:i - 1] + [")"] + s[i + 1:]
                i -= 1
                assert(s[i] == ")")
            elif cmd in ("add", "sort", "join", "find", "sub",
                    "rep", "trim", "glyph_sub", "value", "copy",
                    "ltrim", "rtrim", "rfind", "sublast",
                    "insert", "pop_at", "add_at",
                    "subfirst", "last", "first", "del"):
                # Truncate "(", ... and turn it to ",", ...
                s = s[:i - 1] + [","] + s[i + 2:]
                i -= 1
                assert(s[i] == ",")
            elif cmd == "[":
                # Change the "[" into a ",":
                s = s[:i] + [","] + s[i + 1:]
                # We also need to replace the closing ']' with a ')':
                bracket_depth = 0
                k = i + 2
                while (k < len(s) and (
                        bracket_depth > 0 or
                        s[k] != "]")):
                    if s[k] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif s[k] in {")", "]", "}"}:
                        bracket_depth -= 1
                    k += 1
                if k >= len(s) or s[k] != "]":
                    raise ValueError("invalid code, failed to "
                        "find closing ']' in: " +
                        untokenize(s[i:i + 20]) + "||" + str(s))
                s[k] = ")"
            else:
                # Truncate "(", ")" to leave a ")":
                s = s[:i - 1] + s[i + 2:]
                i -= 1
                assert(s[i] == ")")
            inserted_left_end = False
            bdepth = 0
            i -= 1  # Go before terminating ) or , character
            assert(i >= 0)
            istart = find_start_of_call_index_chain(s, i)
            if istart > i:
                istart = find_start_of_call_index_chain(s, i, debug=True)
            assert(istart <= i), (
                "expression start should be before where we began "
                "searching at " + str(i) + " (token: '" +
                str(s[i]) + "') but it's at " +
                str(istart) + ", expression surroundings: " +
                str(s[min(istart, i) - 10:max(istart, i) + 10]))
            s = s[:istart] + insert_call + ["("] + s[istart:]
            inserted_left_end = True
            assert(inserted_left_end), (
                "FAILED TO FIND LEFT END OF EXPRESSION FOR: " + str(
                "cmd='" + str(cmd) + "', old_s=" + str(old_s) +
                "new_s=" + str(s) + ", i=" + str(i) +
                ", istart=" + str(istart)))
            #print("Transformed for "
            #    "cmd='" + str(cmd) + "', old_s=" + str(olds) +
            #    "new_s=" + str(s) + ", i=" + str(i) +
            #    ", istart=" + str(istart)))
            break
    if was_str:
        return untokenize(s)
    return s

def line_has_multi_stmts_for_sure(s):
    s = tokenize(s)
    hadnonblank = False
    bdepth = 0
    prevnonblankstr = None
    i = 0
    while i < len(s):
        if s[i] in {"(", "[", "{"}:
            bdepth += 1
        elif s[i] in {")", "]", "}"}:
            bdepth -= 1
        if (bdepth == 0 and hadnonblank and
                s[i] in {"var", "const",
                "return", "enum",
                "do", "while", "for", "type",
                "import", "with", "await"} and
                (not s[i] in {"func", "type", "enum"} or
                 prevnonblankstr != "extend")):
            return True
        if s[i].strip(" \r\n\t") != "":
            prevnonblankstr = s[i]
            hadnonblank = True
        i += 1
    return False


def vec_expr_len_if_any(toks, i):
    starti = i
    while i < len(toks) and toks[i].strip(" \t\r\n") == "":
        i += 1
    if i >= len(toks) or toks[i] != "[":
        return None
    found_colon = False
    bdepth = 0
    i += 1
    while i < len(toks) and (
            bdepth > 0 or
            toks[i] != "]"):
        if bdepth == 0 and toks[i] == "->":
            return None
        if bdepth == 0 and toks[i] == ":":
            found_colon = True
        if toks[i] in {"(", "[", "{"}:
            bdepth += 1
        elif toks[i] in {"(", "[", "{"}:
            bdepth -= 1
            if bdepth < 0:
                return None
        i += 1
    if i >= len(toks) or toks[i] != "]" or not found_colon:
        return None
    return i - starti + 1


def apply_make_vec_call(expr):
    vec_len = vec_expr_len_if_any(expr, 0)
    if vec_len is None:
        return list(expr)
    expr = list(expr)
    i = firstnonblankidx(expr)
    assert(expr[i] == "[" and expr[vec_len - 1] == "]")
    expr[i] = "{"
    expr[vec_len - 1] = "}"
    named_entry = ["x", "y", "z", "w"]
    k = i + 1
    while k < vec_len - 1:
        if expr[k] in named_entry:
            expr[k] = str(1 + named_entry.index(expr[k]))
        k += 1
    return (["_translator_runtime_helpers",
        ".", "_make_vec", "(", "{"] +
        expr[i + 1:vec_len - 1] + ["}", ")"])


def set_expr_len_if_any(toks, i):
    starti = i
    while i < len(toks) and toks[i].strip(" \t\r\n") == "":
        i += 1
    if i >= len(toks) and toks[i] != "{":
        return None
    if prevnonblank(toks, i) == "else":
        return None
    bdepth = 0
    i += 1
    while i < len(toks) and (
            bdepth > 0 or
            toks[i] != "}"):
        if bdepth == 0 and (
                toks[i] == "->" or toks[i] == ":"
                ):
            return None
        if toks[i] in {"(", "[", "{"}:
            bdepth += 1
        elif toks[i] in {"(", "[", "{"}:
            bdepth -= 1
            if bdepth < 0:
                return None
        i += 1
    if i >= len(toks) or toks[i] != "}" or (
            nextnonblank(toks, i) == "else"):
        return None
    return i - starti + 1


def apply_make_set_call(expr):
    set_len = set_expr_len_if_any(expr, 0)
    if set_len is None:
        return list(expr)
    i = firstnonblankidx(expr)
    assert(expr[i] == "{")
    return (["_translator_runtime_helpers",
        ".", "_make_set", "(", "["] +
        expr[i + 1:set_len - 1] + ["]", ")"])


def indent_sanity_check(s, what_in="unknown code"):
    if type(s) == list:
        s = untokenize(s)
    assert(type(s) == str)

    def maybe_line_comment(s):
        return ("#" in s)

    # Dumb helper function for at least obvious cases:
    def starts_with_statement_for_sure(s, prev_s):
        if maybe_line_comment(s) or maybe_line_comment(prev_s):
            return False
        s = s.replace("\t", " ")
        s = s.replace("\n", " ")
        s = s.replace("\t", " ")
        prev_s = prev_s.replace("\t", " ")
        prev_s = prev_s.replace("\n", " ")
        prev_s = prev_s.replace("\t", " ")
        if (s.startswith(")") or s.startswith("}") or
                s.startswith("]")):
            return False
        if (s.startswith("var ") or
                s.startswith("const ") or
                s.startswith("do ") or
                s.startswith("for ") or
                s.startswith("return ") or
                s.startswith("with ") or
                s.startswith("await ") or
                s.startswith("type ") or
                s.startswith("import ")):
            return True
        if prev_s.endswith(":"):
            return True
        if prev_s.endswith(" repeat"):
            return True
        return False
    def expected_indent_direction_after(s):
        if (s.startswith("do ") or
                s.startswith("func ") or
                s.startswith("with ") or
                s.startswith("type ")):
            return 1
        if (s.startswith("var ") or
                s.startswith("return ") or
                s.startswith("const ") or
                s.startswith("import ") or
                s.endswith("repeat") or
                s.startswith("await ")
                ):
            return 0
        if s.strip() in {"}", "]", ")"}:
            return -1
        return None

    slines = s.splitlines()
    prev_line = ""
    prev_prev_s = ""
    prev_s = ""
    _future_prev_indent = ""
    _future_prev_s = ""
    i = -1
    for sline in slines:
        i += 1
        if sline.strip() == "":
            continue
        prev_indent = _future_prev_indent
        prev_prev_s = prev_s
        prev_s = _future_prev_s
        indent = get_indent(sline)
        if indent is None:
            indent = ""
        s = sline.lstrip()
        _future_prev_indent = indent
        _future_prev_s = s

        # Do some wild heuristic guesses:
        shift_actual = len(indent) - len(prev_indent)
        if (shift_actual >= 0 and (
                s.startswith(")") or
                s.startswith("]") or
                s.startswith("}")) and
                (starts_with_statement_for_sure(prev_s, prev_prev_s) or
                prev_s in (")", "]", "}")) and
                not prev_s.endswith(mirror_brackets(s[:1]))):
            raise ValueError("in " + str(what_in) + ", " +
                "line " + str(i + 1) + ": " +
                "expected indent to decrease to last line, " +
                "but it changed by " + str(shift_actual) +
                " character(s)"
            )
        if prev_s == "}" and shift_actual > 0:
            raise ValueError("in " + str(what_in) + ", " +
                "line " + str(i + 1) + ": " +
                "expected indent not increase to last line, " +
                "but it changed by " + str(shift_actual) +
                " character(s)"
            )
        if line_has_multi_stmts_for_sure(s):
            raise ValueError("in " + str(what_in) + ", " +
                "line " + str(i + 1) + ": " +
                "indentation error, please write multiple "
                "statements separated in multiple "
                "lines. affected line: " + str(s)
            )
        if not starts_with_statement_for_sure(s, prev_s):
            continue
        shift_expect = expected_indent_direction_after(prev_s)
        if (shift_expect != None and
                shift_expect == 0 and shift_actual != 0):
            raise ValueError("in " + str(what_in) + ", " +
                "line " + str(i + 1) + ": " +
                "expected indent to remain same to last line, " +
                "but it changed by " + str(shift_actual) +
                " character(s)"
            )
        if (shift_expect != None and
                shift_expect > 0 and shift_actual < 0):
            raise ValueError("in " + str(what_in) + ", " +
                "line " + str(i + 1) + ": " +
                "expected indent to if at all increase after "
                "last line, " +
                "but it decreased by " + str(-shift_actual) +
                " character(s)"
            )
        if (shift_expect != None and
                shift_expect < 0 and shift_actual > 0):
            raise ValueError("in " + str(what_in) + ", " +
                "line " + str(i + 1) + ": " +
                "expected indent to if at all decrease after "
                " last line, " +
                "but it increased by " + str(shift_actual) +
                " character(s)"
            )


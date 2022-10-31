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


import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap
import traceback


from translator_syntaxhelpers import (
    tokenize, untokenize, get_indent,
    is_identifier, as_escaped_code_string,
    mirror_brackets,
    is_whitespace_token, get_next_token,
    split_toplevel_statements, nextnonblank,
    nextnonblankidx,
    firstnonblank, firstnonblankidx,
    get_next_statement, prevnonblank, prevnonblankidx,
    sanity_check_h64_codestring,
    separate_out_inline_funcs,
    identifier_or_keyword, is_h64op_with_righthand,
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
                if (st[i] == "{" and bracket_depth == 1 and
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
                inext = nextnonblank(st, i)
                st[i] == " "
                i = inext
            if not current_arg_had_assign:
                last_nonkw_arg_end = i
                if current_arg_nonempty:
                    had_any_positional_arg = True
            break
        elif st[i] == "=" and bracket_depth <= 1:
            current_arg_had_assign = True
            current_arg_nonempty = True
        elif st[i] == "," and bracket_depth <= 1:
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


def is_isolated_pure_assign(t):
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
            if not is_isolated_pure_expression(t[starti:i]):
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


def is_isolated_pure_expression(t):
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
                assigned_expr[:k]
            ) and is_isolated_pure_expression(
                assigned_expr[k + 1:]
            )
        if assigned_expr[k] in {"(", "[", "{"}:
            bdepth += 1
        elif assigned_expr[k] in {")", "]", "}"}:
            bdepth -= 1
        k += 1

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
                        assigned_expr[item_start:i]):
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
            cmd = None
            if (prevnonblank(s, i) == "." and (
                    s[i] in ("len", "glyph_len") or (
                    s[i] in ("as_str", "as_bytes", "to_num",
                            "as_hex") and
                        nextnonblank(s, i) == "(" and
                        nextnonblank(s, i, no=2) == ")") or (
                    s[i] in ("add", "sort", "trim", "find",
                        "ltrim", "rtrim", "rfind", "copy",
                        "reverse", "sublast", "subfirst",
                        "last", "first", "del", "insert",
                        "join", "glyph_sub", "sub", "repeat") and
                        nextnonblank(s, i) == "("
                    ))):
                cmd = s[i]
            elif (s[i] == "[" and (
                    prevnonblank(s, i) in {")", "]", "}"} or
                    is_identifier(prevnonblank(s, i)))):
                cmd = "["
            else:
                i += 1
                continue
            replaced_one = True
            insert_call = ["_translator_runtime_helpers",
                ".", "_value_to_str"]
            if cmd == "len" or cmd == "glyph_len":
                insert_call = ["len"]
            elif cmd == "as_bytes":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_value_to_bytes"]
            elif cmd == "as_hex":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_as_hex"]
            elif cmd == "insert":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_insert"]
            elif cmd == "copy":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_copy"]
            elif cmd == "del":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_del"]
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
            elif cmd == "repeat":
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
                    "repeat", "trim", "glyph_sub", "copy",
                    "ltrim", "rtrim", "rfind", "sublast",
                    "insert",
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
                "cmd='" + str(cmd) + "', old_s=" + str(olds) +
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
    i = 0
    while i < len(s):
        if s[i] in {"(", "[", "{"}:
            bdepth += 1
        elif s[i] in {")", "]", "}"}:
            bdepth -= 1
        if (bdepth == 0 and hadnonblank and
                s[i] in {"var", "const",
                "return",
                "do", "while", "for", "type",
                "import", "with", "await"}):
            return True
        if s[i].strip(" \r\n\t") != "":
            hadnonblank = True
        i += 1
    return False


def indent_sanity_check(s, what_in="unknown code"):
    if type(s) == list:
        s = untokenize(s)
    assert(type(s) == str)

    # Dumb helper function for at least obvious cases:
    def starts_with_statement_for_sure(s, prev_s):
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
                s.startswith("type ") or
                s.startswith("if ")):
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
                "statements with same indentation in multiple "
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
                " last line, " +
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


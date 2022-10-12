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

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)


def is_keyword(x):
    if x in {"if", "func", "import", "else",
            "type", "do", "rescue", "finally",
            "from", "as", "extends", "protect",
            "var", "const", "elseif", "while",
            "for", "in", "not", "and", "or"}:
        return True
    return False


def identifier_or_keyword(x):
    if x == "" or type(x) != str:
        return False
    i = 0
    while i < len(x):
        if (x[i] != "_" and
                (ord(x[i]) < ord("a") or ord(x[i]) > ord("z")) and
                (ord(x[i]) < ord("A") or ord(x[i]) > ord("Z")) and
                (ord(x[i]) < ord("0") or ord(x[i]) > ord("9")
                 or i == 0) and
                ord(x[i]) <= 127):
            return False
        i += 1
    return True


def is_identifier(v):
    return (identifier_or_keyword(v) and
        not is_keyword(v))


def as_escaped_code_string(s):
    insert_value = "(b\""
    bytes_path = s.encode(
        "utf-8", "replace"
    )
    for byteval in bytes_path:
        assert(byteval >= 0 and byteval <= 255)
        if ((byteval >= ord("a") and byteval <= ord("z")) or
                (byteval >= ord("A") and byteval <= ord("Z")) or
                (byteval >= ord("0") and byteval <= ord("9")) or
                chr(byteval) in {"/", ".", " ", "-", "!", "?",
                    ":", "_"}):
            insert_value += chr(byteval)
            continue
        insert_value += "\\" + (
            "x%0.2X" % byteval
        )
    insert_value += "\").decode(\"utf-8\", \"replace\")"
    return insert_value


def is_whitespace_token(s):
    if len(s) == 0:
        return False
    for char in s:
        if char not in [" ", "\t", "\n", "\r"]:
            return False
    return True


def get_next_token(s):
    assert(type(s) == str)
    if s == "":
        return ""
    len_s = len(s)

    if s[:2] == "->":
        return "->"
    if (s[0] == "'" or s[0] == '"' or
            (s[0] == 'b' and len_s > 1 and (
            s[1] == "'" or s[1] == '"'))):
        end_marker = s[0]
        i = 1
        if end_marker == "b":
            end_marker = s[1]
            i = 2
        next_escaped = False
        while i < len_s:
            if s[i] == '\\':
                if next_escaped:
                    next_escaped = False
                    i += 1
                    continue
                next_escaped = True
                i += 1
                continue
            if s[i] == end_marker and not next_escaped:
                next_escaped = False
                i += 1
                break
            next_escaped = False
            i += 1
        return s[:i]
    if s[0] == "#":
        i = 1
        while i < len_s and s[i] not in {"\n", "\r"}:
            i += 1
        result = " " * i
        if i < len_s and s[i] in {"\n", "\r"}:
            result += s[i]
            i += 1
            if s[i - 1] == "\n" and i < len_s and s[i] == "\r":
                result += s[i]
                i += 1
        return result
    if s[0] in {"\n", "\r"}:
        i = 1
        if s[i - 1] == "\n" and i < len_s and s[i] == "\r":
            i += 1
        return s[:i]
    if s[0] in {" ", "\t"}:
        i = 1
        while i < len_s and s[i] in {" ", "\t"}:
            i += 1
        if i < len_s and s[i] in {"\n", "\r"}:
            i += 1
            if s[i - 1] == "\n" and i < len_s and s[i] == "\r":
                i += 1
        return s[:i]
    if s[0] in {"{", "}", "(", ")", "[", "]"}:
        return s[0]
    if (ord(s[0]) >= ord("0") and ord(s[0]) <= ord("9")) or \
            (s[0] == "-" and 1 < len_s and
            (ord(s[1]) >= ord("0") and ord(s[1]) <= ord("9"))):
        i = 1
        while i < len_s and (
                (ord(s[i]) >= ord("0") and ord(s[i]) <= ord("9"))):
            i += 1
        if i < len_s and s[i] == ".":
            i += 1
            while i < len_s and (
                    (ord(s[i]) >= ord("0") and ord(s[i]) <= ord("9"))):
                i += 1
        return s[:i]
    if s[0] == ":":
        return ":"
    if s[0] in {">", "=", "<", "!", "+", "-", "/", "*",
            "%", "|", "^", "&", "~"}:
        if s[1:2] in ["="]:
            return s[:2]
        return s[:1]
    if (ord(s[0]) >= ord("a") and ord(s[0]) <= ord("z")) or \
            (ord(s[0]) >= ord("A") and ord(s[0]) <= ord("Z")) or \
            s[0] == "_":
        i = 1
        while i < len_s and (
                (ord(s[i]) >= ord("a") and ord(s[i]) <= ord("z")) or
                (ord(s[i]) >= ord("A") and ord(s[i]) <= ord("Z")) or
                (ord(s[i]) >= ord("0") and ord(s[i]) <= ord("9")) or
                s[i] == "_"):
            i += 1
        return s[:i]
    return s[:1]


def get_statement_ranges_ex(t,
        range_type="expr"):
    result = []
    assert(type(t) in {list, tuple})
    i = 0
    while (i < len(t) and
            t[i].strip(" \r\n\t") == ""):
        i += 1
    if i >= len(t):
        return []
    if (t[i] in {"type"}):
        if range_type == "block":
            while (i < len(t) and
                    t[i] != "{"):
                i += 1
            if i >= len(t) or t[i] != "{":
                return []
            i += 1
            block_start = i
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "}" or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t) or t[i] != "}":
                return []
            return [[block_start, i]]
        elif range_type == "expr":
            while (i < len(t) and
                    t[i] != "{" and
                    t[i] != "extends"):
                i += 1
            if i >= len(t) or t[i] != "extends":
                return []
            i += 1  # Past 'extends' kw.
            while i < len(t) and t[i].strip(" \r\n\t") == "":
                i += 1
            had_nonwhitespace = False
            expr_start = i
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "{" or
                    bracket_depth > 0 or
                    not had_nonwhitespace)):
                if t[i].strip(" \r\n\t") != "":
                    had_nonwhitespace = True
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t) or t[i] != "{":
                return []
            return [[expr_start, i]]
        return []
    if (t[i] in {"func", "while", "for",
            "do", "with", "if"}):
        stmt_type = t[i]
        i += 1  # Past statement's main keyword.
        if stmt_type != "if" and stmt_type != "while":
            # (For "if"/"while", keep whitespace in expression.)
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
        if (stmt_type == "do" and
                range_type == "block"):
            if t[i] != "{":
                return []
            i += 1  # Past '{' opening bracket.
            block_start = i
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "}" or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i > len(t) or t[i] != "}":
                return []
            result.append([block_start, i])
            i += 1  # Past '}' closing bracket.
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            if i >= len(t):
                return result
            if t[i] == "rescue":
                i += 1  # Past 'rescue' keyword.
                saw_nonwhitespace = False
                bracket_depth = 0
                while (i < len(t) and
                        ((t[i] != "as" and
                        (t[i] != "{" or not saw_nonwhitespace) or
                        bracket_depth > 0))):
                    if t[i] in {"[", "(", "{"}:
                        bracket_depth += 1
                    elif t[i] in {"]", ")", "}"}:
                        bracket_depth -= 1
                    if t[i].strip(" \r\n\t") != "":
                        saw_nonwhitespace = True
                    i += 1
                if t[i] == "as":
                    bracket_depth = 0
                    while (i < len(t) and
                            (t[i] != "{" or
                            bracket_depth > 0)):
                        if t[i] in {"[", "(", "{"}:
                            bracket_depth += 1
                        elif t[i] in {"]", ")", "}"}:
                            bracket_depth -= 1
                        i += 1
                if i >= len(t):
                    return result
                assert(t[i] == "{")
                i += 1  # Past '{' opening bracket.
                block_start = i
                bracket_depth = 0
                while (i < len(t) and
                        (t[i] != "}" or
                        bracket_depth > 0)):
                    if t[i] in {"[", "(", "{"}:
                        bracket_depth += 1
                    elif t[i] in {"]", ")", "}"}:
                        bracket_depth -= 1
                    i += 1
                if i >= len(t):
                    return result
                assert(t[i] == "}")
                result.append([block_start, i, "rescue"])
                i += 1  # Past '}" closing bracket.
                while (i < len(t) and
                        t[i].strip(" \r\n\t") == ""):
                    i += 1
            if i < len(t) and t[i] == "finally":
                i += 1  # Past 'finally' keyword.
                bracket_depth = 0
                while (i < len(t) and
                        (t[i] != "{" or
                        bracket_depth > 0)):
                    if t[i] in {"[", "(", "{"}:
                        bracket_depth += 1
                    elif t[i] in {"]", ")", "}"}:
                        bracket_depth -= 1
                    i += 1
                if i >= len(t):
                    return result
                assert(t[i] == "{")
                i += 1  # Past '{' opening bracket.
                block_start = i
                bracket_depth = 0
                while (i < len(t) and
                        (t[i] != "}" or
                        bracket_depth > 0)):
                    if t[i] in {"[", "(", "{"}:
                        bracket_depth += 1
                    elif t[i] in {"]", ")", "}"}:
                        bracket_depth -= 1
                    i += 1
                if i >= len(t):
                    return result
                assert(t[i] == "}")
                result.append([block_start, i, "finally"])
                i += 1  # Past '}" closing bracket.
            return result
        if (stmt_type == "do" and
                range_type == "expr"):
            # Skip until 'rescue' keyword (since
            # nothing else directly has expressions):
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "rescue" or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t):
                return []
            i += 1  # Past 'rescue' keyword.
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            # Fall through, code after collects expression.
        elif stmt_type == "for":
            # Skip until 'in' keyword:
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "in" or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t):
                return []
            i += 1  # Past 'in' keyword.
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            # Fall through, code after collects expression or block.
        elif stmt_type == "func":
            # Skip over dots in function name (for types)
            while (i + 1 < len(t) and
                    is_identifier(t[i]) and
                    nextnonblank(t, i) == "."):
                i += 1  # the identifier
                while (i < len(t) and
                        t[i].strip(" \r\n\t") == ""):
                    i += 1
                i += 1  # the dot
                while (i < len(t) and
                        t[i].strip(" \r\n\t") == ""):
                    i += 1
            if (i >= len(t) or
                    not is_identifier(t[i])):
                # Shouldn't happen if this was valid.
                return []
            i += 1  # Past identifier.
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            if (i >= len(t) or (t[i] == "{" and
                    range_type == "expr")):
                # A parameterless func, or cut off early.
                return []
            # Fall through, block after collects expression or block.
        # Okay, now get the first main expression:
        expr_start = i
        prev_seen_nonblank = ""
        bracket_depth = 0
        while (i < len(t) and
                ((stmt_type == "with" and t[i] != "as") or
                (stmt_type != "with" and (t[i] != "{" or
                (i == expr_start and stmt_type != "func"))) or
                is_h64op_with_righthand(
                    prevnonblank(t, i)) or
                bracket_depth > 0 or
                (stmt_type != "func" and
                prev_seen_nonblank == ""))):
            if t[i].strip(" \r\n\t") != "":
                prev_seen_nonblank = t[i]
            if t[i] in {"[", "(", "{"}:
                bracket_depth += 1
            elif t[i] in {"]", ")", "}"}:
                bracket_depth -= 1
            i += 1
        if stmt_type != "if" and range_type == "expr":
            if i < len(t):
                return ([[expr_start, i]])
            return []
        elif range_type == "block":
            if stmt_type == "with":
                # We're at 'as' keyword, forward to '{'.
                while i < len(t) and t[i] != '{':
                    i += 1
            if i >= len(t):
                return []
            assert(t[i] == "{")
            i += 1  # Past '{' opening bracket.
            block_start = i
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "}" or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t):
                return []
            assert(t[i] == "}")
            result.append([block_start, i])
            if stmt_type != "if":
                return result
            i += 1  # Past '}' closing bracket.
        else:
            assert(stmt_type == "if" and
                range_type == "expr")
            result = [[expr_start, i]]
        assert(stmt_type == "if")  # Everything else handled above.
        # Scan for any elseif/else:
        while True:
            if i >= len(t):
                return result
            bracket_depth = 0
            while (i < len(t) and (
                    (t[i] != "elseif" and
                    t[i] != "else") or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t) or (t[i] == "else" and
                    range_type == "expr"):
                return result
            is_elseif = (t[i] == "elseif")
            i += 1  # Past 'elseif'/'else keyword.
            expr_start = i
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            if is_elseif:
                while (i < len(t) and
                        (t[i] != "{" or i == expr_start or
                        is_h64op_with_righthand(t[i - 1]) or
                        bracket_depth > 0)):
                    if t[i] in {"[", "(", "{"}:
                        bracket_depth += 1
                    elif t[i] in {"]", ")", "}"}:
                        bracket_depth -= 1
                    i += 1
            if i >= len(t) or t[i] != "{":
                return result
            expr_end = i - 1
            i += 1  # Past '{' opening bracket.
            if range_type == "expr":
                result.append([expr_start, expr_end + 1])
            block_start = i
            bracket_depth = 0
            while (i < len(t) and
                    (t[i] != "}" or
                    bracket_depth > 0)):
                if t[i] in {"[", "(", "{"}:
                    bracket_depth += 1
                elif t[i] in {"]", ")", "}"}:
                    bracket_depth -= 1
                i += 1
            if i >= len(t):
                return result
            assert(t[i] == '}')
            if range_type == "block":
                result.append([block_start, i])
            if not is_elseif:
                # Was an 'else', so we have to stop.
                return result
            i += 1  # Past '}' closing bracket
            continue  # Search for further 'elseif' blocks.
    if t[i] in {"const", "var"}:
        if range_type == "block":
            return []
        while (i < len(t) and
                t[i] != "="):
            i += 1
        if i < len(t) and t[i] == "=":
            return [[i + 1, len(t)]]
        return []
    # General unrecognized statement.
    if range_type == "expr":
        return [[0, len(t)]]  # Default to full length expression.
    return []  # Default to no sub-blocks.


def get_statement_expr_ranges(t):
    return get_statement_ranges_ex(
        t, range_type="expr")


def get_statement_block_ranges(t):
    ranges = get_statement_ranges_ex(
        t, range_type="block")
    return ranges


def firstnonblankidx(t):
    idx = 0
    while (idx < len(t) and
            t[idx].strip(" \r\n\t") == ""):
        idx += 1
    if idx >= len(t):
        return -1
    return idx


def firstnonblank(t):
    idx = 0
    while (idx < len(t) and
            t[idx].strip(" \r\n\t") == ""):
        idx += 1
    if idx >= len(t):
        return ""
    return t[idx]


def nextnonblank(t, idx, no=1):
    while no > 0:
        idx += 1
        while (idx < len(t) and
                t[idx].strip(" \r\n\t") == ""):
            idx += 1
        no -= 1
    if idx >= len(t):
        return ""
    return t[idx]


def nextnonblankidx(t, idx, no=1):
    while no > 0:
        idx += 1
        while (idx < len(t) and
                t[idx].strip(" \r\n\t") == ""):
            idx += 1
        no -= 1
    if idx >= len(t):
        return -1
    return idx


def prevnonblank(t, idx, no=1):
    while no > 0:
        idx -= 1
        while (idx >= 0 and
                t[idx].strip(" \r\n\t") == ""):
            idx -= 1
        no -= 1
    if idx < 0:
        return ""
    return t[idx]


def expr_nonblank_equals(
        v1, v2, any_match_value=None
        ):
    if type(v1) == str:
        v1 = tokenize(v1)
    if type(v2) == str:
        v2 = tokenize(v2)
    i1 = 0
    i2 = 0
    while True:
        while (i1 < len(v1) and (v1[i1] == "" or
                is_whitespace_token(v1[i1]))):
            i1 += 1
        while (i2 < len(v2) and (v2[i2] == "" or
                is_whitespace_token(v2[i2]))):
            i2 += 1
        if i1 >= len(v1):
            return (i2 >= len(v2))
        elif i2 >= len(v2):
            return False
        if (v1[i1] != v2[i2]) and (
                any_match_value == None or
                (v1[i1] != any_match_value and
                v2[i2] != any_match_value)):
            #print("DIVERGED AT: " + str((v1[:i1 + 1],
            #    v2[:i2 + 1])) + ", " +
            #    "MISMATCH '" + str(v1[i1]) + "' vs '" +
            #    str(v2[i2]) + "'")
            return False
        i1 += 1
        i2 += 1


def find_start_of_call_index_chain(s, i):
    while (i >= 0 and
            is_whitespace_token(s)):
        i -= 1
    if i < 0:
        return 0
    while True:
        if is_identifier(s[i]):
            if prevnonblank(s, i) == ".":
                i = prevnonblankidx(s, i, no=2)
                if i < 0:
                    return 0
                continue
            return i
        if s[i] in {"[", "{", "("}:
            return i + 1
        if s[i] == "]" or s[i] == ")" or s[i] == "}":
            endbracket = "["
            if s[i] == ")":
                endbracket = "("
            elif s[i] == "}":
                endbracket = "{"
            bracket_depth = 0
            while (i >= 0 and
                    (s[i] != endbracket or
                    bracket_depth > 0)):
                if s[i] in {"]", ")", "}"}:
                    bracket_depth += 1
                elif s[i] in {"[", "(", "{"}:
                    bracket_depth -= 1
                    if bracket_depth <= 0:
                        break
                i -= 1
            if i < 0 or s[i] != endbracket:
                return 0
            if (prevnonblank(s, i) in {")", "]"} or
                    (endbracket == "[" and
                    prevnonblank(s, i) in {"}"})):
                i = prevnonblankidx(s, i)
                continue
            if (endbracket in {"(", "["} and
                    is_identifier(prevnonblank(s, i))):
                i = prevnonblankidx(s, i)
                continue
            return i
        if (s[i].startswith("'") or
                s[i].startswith("\"") or
                s[i].startswith("b'") or
                s[i].startswith("b\"") or
                is_number_token(s[i])):
            return i
        return i + 1


def is_number_token(v):
    def is_digit(v):
        if len(v) == 0:
            return False
        i = 0
        while i < len(v):
            if (ord(v[i]) < ord("0") or
                    ord(v[i]) > ord("9")):
                return False
            i += 1
        return True
    if "." in v:
        nonfrac = v.partition(".")[0]
        frac = v.partition(".")[2]
        if (is_digit(frac) and (
                (nonfrac.startswith("-") and
                is_digit(nonfrac[1:])) or
                is_digit(nonfrac))):
            return True
    else:
        if v.startswith("-") and is_digit(v[1:]):
            return True
        return is_digit(v)


def prevnonblankidx(t, idx, no=1):
    while no > 0:
        idx -= 1
        while (idx >= 0 and
                t[idx].strip(" \r\n\t") == ""):
            idx -= 1
        no -= 1
    if idx < 0:
        return -1
    return idx


def get_statement_inline_funcs(t):
    assert(type(t) in {list, tuple})
    ranges = get_statement_expr_ranges(t)
    assert(type(ranges) == list)
    result = []
    for expr_range in ranges:
        assert(type(expr_range) == list)
        assert(expr_range[0] >= 0 and
            expr_range[1] >= expr_range[0] and
            expr_range[1] <= len(t))
        i = expr_range[0]
        while i < expr_range[1]:
            if t[i] != "func":
                i += 1
                continue
            func_start = i
            bracket_depth = 0
            while (i < len(t) and
                    i < expr_range[1] - 1 and
                    (t[i] != "{" or bracket_depth > 0 or
                    (i > func_start and
                    is_h64op_with_righthand(
                        prevnonblank(t, i))))):
                if t[i] in {"{", "(", "["}:
                    bracket_depth += 1
                elif t[i] in {"}", ")", "]"}:
                    bracket_depth -= 1
                i += 1
            assert(t[i] == "{")
            body_opening_bracket = i
            i += 1  # Past '{' opening bracket.
            bracket_depth = 0
            while i < len(t) and (bracket_depth > 0 or
                    t[i] != "}") and i < expr_range[1]:
                if t[i] in {"{", "(", "["}:
                    bracket_depth += 1
                elif t[i] in {"}", ")", "]"}:
                    bracket_depth -= 1
                i += 1
            assert(t[i] == "}")
            result.append([func_start,
                body_opening_bracket, i + 1])
            i += 1
            continue
    return result


def tokenize(s):
    tokens = []
    while len(s) > 0:
        t = get_next_token(s)
        if len(t) == 0:
            return tokens
        tokens.append(t)
        s = s[len(t):]
    return tokens


def is_h64op_with_righthand(v):
    if v in {"and", "or", "not", "+", "-", "*", "/",
            ">", "<", "->",
            ".", "!=", "=", "=="}:
        return True
    if len(v) == 2 and v[1] == "=":
        return True
    return False


def is_h64op_with_lefthand(v):
    if v in {"and", "or", "+", "-", "*", "/",
            ">", "<", "->", ".", "!=", "=", "==",
            ":"}:
        return True
    if len(v) == 2 and v[1] == "=":
        return True
    return False


def has_no_ascii_letters(v):
    if v == "":
        return True
    v = v.lower()
    i = 0
    while i < len(v):
        if (ord(v[i]) >= ord("a") and
                ord(v[i]) <= ord("z")):
            return False
        i += 1
    return True


def has_any_ascii_letters(v):
    if v == "":
        return False
    v = v.lower()
    i = 0
    while i < len(v):
        if (ord(v[i]) >= ord("a") and
                ord(v[i]) <= ord("z")):
            return True
        i += 1
    return False


def get_next_statement(s):
    if len(s) == 0:
        return []
    must_continue_tokens = {
        "->", "(", "[", ":", "then",
        ",", "else", "as", "in", "from",
        "rescue", "finally", "elseif"}
    last_nonwhitespace_token = ""
    token_count = 0
    bracket_nesting = 0
    _future_last_token = None
    i = -1
    for t in s:
        if (_future_last_token != None and
                _future_last_token.strip(" \t\r\n") != ""):
            last_nonwhitespace_token = _future_last_token
        _future_last_token = t
        i += 1
        token_count += 1
        if t in ["(", "[", "{"]:
            bracket_nesting += 1
        if t in [")", "]", "}"]:
            bracket_nesting -= 1
        if (is_whitespace_token(t) and
                nextnonblank(t, i) in
                must_continue_tokens):
            continue
        if (bracket_nesting == 0 and
                t == "}"):
            nt = nextnonblank(s, i)
            if (not nt in must_continue_tokens and
                    not is_h64op_with_lefthand(nt) and
                    not nt in {"(", "{", "["}) :
                return s[:token_count]
        if (bracket_nesting == 0 and
                last_nonwhitespace_token != "" and
                t in {"var", "const", "while",
                "do", "for", "type"}):  # "if"/"func" can be inline!
            # Important: cut off BEFORE the token for this one.
            return s[:token_count - 1]
        if (bracket_nesting == 0 and
                (t.endswith("\n") or t.endswith("\r")) and
                last_nonwhitespace_token != "," and
                not is_h64op_with_righthand(last_nonwhitespace_token) and
                not last_nonwhitespace_token in {"in", "as"} and
                not is_h64op_with_lefthand(nextnonblank(s, i)) and
                not nextnonblank(s, i) in must_continue_tokens
                ):
            is_string_continuation = False
            if (last_nonwhitespace_token.endswith("\"") or
                    last_nonwhitespace_token.endswith("'")):
                z = token_count
                while z < len(s) and s[z].strip(" \t\r\n") == "":
                    z += 1
                if z < len(s) and (
                        s[z].endswith("\"") or s[z].endswith("'")):
                    is_string_continuation = True
            if not is_string_continuation:
                return s[:token_count]
        assert(bracket_nesting >= 0), \
            "failed to find terminating bracket in: " + str(s)
    return s


def is_whitespace_statement(tokens):
        for token in tokens:
            for c in token:
                if not is_whitespace_token(c):
                    return False
        return True


def split_toplevel_statements(s, skip_whitespace=True):
    assert(type(s) in {list, tuple})
    if len(s) == 0:
        return []
    statements = []
    while True:
        next_stmt = get_next_statement(s)
        if len(next_stmt) == 0:
            return statements
        if (not skip_whitespace or
                not is_whitespace_statement(
                next_stmt)):
            statements.append(next_stmt)
        s = s[len(next_stmt):]
    return statements


def is_bracket(v):
    return v in {"(", "[", "{",
        "}", "]", ")"}


def tokens_need_spacing(v1, v2):
    if v1 == "" or v2 == "":
        return False
    if (is_whitespace_token(v1) or
            is_whitespace_token(v2)):
        return False
    if (is_bracket(v1) or is_bracket(v2) or
            v1 == ":" or v2 == ":"):
        return False
    if v1 == "." or v2 == ".":
        return False
    if (identifier_or_keyword(v1) and
            identifier_or_keyword(v2)):
        return True
    if (not is_h64op_with_righthand(v1) and
            not is_h64op_with_righthand(v2)) and (
            has_no_ascii_letters(v1) and
            has_no_ascii_letters(v2)
            ):
        return False
    if v2 == "->":
        return False
    if (len(v1) == 2 and not has_any_ascii_letters(v1) and
            len(v2) == 2 and not has_any_ascii_leters(v2)):
        return False
    return True


def untokenize(tokens):
    assert(type(tokens) in {list, tuple})
    result = ""
    prevtoken = ""
    for token in tokens:
        assert(type(token) == str)
        if prevtoken != "" and \
                tokens_need_spacing(prevtoken, token):
            result += " "
        result += token
        prevtoken = token
    return result


def tree_transform_statements(code, callback_statement_list):
    if (type(code) != str and (
            type(code) not in {list, tuple} or
            (len(code) > 0 and type(code[0]) != str))):
        raise TypeError("code must be string or "
            "list of tokens (=list of strings)")
    was_string = False
    if type(code) == str:
        code = tokenize(code)
        was_string = True
    statements = split_toplevel_statements(
        code, skip_whitespace=False
    )
    if callback_statement_list != None:
        statements = callback_statement_list(statements)
        assert(type(statements) == list)
        assert(len(statements) == 0 or (
            type(statements[0]) == list and
            (len(statements[0]) == 0 or
            type(statements[0][0]) == str)))
    final_tokens = []
    for statement in statements:
        ranges = get_statement_block_ranges(statement)
        for block_range in reversed(ranges):
            assert(type(block_range) == list and
                len(block_range) >= 2 and
                type(block_range[0]) in {float, int} and
                type(block_range[1]) in {float, int})
            assert(block_range[0] > 0 or
                block_range[1] < len(statement))
            replacement = tree_transform_statements(statement[
                block_range[0]:block_range[1]],
                callback_statement_list)
            statement = (statement[:block_range[0]] +
                replacement +
                statement[block_range[1]:])
        final_tokens += statement
    if was_string:
        return untokenize(final_tokens)
    return final_tokens


def get_leading_whitespace(st):
    if type(st) == str:
        st = [st]
    leading = ""
    i = 0
    while i < len(st):
        if st[i].strip(" \r\n\t") != "":
            len_diff = (len(st[i]) -
                len(st[i].lstrip(" \r\n\t")))
            if len_diff > 0:
                leading += st[i][:len_diff]
            return leading
        else:
            leading += st[i]
        i += 1
    return leading


def extract_all_imports(s):
    if type(s) == str:
        s = tokenize(s)
    result = []
    statements = split_toplevel_statements(s)
    for statement in statements:
        if firstnonblank(statement) != "import":
            continue
        i = firstnonblankidx(statement) + 1
        while (i < len(statement) and
                statement[i].strip(" \n\r\t") == ""):
            i += 1
        import_module = []
        if i >= len(statement) or not is_identifier(
                statement[i]):
            continue
        import_module.append(statement[i])
        while (i < len(statement) and
                nextnonblank(statement, i) == "." and
                is_identifier(nextnonblank(
                    statement, i, no=2))):
            i = nextnonblankidx(statement, i, no=2)
            import_module.append(statement[i])
        assert(is_identifier(statement[i]))
        if nextnonblank(statement, i) != "from":
            result.append([".".join(import_module), None])
            continue
        i = nextnonblankidx(statement, i, no=2)
        import_package = statement[i]
        while (i < len(statement) and
                nextnonblank(statement, i) == "." and
                is_identifier(nextnonblank(
                    statement, i, no=2))):
            i = nextnonblankidx(statement, i, no=2)
            import_package += ("." + statement[i])
        result.append([".".join(import_module),
            import_package])
        continue
    return result


def get_global_standalone_func_names(s,
        error_duplicates=False
        ):
    result = []
    scope = get_global_names(s)
    for entry in scope:
        if scope[entry]["type"] == "func":
            result.append(entry)
    return result


def separate_out_inline_funcs(s):
    def do_separate_out(sts):
        new_sts = []
        for st in sts:
            # Find all inline functions in this statement:
            func_ranges = get_statement_inline_funcs(st)
            if len(func_ranges) == 0:
                new_sts.append(st)
                continue

            # For each inline function, we need to separate it:
            for frange in reversed(func_ranges):
                # Sanity checks on inline func's reported extent:
                assert(len(frange) == 3)
                assert(frange[0] >= 0 and
                    frange[0] < len(st) and
                    st[frange[0]] == "func")
                assert(frange[2] > frange[0] and
                    frange[2] <= len(st) and
                    st[frange[2] - 1] == "}")

                # Create new 'func' statement and extract arguments:
                fname = "_f" + str(uuid.uuid4()).replace("-", "")
                prepend_st = [get_leading_whitespace(st),
                    "func", " ", fname]
                params = st[frange[0] + 1:frange[1]]
                while (len(params) > 0 and
                        is_whitespace_token(params[0])):
                    params = params[1:]
                while (len(params) > 0 and
                        is_whitespace_token(params[-1])):
                    params = params[:-1]
                if (len(params) == 0 or
                        params[0] != "(" or
                        params[-1] != ")"):
                    params = ["("] + params + [")"]
                prepend_st += params

                # Now add in the body and prepend new statement:
                prepend_st += (["{"] + st[
                    frange[1] + 1:frange[2]] + ["\n"])
                new_sts.append(prepend_st)

                # In the original/old statement, rip out the inline
                # 'func' def and refer to our new 'func' statement:
                st = (st[:frange[0]] +
                    [fname, " "] + st[frange[2]:])
            new_sts.append(st)
        return new_sts
    s = tree_transform_statements(s, do_separate_out)
    return s


def sanity_check_h64_codestring(s, filename="", modname=""):
    tokens = None
    if type(s) == list:
        tokens = s
    else:
        tokens = tokenize(
            s.replace("\r\n", "\n").replace("\r", "\n")
        )
    col = 1
    line = 1
    bracket_nesting_orig_loc = []
    bracket_nesting = []
    i = -1
    for token in tokens:
        i += 1
        if token == "," and nextnonblank(tokens, i) == ",":
            raise ValueError(("" if (modname == "" or
                modname == None) else ("in module " +
                str(modname) + " ")) +
                ("" if (filename == "" or
                filename == None) else ("in file " +
                str(filename) + " ")) +
                "in line " + str(line) + ", col " + str(col) + ": " +
                "invalid double use of ','")
        if token in {"(", "{", "["}:
            bracket_nesting_orig_loc.append((line, col))
            bracket_nesting.append(token)
        elif token in {")", "}", "]"}:
            reverse_bracket = "("
            if token == "}":
                reverse_bracket = "{"
            elif token == "]":
                reverse_bracket = "["
            if (len(bracket_nesting) == 0 or
                    bracket_nesting[-1] != reverse_bracket):
                errmsg = (("" if (modname == "" or
                    modname == None) else ("in module " +
                    str(modname) + " ")) +
                    ("" if (filename == "" or
                    filename == None) else ("in file " +
                    str(filename) + " ")) +
                    "in line " + str(line) + ", col " + str(col) + ": " +
                    "unexpected unmatched closing bracket '" +
                    str(token) + "', expected ")
                if len(bracket_nesting) > 0:
                    errmsg += ("one closing '" +
                        bracket_nesting[-1] +
                        "' opened in line " + str(
                        bracket_nesting_orig_loc[-1][0]) +
                        ", col " + str(bracket_nesting_orig_loc[-1][1]))
                else:
                    errmsg += ("none (all previous pairs closed)")
                raise ValueError(errmsg)
            bracket_nesting = bracket_nesting[:-1]
            bracket_nesting_orig_loc = (
                bracket_nesting_orig_loc[:-1])
        if "\n" in token:
            token_per_line = token.split("\n")
            line += len(token_per_line) - 1
            col = 1 + len(token_per_line[-1])
        else:
            col += len(token)


def get_names_defined_in_func(
        st, is_anonymous_inline=False
        ):
    """ Get all identifiers that are present in the most
        outer scope of the given function statement."""

    if type(st) == str:
        st = tokenize(st)
    else:
        st = list(st)
    func_kw_idx = firstnonblankidx(st)
    if (func_kw_idx < 0 or
            st[func_kw_idx] != "func"):
        return []
    names = []

    # Get names of function arguments:
    k = nextnonblankidx(st, func_kw_idx)
    if not is_anonymous_inline:
        # Skip the function name.
        if k < 0 or not is_identifier(st[k]):
            return []
        if not st[k] in names:
            names.append(st[k])
        k = nextnonblankidx(st, k)
    else:
        if not st[k] in {"(", "{"}:
            return []
        # We must insert a fake function name because
        # get_statement_block_ranges() only knows named
        # func statements, not anonymous inline funcs.
        st = st[:k] + [
            "_f" + str(uuid.uuid4()).replace("-", "")
            ] + st[k:]
        k += 1
    if st[k] == "(":
        # Arugment list start!
        k += 1  # Past opening "(" of argument list.
        while k < len(st) and st[k] != ")":
            if st[k] == "" or is_whitespace_token(st[k]):
                k += 1
                continue
            # Get argument name first:
            if is_identifier(st[k]):
                if not st[k] in names:
                    names.append(st[k])
                bracket_depth = 0
                # Forward to end of argument:
                while k < len(st) and (
                        bracket_depth > 0 or
                        (st[k] != ")" and st[k] != ",")):
                    if st[k] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif st[k] in {")", "]", "}"}:
                        bracket_depth -= 1
                    k += 1
                if k >= len(st) or st[k] != ",":
                    # End of parameter list.
                    break
                k += 1  # Past "," of last argument.
                continue  # Parse next argument.
            k += 1

    # Get names from function body:
    ranges = get_statement_block_ranges(st)
    for brange in ranges:
        subtokens = st[brange[0]:brange[1]]
        stmts = split_toplevel_statements(subtokens)
        for inner_st in stmts:
            if firstnonblank(inner_st) in {
                    "var", "const"
                    }:
                k = nextnonblankidx(inner_st,
                    firstnonblankidx(inner_st))
                if (k < 0 or
                        not is_identifier(inner_st[k])):
                    continue
                if not inner_st[k] in names:
                    names.append(inner_st[k])
                continue
    # We should have all names in the outermost scope now!
    return names


def transform_then_to_closure_unnested(
        sts, h64_indent="    "
        ):
    new_sts = []
    st_idx = -1
    for st in sts:
        st_idx += 1

        # Find all 'then' keyword uses:
        then_indexes = []
        i = -1
        for t in st:
            i += 1
            if t == "then":
                then_indexes.append(i)
        if len(then_indexes) == 0:
            new_sts.append(st)
            continue

        # Discard those inside nested statement blocks:
        ranges = get_statement_block_ranges(st)
        for brange in ranges:
            i = 0
            while i < len(then_indexes):
                if (then_indexes[i] >=
                        brange[0] and
                        then_indexes[i] < brange[1]):
                    then_indexes = (
                        then_indexes[:i] +
                        then_indexes[i + 1:])
                    continue
                i += 1
        if len(then_indexes) != 1:
            new_sts.append(st)
            continue

        # Now we should have just one 'then' left if the
        # code is valid in the first place:
        then_index = then_indexes[0]
        if prevnonblank(st, then_index) != ")":
            # Invalid code. Just ignore.
            new_sts.append(st)
            continue
        then_preceding_call_noargs = False
        then_preceding_call_close = prevnonblankidx(st, then_index)
        then_preceding_call_args_have_trailing_comma = False
        if prevnonblank(st, then_index, no=2) == "(":
            then_preceding_call_noargs = True
        elif prevnonblank(st, then_index, no=2) == ",":
            then_preceding_call_args_have_trailing_comma = True

        # Extract the arguments after 'then' keyword:
        arg_start = then_index + 1
        i = arg_start
        bracket_depth = 0
        while (i < len(st) and (
                st[i] != ":" or bracket_depth > 0)):
            if st[i] in {"(", "{", "["}:
                bracket_depth += 1
            elif st[i] in {")", "}", "]"}:
                bracket_depth -= 1
            i += 1
        arg_end = i
        if i >= len(st) or st[i] != ":":
            # Invalid, so skip this:
            new_sts.append(st)
            continue
        i += 1  # Go past ':' past the 'then' args.

        # Name for our new callback implicitly created by 'then',
        # as well as indent for the 'func ... {' opening line:
        funcname = "_" + str(uuid.uuid4()).replace("-", "")
        indent = get_indent(st)
        def flatten(l):
            flat = []
            for sl in l:
                for item in sl:
                    flat.append(item)
            return flat

        # Get all the statements after 'then' to pull into callback:
        func_inner_content_str = (
            untokenize(flatten(sts[st_idx + 1:])))
        func_inner_content_str = h64_indent + (
            ("\n" + h64_indent).join(
                func_inner_content_str.split("\n")
            ))
        func_inner_content = flatten(
            transform_then_to_closure_unnested(
                split_toplevel_statements(
                    tokenize(func_inner_content_str)
                )
            )
        )
        assert(len(func_inner_content) == 0 or
            type(func_inner_content[0]) == str)

        # Assemble callback statement and add it in:
        insert_st = ([indent, "func", " ",
            funcname, " "])
        if len(untokenize(
                st[arg_start:arg_end]).strip(" \t\r\n")) > 0:
            insert_st += (["("] + st[arg_start:arg_end] +
                [")", " "])
        insert_st += (["{", "\n"] +
            func_inner_content +
            ["\n"] + ([indent] if
                indent != None and len(indent) > 0 else
                []) +
            ["}", "\n"])
        new_sts.append(insert_st)

        # Now add the call that had the 'then', but stripped off:
        orig_st = list(st)
        st = st[:then_preceding_call_close]
        if (not then_preceding_call_noargs and
                not then_preceding_call_args_have_trailing_comma):
            st += [",", " "]
        st += [funcname] + [")", "\n"]
        new_sts.append(st)

        # Output some debug info:
        #print("CREATED STATEMENTS: " + str(new_sts[-2:]))
        #print("ORIGINAL ONE: " + str(orig_st))
        #print("TOKEN WHERE ORIG CALL ENDED: " +
        #    str(then_preceding_call_close))
        #print("ARG START:ARG_END FOR 'then': " +
        #    str(orig_st[arg_start:arg_end]))
        break
    return new_sts


def get_indent(statement):
    s = statement
    if type(s) == list:
        s = untokenize(s)
    i = 0
    while i < len(s):
        if not s[i] in {
                " ", "\t", "\n", "\r"}:
            break
        if s[i] in {"\n", "\r"}:
            s = s[i + 1:]
            i = 0
            continue
        i += 1
    indentlen = (
        len(s) - len(s.lstrip(" \t"))
    )
    result = None
    if indentlen < len(s):
        result = s[:indentlen]
    return result


def transform_then_to_closures(s):
    def do_transform_then(sts):
        return transform_then_to_closure_unnested(sts)
    s = tree_transform_statements(s, do_transform_then)
    return s


def get_global_names(
        s, error_on_duplicates=False
        ):
    if type(s) == str:
        s = tokenize(s)
    sts = split_toplevel_statements(s)
    result = {}
    for st in sts:
        # See if this is a statement naming something:
        kw = firstnonblank(st)
        if kw not in {
                "var", "const", "import", "func", "type"}:
            continue

        # Extract what it names:
        i = firstnonblankidx(st)
        assert(st[i] == kw)
        i = nextnonblankidx(st, i)
        if (i < 0 or not is_identifier(st[i]) or
                (kw == "func" and
                nextnonblank(st, i) == ".")):
            continue
        is_type = kw
        is_named = [st[i]]
        if is_type in {"var", "const"}:
            while (nextnonblank(st, i) == "," and
                    is_identifier(nextnonblank(st, i, no=2))):
                is_named.append(nextnonblank(st, i, no=2))
                i = nextnonblankidx(st, i, no=2)

        # Go through all identifiers this name:
        for is_named in is_named:
            if (is_named in result and (
                    result[is_named]["type"] != "import" or
                    is_type != "import")):
                if error_on_duplicates:
                    raise ValueError("code syntax error, "
                        "global identifier \"" +
                        st[i] +
                        "\" defined twice, first as " +
                        result[is_named]["type"] + " and now as " +
                        is_type)
                continue
            result[is_named] = {
                "type": is_type
            }
    return result


def make_kwargs_in_call_tailing(s):
    was_str = False
    if type(s) == str:
        s = tokenize(s)
        was_str = True
    i = 0
    while i < len(s):
        if s[i] != "(":
            i += 1
            continue
        # Check if this is a function definition (which
        # we don't want to touch):
        is_fdef = False
        k = i - 1
        while k >= 0 and s[k].strip(" \t\r\n") == "":
            k -= 1
        if k >= 0 and s[k] == "func":
            is_fdef = True
        elif (k >= 0 and s[k] != "=" and
                (len(s[k]) != 2 or s[k][1] != "=") and
                not is_keyword(s[k]) and
                not is_h64op_with_righthand(s[k]) and
                s[k] not in {"(", "[", "{"}
                ):
            notdef_kw = ["as", "with", "rescue",
                "while", "for", "if", "elseif",
                "type", "var", "const"]
            bracket_depth = 0
            while k >= 0:
                if s[k] in {")", "]", "}"}:
                    bracket_depth += 1
                elif s[k] in {"(", "[", "{"}:
                    bracket_depth -= 1
                    if bracket_depth <= 0:
                        break
                if prevnonblank(s, k) == "func":
                    break
                if s[k] in notdef_kw:
                    break
                k -= 1
            if (k >= 0 and s[k] not in notdef_kw and
                    prevnonblank(s, k) == "func"):
                is_fdef = True
        if is_fdef:
            i += 1
            continue
        bracket_depth = 0
        arg_indexes = []
        assert(s[i] == "(")
        k = i + 1
        guaranteed_not_a_call = False
        had_any_kw_arg = False
        current_arg_eq = None
        current_arg_start = k
        while k < len(s) and (s[k] != ")" or
                bracket_depth > 0):
            if s[k] in {"(", "[", "{"}:
                bracket_depth += 1
            if s[k] in {")", "]", "}"}:
                bracket_depth -= 1
            if (bracket_depth == 0 and
                    s[k] in {"rescue", "var", "const",
                        "do", "with", "while", "if", "elseif",
                        "else"}):
                # Oops, this some other expr in ( .. ), not a call.
                guaranteed_not_a_call = True
                break
            if (bracket_depth == 0 and
                    k + 1 < len(s) and
                    s[k + 1] == ")"):
                arg_indexes.append((
                    current_arg_start,
                    current_arg_eq, k + 1))
            elif s[k] == "," and bracket_depth == 0:
                arg_indexes.append((
                    current_arg_start,
                    current_arg_eq, k))
                current_arg_start = k + 1
                current_arg_eq = None
            elif bracket_depth == 0 and s[k] == "=":
                current_arg_eq = k
                had_any_kw_arg = True
            k += 1
        if guaranteed_not_a_call:
            i += 1
            continue
        if not had_any_kw_arg:
            # Nothing for us to do, even if this is a call.
            i += 1
            continue
        if nextnonblank(s, k) == "{":
            # Oops, this isn't possible inside a normal statement
            # after a call. Assume we shouldn't touch this!
            i += 1
            continue
        # We got all arguments and even a '=', and it doesn't
        # look like a func definition, so this has to be a call.
        #print("FOUND ARGS WITH EQ: " + str((arg_indexes,
        #    s[i:k + 1])))
        old_tokens = s[i:k + 1]
        new_tokens = ["("]
        arg_no = 0
        # Collect all positional args first:
        had_positional_before_kwarg = False
        seen_any_kw_arg = None
        for arg_index_entry in arg_indexes:
            if arg_index_entry[1] is not None:
                seen_any_kw_arg = True
                continue
            if seen_any_kw_arg:
                had_positional_before_kwarg = True
            arg_no += 1
            if arg_no > 1:
                new_tokens += [","]
            new_tokens += s[arg_index_entry[0]:arg_index_entry[2]]
        # If we didn't have a positional arg before a kwarg yet,
        # then everything is already in order and we can bail early:
        if not had_positional_before_kwarg:
            i = k + 1
            continue
        # Now add the keyword arguments:
        for arg_index_entry in arg_indexes:
            if arg_index_entry[1] == None:
                continue
            arg_no += 1
            if arg_no > 1:
                new_tokens += [","]
            new_tokens += s[arg_index_entry[0]:arg_index_entry[2]]
        new_tokens += ")"
        #print(" TRANSFORM =" + str([s[i:k + 1], new_tokens]))

        # Insert the new result:
        s = s[:i] + new_tokens + s[k + 1:]

        i += 1
        continue
    if was_str:
        return untokenize(s)
    return s


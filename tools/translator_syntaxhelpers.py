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

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)


def could_be_identifier(x):
    if (len(x) == 0 or (x[0] != "_" and
            (ord(x[0]) < ord("a") or ord(x[0]) > ord("z")) and
            (ord(x[0]) < ord("A") or ord(x[0]) > ord("Z")) and
            ord(x[0]) <= 127)):
        return False
    if x in {"if", "func", "import", "else",
            "type", "do", "rescue", "finally",
            "from",
            "var", "const", "elseif", "while",
            "for", "in", "not", "and", "or"}:
        return False
    return True


def identifier_or_keyword(x):
    if x == "" or type(x) != str:
        return False
    i = 0
    while i < len(x):
        if (x[i] != "_" and
                (ord(x[i]) < ord("a") or ord(x[i]) > ord("z")) and
                (ord(x[i]) < ord("A") or ord(x[i]) > ord("Z")) and
                (ord(x[i]) < ord("0") or ord(x[i]) < ord("9")
                 or i == 0) and
                ord(x[i]) <= 127):
            return False
        i += 1
    return True


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
            if t[i] != "{":
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
            if i > len(t) or t[i] != "}":
                return []
            return [[block_start, i]]
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
            result.append([[block_start, i]])
            i += 1  # Past '}' closing bracket.
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            if i >= len(t):
                return result
            if t[i] == "rescue":
                i += 1  # Past 'rescue' keyword.
                bracket_depth = 0
                while (i < len(t) and
                        (t[i] != "as" or
                        bracket_depth > 0)):
                    if t[i] in {"[", "(", "{"}:
                        bracket_depth += 1
                    elif t[i] in {"]", ")", "}"}:
                        bracket_depth -= 1
                    i += 1
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
            if t[i] == "finally":
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
                    could_be_identifier(t[i]) and
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
                    not could_be_identifier(t[i])):
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
            return [i + 1, i]
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


def get_statement_inline_funcs(t):
    assert(type(t) in {list, tuple})
    ranges = get_statement_expr_ranges(t)
    result = []
    for expr_range in ranges:
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
            ">", "<", "->", ".", "!=", "=", "=="}:
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
    return False


def get_next_statement(s):
    if len(s) == 0:
        return []
    last_nonwhitespace_token = ""
    token_count = 0
    bracket_nesting = 0
    for t in s:
        token_count += 1
        if t in ["(", "[", "{"]:
            bracket_nesting += 1
        if t in [")", "]", "}"]:
            bracket_nesting -= 1
        if (bracket_nesting == 0 and
                t == "}"):
            j = token_count
            while (j < len(s) and
                    s[j].strip(" \r\n\t") == ""):
                j += 1
            if j >= len(s):
                return s
            if (not s[j] in {"rescue", "finally", "elseif",
                    "else"} and not is_h64op_with_righthand(s[j]) and
                    not s[j] in {"(", "{", "["}):
                return s[:token_count + 1]
        if (bracket_nesting == 0 and
                (t.endswith("\n") or t.endswith("\r")) and
                not is_h64op_with_righthand(last_nonwhitespace_token)
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
        if t.strip(" \t\r\n") != "":
            last_nonwhitespace_token = t
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
    if is_bracket(v1) or is_bracket(v2):
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
    final_statements = []
    for statement in statements:
        ranges = get_statement_block_ranges(statement)
        for block_range in reversed(ranges):
            assert(block_range[0] > 0 or
                block_range[1] < len(statement))
            replacement = tree_transform_statements(statement[
                block_range[0]:block_range[1]],
                callback_statement_list)
            replacement_flat = []
            for inner_stmt in replacement:
                replacement_flat += inner_stmt
            statement = (statement[:block_range[0]] +
                replacement_flat +
                statement[block_range[1]:])
        final_statements.append(statement)
    if was_string:
        return "".join([untokenize(st)
            for st in final_statements])
    return final_statements





def sanity_check_h64_codestring(s, filename="", modname=""):
    tokens = tokenize(s.replace("\r\n", "\n").replace("\r", "\n"))
    col = 1
    line = 1
    bracket_nesting = []
    i = -1
    for token in tokens:
        i += 1
        if token in {"(", "{", "["}:
            bracket_nesting.append(token)
        elif token in {")", "}", "]"}:
            reverse_bracket = "("
            if token == "}":
                reverse_bracket = "{"
            elif token == "]":
                reverse_bracket = "["
            if (len(bracket_nesting) == 0 or
                    bracket_nesting[-1] != reverse_bracket):
                raise ValueError(("" if (modname == "" or
                    modname == None) else ("in module " +
                    str(modname) + " ")) +
                    ("" if (filename == "" or
                    filename == None) else ("in file " +
                    str(filename) + " ")) +
                    "in line " + str(line) + ", col " + str(col) + ": " +
                    "unexpected unmatched closing bracket '" +
                    str(token) + "'")
            bracket_nesting = bracket_nesting[:-1]
        if "\n" in token:
            token_per_line = token.split("\n")
            line += len(token_per_line) - 1
            col = 1 + len(token_per_line[-1])
        else:
            col += len(token)

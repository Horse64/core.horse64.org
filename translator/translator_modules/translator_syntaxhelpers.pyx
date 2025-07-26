# Copyright (c) 2020-2025, ellie/@ell1e & Horse64 authors (see AUTHORS.md).
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

cdef is_keyword(x):
    if x in {"if", "func", "import", "else",
            "type", "do", "rescue", "finally",
            "from", "as", "extend", "base", "protect",
            "return", "await", "throw", "repeat",
            "var", "const", "elseif", "while",
            "any", "ignore", "with", "later",
            "new", "enum", "parallel", "continue",
            "break",
            "for", "in", "not", "and", "or"}:
        return True
    return False

def flatten(l):
    flat = []
    for sl in l:
        for item in sl:
            flat.append(item)
    return flat

cdef identifier_or_keyword(str x):
    if x == "":
        return False
    cdef int i = 0
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

cdef is_identifier(str v):
    return (identifier_or_keyword(v) and
        not v in {"yes", "no", "none"} and
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

cdef is_whitespace_token(str s):
    if len(s) == 0:
        return False
    for char in s:
        if char not in [" ", "\t", "\n", "\r"]:
            return False
    return True

cdef str get_next_token(str s):
    cdef int i
    cdef int len_s
    if s == "":
        return ""
    len_s = len(s)

    if s[:2] == "->":
        return "->"
    if (s[0] == "0" and len(s) >= 3 and
             s[1] == "x"):
        i = 1
        while (i + 1 < len(s) and (
                (ord(s[i + 1]) >= ord('0') and
                ord(s[i + 1]) <= ord('9')) or
                (ord(s[i + 1]) >= ord('a') and
                ord(s[i + 1]) <= ord('f')) or
                (ord(s[i + 1]) >= ord('A') and
                ord(s[i + 1]) <= ord('F')))):
            i += 1
        return s[:i + 1]
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
        if s[0:3] == "**=":
            return s[:3]
        if s[1:2] == "=" or s[0:2] == "**":
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
    assert(type(t) in {list, tuple})
    ranges = get_statement_ranges_ex_with_confused_linebreaks(
        t, range_type=range_type
    )
    if range_type == "block" and len(ranges) > 0:
        # We want the start of the range always to be AFTER the
        # full previous line (including its line break!!) and the
        # end also just right AFTER the ending line break.
        ranges_fixed = []
        for brange in ranges:
            linebreaks_range = [
                idx_of_lineend(t, brange[0], forward_first=False),
                idx_of_lineend(t, brange[1] - 1,  # <- since exclusive end
                     forward_first=True)
            ]
            new_range = [brange[0], brange[1]]
            if linebreaks_range[0] != None:
                new_range[0] = linebreaks_range[0] + 1
            if linebreaks_range[1] != None:
                new_range[1] = linebreaks_range[1] + 1
            if len(brange) >= 3:
                new_range.append(brange[2])  # Copy type.
            ranges_fixed.append(new_range)
        #print("FIX JOB : " + str((ranges, ranges_fixed)) +
        #    " ON: " + str(t))
        return ranges_fixed
    return ranges

def adjust_to_absolute_indent(t, indent=""):
    old_indent = get_indent(t)
    if old_indent is None:
        return t
    if len(indent) == len(old_indent):
        return t
    if len(indent) > len(old_indent):
        change_indent = indent[len(old_indent):]
        t = increase_indent(t, added=change_indent)
    else:
        t = increase_indent(t, removed=(
            len(old_indent) - len(indent)))
    return t

def increase_indent(t, added="", removed=0):
    was_str = False
    if type(t) == str:
        was_str = True
        t = tokenize(t)
    else:
        t = list(t)
        if len(t) > 0 and type(t[0]) == list:
            t = flatten(t)
    assert(type(t) == list and (
        len(t) == 0 or type(t[0]) == str))
    assert(type(added) == str)
    if not ((len(added) == 0 or removed == 0) and
            (len(added) > 0 or removed > 0)):
        raise ValueError("can't have both added "
            "and removed indent or neither!")

    lb = "\n"
    for _t in t:
        if "\r\n" in _t:
            lb = "\r\n"
            break
        elif "\r" in _t:
            lb = "\r"
            break
        elif "\n" in _t:
            lb = "\n"
            break

    had_trailing_lb = (
        len(lb) > 0 and len(t) > 0 and t[-1].endswith(lb)
    )
    new_tokens = []
    line_start = 0
    i = 0
    while True:
        if i >= len(t) or (t[i].startswith(lb) and
                i > line_start):
            # We're at a line break.
            old_line = t[line_start:i]
            if i < len(t) and t[i].index(lb) > 0:
                # Pull in partial token only up to line break!
                old_line += t[i].partition(lb)[0]
                t = (t[:i] + [t[i].partition(lb)[2]] +
                    t[i + 1:])
            else:
                i += 1

            # Prepare to transform line to new indent:
            line_start = i
            old_line += [lb]
            indent = get_indent(old_line)
            if indent == None:
                # Nothing to change.
                if i >= len(t):
                    break
                continue
            # Do actual transformation:
            while (len(old_line) > 0 and
                    is_whitespace_token(old_line[0])):
                old_line = old_line[1:]
            if len(added) > 0:
                new_line = [indent + added] + old_line
            else:
                new_line = [indent[:-removed]] + old_line
            new_tokens += new_line
            if i >= len(t):
                break
            continue
        i += 1
    if not had_trailing_lb and (
            len(new_tokens) > 0 and
            new_tokens[-1].endswith(lb)):
        new_tokens[-1] = new_tokens[-1][:-len(lb)]
        if len(new_tokens[-1]) == 0:
            new_tokens = new_tokens[:-1]
    if was_str:
        return untokenize(new_tokens)
    return new_tokens

def token_outside_brackets_idx(
        s, t, startidx = 0, startbdepth = 0):
    assert(type(s) == list and (
        len(s) == 0 or type(s[0]) == str))
    assert(type(t) == str)
    i = startidx
    bdepth = startbdepth
    while i < len(s):
        if s[i] in {"(", "[", "{"}:
            bdepth += 1
        if s[i] in {")", "]", "}"}:
            bdepth -= 1
            if bdepth < 0:
                return -1
        if s[i] == t:
            return i
        i += 1
    return -1

def get_statement_ranges_ex_with_confused_linebreaks(t,
        range_type="expr"):
    result = []
    assert(type(t) in {list, tuple})
    i = 0
    while (i < len(t) and
            t[i].strip(" \r\n\t") == ""):
        i += 1
    if i >= len(t):
        return []
    if t[i] in {"return", "await"}:
        if range_type != "expr":
            return []
        i += 1  # Past 'return' keyword.
        while (i < len(t) and
                t[i].strip(" \r\n\t") == ""):
            i += 1
        if i >= len(t):  # This can happen for 'return'.
            return []
        return [[i, len(t), t[i]]]
    elif (t[i] in {"type"}) or \
            (t[i] == "extend" and
            nextnonblank(t, i) == "type"):
        is_extend = (t[i] == "extend")
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
        elif range_type == "expr" and not is_extend:
            while (i < len(t) and
                    t[i] != "{" and
                    t[i] != "base"):
                i += 1
            if i >= len(t) or t[i] != "base":
                return []
            i += 1  # Past 'base' kw.
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
            result.append([block_start, i, "do"])
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
                if i < len(t) and t[i] == "as":
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
                return ([[expr_start, i,
                    stmt_type]])
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
            result.append([block_start, i,
                stmt_type])
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
            while (i < len(t) and
                    t[i].strip(" \r\n\t") == ""):
                i += 1
            expr_start = i
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
                result.append([expr_start, expr_end + 1,
                    "else" if not is_elseif else "elseif"
                ])
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
                result.append([block_start, i,
                    "else" if not is_elseif else "elseif"])
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

cdef firstnonblankidx(t):
    cdef int tlen, idx
    tlen = len(t)
    idx = 0
    while (idx < tlen and
            t[idx].strip(" \r\n\t") == ""):
        idx += 1
    if idx >= tlen:
        return -1
    return idx

cdef firstnonblank(t):
    cdef int tlen, idx
    tlen = len(t)
    idx = 0
    while (idx < tlen and
            t[idx].strip(" \r\n\t") == ""):
        idx += 1
    if idx >= tlen:
        return ""
    return t[idx]

cdef nextnonblank(list t, int idx, int no=1):
    cdef int tlen
    tlen = len(t)
    while no > 0:
        idx += 1
        while (idx < tlen and
                t[idx].strip(" \r\n\t") == ""):
            idx += 1
        no -= 1
    if idx >= tlen:
        return ""
    return t[idx]

cdef nextnonblankidx(list t, int idx, int no=1):
    cdef int tlen
    tlen = len(t)
    while no > 0:
        idx += 1
        while (idx < tlen and
                t[idx].strip(" \r\n\t") == ""):
            idx += 1
        no -= 1
    if idx >= tlen:
        return -1
    return idx

cdef prevnonblank(list t, int idx, int no=1):
    while no > 0:
        idx -= 1
        while (idx >= 0 and
                t[idx].strip(" \r\n\t") == ""):
            idx -= 1
        no -= 1
    if idx < 0:
        return ""
    return t[idx]

cdef prevnonblankidx(list t, int idx, int no=1):
    while no > 0:
        idx -= 1
        while (idx >= 0 and
                t[idx].strip(" \r\n\t") == ""):
            idx -= 1
        no -= 1
    if idx < 0:
        return -1
    return idx

def nextnonblank_py(t, idx):
    return nextnonblank(t, int(idx))

def firstnonblank_py(t):
    return firstnonblank(t)

def firstnonblankidx_py(t):
    return firstnonblankidx(t)

def nextnonblanksameline(t, idx, no=1):
    while no > 0:
        idx += 1
        while (idx < len(t) and
                t[idx].strip(" \r\n\t") == ""):
            if "\n" in t[idx] or "\r" in t[idx]:
                return ""
            idx += 1
        no -= 1
    if idx >= len(t):
        return ""
    return t[idx]

def expr_nonblank_equals(
        v1, v2, any_match_value=None,
        throw_error_with_details=False,
        pair_match_prefix=None,
        ):
    if type(v1) == str:
        v1 = tokenize(v1)
    if type(v2) == str:
        v2 = tokenize(v2)

    # A map to store which pair values we had, so later pair
    # placeholders can enforce the value stays the same:
    pair_map = dict()

    # Tracking line and token numbers:
    line1 = 1
    prevline1starttok = 0
    line1starttok = 0
    i1 = 0
    line2 = 1
    prevline2starttok = 0
    line2starttok = 0
    i2 = 0

    # Start loop checking for token equality:
    while True:
        while (i1 < len(v1) and (v1[i1] == "" or
                is_whitespace_token(v1[i1]))):
            if "\n" in v1[i1] or "\r" in v1[i1]:
                prevline1starttok = line1starttok
                line1starttok = i1 + 1
                line1 += 1
            i1 += 1
        while (i2 < len(v2) and (v2[i2] == "" or
                is_whitespace_token(v2[i2]))):
            if "\n" in v2[i2] or "\r" in v2[i2]:
                prevline2starttok = line2starttok
                line2starttok = i2 + 1
                line2 += 1
            i2 += 1
        if i1 >= len(v1):
            return (i2 >= len(v2))
        elif i2 >= len(v2):
            return False
        match = True
        if (v1[i1] != v2[i2]) and (
                any_match_value == None or
                (v1[i1] != any_match_value and
                v2[i2] != any_match_value)):
            match = False
            # Check our pair mechanics:
            if (pair_match_prefix != None and (
                    v1[i1].startswith(pair_match_prefix) or
                    v2[i2].startswith(pair_match_prefix)) and (
                    not v1[i1].startswith(pair_match_prefix) or
                    not v2[i2].startswith(pair_match_prefix))):
                # One of these is a pair placeholder.
                # See which one it is:
                v1_is_pairval = (v1[i1].startswith(
                    pair_match_prefix
                ))
                pair_val = v1[i1]
                nonpair_val = v2[i2]
                if not v1_is_pairval:
                    pair_val = v2[i2]
                    nonpair_val = v1[i1]
                # A pair placeholder can match anything, but if
                # used multiple times only the same recurring value:
                if pair_val in pair_map:
                    # Needs to be the same recurring!
                    match = (pair_map[pair_val] == nonpair_val)
                else:
                    # Set what the next occurences need to match.
                    pair_map[pair_val] = nonpair_val
                    match = True
            # (End of pair handling code above.)
        if not match:
            if throw_error_with_details:
                raise ValueError("Tokens don't match, "
                    "diverged at positions #" + str(i1) +
                    "(value 1 line " + str(line1) +
                    ") and #" + str(i2) +
                    "(value 2 line " + str(line2) +
                    "), at:\n  (value1 excerpt follows)\n" +
                    str(untokenize(v1[prevline1starttok:
                        i1 + 10])) + "\n" +
                    "  (value2 excerpt follows)\n" +
                    str(untokenize(v2[prevline2starttok:
                        i2 + 10])) + "\n" +
                    "Exact mismatch was: '" + str(v1[i1]) +
                    "' vs '" +
                    str(v2[i2]) + "'")
            return False
        i1 += 1
        i2 += 1

def find_start_of_call_index_chain(s, i, debug=False):
    if debug:
        print("find_start_of_call_index_chain(): " +
              "searching in " + str(s[i - 10:i + 10]) +
              " from index " + str(i) +
              "/token '" + str(s[i]) + "'")
    while (i >= 0 and
            is_whitespace_token(s[i])):
        i -= 1
    if debug:
        print("find_start_of_call_index_chain(): " +
              "backed past whitespace to index " + str(i) +
              "/token '" + str(s[i] if i >= 0 else None) + "'")
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
            if t[i] != "func" or prevnonblank(t, i) == "extend":
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

cpdef tokenize(str s):
    cdef set one_char_toks
    cdef str first_c
    cdef list tokens
    cdef int len_s, offset_s, offset_s2

    one_char_toks = {".", ",",
        "{",  "[", "(", ")", "]", "}"}
    string_start_toks = {"'", "\""}
    whitespace_toks = {" ", "\t", "\r", "\n"}
    longer_token_start_toks = (
        string_start_toks.union(whitespace_toks.union({"#"}))
    )
    tokens = []
    offset_s = 0
    len_s = len(s)
    while len_s > offset_s:
        first_c = s[offset_s]
        if first_c in one_char_toks:
            # This conditional is a perf tweak.
            # We avoid calling the get_next_token() when it's
            # already obvious that the token is a trivial one
            # character item.
            if first_c == ",":
                # HACK XXX: Too much buggy code in 'later' call
                # parsing in our translator breaks when there's
                # a comma at the end of a func argument list.
                # Such a comma is valid, but there are too many
                # bugs and the code isn't worth fixing properly
                # given we just use it for bootstrapping.
                # Therefore, simply don't return such commas
                # at all as potential tokens.
                offset_s2 = offset_s + 1
                while offset_s2 < len_s:
                    if s[offset_s2] == " " or \
                            s[offset_s2] == "\n" or \
                            s[offset_s2] == "\t" or \
                            s[offset_s2] == "\r":
                        offset_s2 += 1
                        continue
                    break
                if offset_s2 < len_s and \
                        s[offset_s2] == ")":
                    # We need to skip this comma without
                    # returning it.
                    offset_s += 1
                    continue
            tokens.append(s[offset_s])
            offset_s += 1
            continue
        if (first_c in longer_token_start_toks or
                (first_c == "b" and offset_s + 1 < len_s and
                s[offset_s + 1] in string_start_toks)):
            t = get_next_token(s[offset_s:])
            len_t = len(t)
        else:
            lookahead = 10
            while True:
                t = get_next_token(
                    s[offset_s:offset_s + lookahead]
                )
                len_t = len(t)
                if len_t < lookahead:
                    break
                lookahead += 100
        if len_t == 0:
            return tokens
        tokens.append(t)
        offset_s += len_t
    return tokens

cdef int is_h64op_with_righthand(str v):
    if v in {"and", "or", "not", "+", "-", "*", "/",
            ">", "<", "->", "**",
            ".", "!=", "=", "=="}:
        return True
    if len(v) == 2 and v[1] == "=":
        return True
    return False

cdef int is_h64op_with_lefthand(str v):
    if v in {"and", "or", "+", "-", "*", "/",
            ">", "<", "->", ".", "!=", "=", "==",
            ":", "**"}:
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

must_continue_after_toks = {
    "->", "(", "[", "{", "later",
    "elseif", "throw", "var", "const",
    "func", "if", "while", "for", "do",
    ",", "else", "as", "in", "from",
    "rescue", "finally", "elseif",
    "enum", "await"}
must_continue_before_toks = {
    "->", "(", "[", ":", "later", "parallel",
    "repeat", "elseif", "ignore",
    ",", "else", "as", "in", "from",
    "rescue", "finally", "elseif"
}
must_stop_before_toks = {
    # XXX: does NOT include "func" or "if"! (Can be inline!)
    "var", "const", "throw", "return",
    "while", "with", "do", "enum", "type", "import",
    "for", "await",
}

cpdef get_next_statement(list s, int pos):
    cdef int s_len, bracket_nesting, token_count, \
        is_string_continuation, z
    cdef str t, last_nonwhitespace_token

    s_len = len(s)
    if s_len <= pos:
        return []
    last_nonwhitespace_token = ""
    token_count = 0
    bracket_nesting = 0
    _future_last_token = None
    i = pos - 1
    while i + 1 < s_len:
        if (_future_last_token != None and
                _future_last_token.strip(" \t\r\n") != ""):
            last_nonwhitespace_token = _future_last_token
        i += 1
        _future_last_token = s[i]
        t = s[i]
        token_count += 1
        if t in ["(", "[", "{"]:
            bracket_nesting += 1
        if t in [")", "]", "}"]:
            bracket_nesting -= 1
        if t == "extend":
            pre_i = i
            while not (s[i] in {"func", "enum", "type"}) and \
                    i + 1 < s_len:
                token_count += 1
                i += 1
                t = s[i]
                if s[i].strip(" \t\r\n") != "":
                    last_nonwhitespace_token = _future_last_token
                    _future_last_token = s[i]
            if i + 1 >= s_len:
                raise RuntimeError("Failed to find extend "
                    "statement type: " + str(s[pre_i:pre_i + 10]) + "...")
        if (bracket_nesting == 0 and
                last_nonwhitespace_token != "" and (
                (t in must_stop_before_toks and
                 (last_nonwhitespace_token != "extend" or
                  (t not in {"func", "enum", "type"}))) or (
                is_whitespace_token(t) and
                nextnonblank(s, i) in
                must_stop_before_toks))):
            return s[pos:pos + token_count - 1]  # Stop EXCLUDING token.
        if ((last_nonwhitespace_token != "" and (
                is_whitespace_token(t) and
                nextnonblank(s, i) in
                must_continue_before_toks)) or
                (t in must_continue_after_toks or
                    is_whitespace_token(t) and
                    last_nonwhitespace_token in
                    must_continue_after_toks)):
            continue
        if (bracket_nesting == 0 and
                t in ("}", "]", ")")):
            nt = nextnonblank(s, i)
            if (not nt in must_continue_before_toks and
                    not is_h64op_with_lefthand(nt) and
                    not nt in {"(", "{", "["}) :
                return s[pos:pos + token_count]
        if (bracket_nesting == 0 and
                (t.endswith("\n") or t.endswith("\r")) and
                last_nonwhitespace_token != "," and
                not is_h64op_with_righthand(last_nonwhitespace_token) and
                not last_nonwhitespace_token in {"in", "as"} and
                not is_h64op_with_lefthand(nextnonblank(s, i)) and
                not nextnonblank(s, i) in must_continue_before_toks
                ):
            is_string_continuation = False
            if (last_nonwhitespace_token.endswith("\"") or
                    last_nonwhitespace_token.endswith("'")):
                z = pos + token_count
                while z < len(s) and s[z].strip(" \t\r\n") == "":
                    z += 1
                if z < len(s) and (
                        s[z].endswith("\"") or s[z].endswith("'")):
                    is_string_continuation = True
            if not is_string_continuation:
                return s[pos:pos + token_count]  # Stop INCLUDING token.
        assert(bracket_nesting >= 0), \
            "failed to find terminating bracket in: " + str(s)
    return s[pos:]

def is_whitespace_statement(tokens):
    for token in tokens:
        for c in token:
            if not is_whitespace_token(c):
                return False
    return True

cpdef split_toplevel_statements(s, skip_whitespace=True):
    assert(type(s) in {list, tuple})
    if len(s) == 0:
        return []
    statements = []
    len_s = len(s)
    i = 0
    while i < len_s:
        next_stmt = get_next_statement(s, i)
        if len(next_stmt) == 0:
            return statements
        if "extend" in next_stmt and \
                not ("type" in next_stmt) and \
                not ("func" in next_stmt) and \
                not ("enum" in next_stmt):
            raise RuntimeError("Unexpectedly got broken "
                "extend result: " + str((
                    s[i:i + 15], next_stmt)))
        if (not skip_whitespace or
                not is_whitespace_statement(
                next_stmt)):
            statements.append(list(next_stmt))
            if ("".join(statements[-1]).strip("\r\n") ==
                    "".join(statements[-1])):
                statements[-1] += ["\n"]
        i += len(next_stmt)
    return statements

_brackets = {"(", "[", "{",
    "}", "]", ")"}

cpdef is_bracket(str v):
    return v in _brackets

cpdef tokens_need_spacing(str v1, str v2):
    if v1 == "" or v2 == "":
        return False
    if (is_whitespace_token(v1) or
            is_whitespace_token(v2)):
        return False
    if (v1 in {"@", "=", ","}) and (
            identifier_or_keyword(v2) or is_number_token(v2)):
        return False
    if (v2 in {"@", "=", ","}) and (
            identifier_or_keyword(v1) or is_number_token(v1) or
            v1.endswith("'") or v1.endswith('"')):
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
            len(v2) == 2 and not has_any_ascii_letters(v2)):
        return False
    return True

cpdef untokenize(tokens):
    assert(type(tokens) in {list, tuple})
    cdef str prevtoken
    cdef list result_l

    result_l = []
    prevtoken = ""
    for token in tokens:
        if (token == " " or token == "\n" or
                token == "." or token == "," or
                token == "[" or token == "]" or
                token == "(" or token == ")" or
                token == "{" or token == "}"):  # Perf tweak.
            result_l.append(token)
            prevtoken = token
            continue
        if prevtoken != "" and \
                tokens_need_spacing(prevtoken, token):
            result_l.append(" ")
        result_l.append(token)
        prevtoken = token
    return "".join(result_l)

def tree_transform_statements(
        code, callback_statement_list, inside_out=False
        ):
    if (type(code) != str and (
            type(code) not in {list, tuple} or
            (len(code) > 0 and type(code[0]) != str))):
        raise TypeError("code must be string or "
            "list of tokens (=list of strings)")
    was_string = False
    if type(code) == str:
        code = tokenize(code)
        was_string = True
    new_statements = []
    statements = split_toplevel_statements(
        code, skip_whitespace=False
    )
    if callback_statement_list != None and not inside_out:
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
        new_statements.append(statement)
    if callback_statement_list != None and inside_out:
        new_statements = callback_statement_list(
            new_statements
        )
        assert(type(new_statements) == list)
        assert(len(new_statements) == 0 or (
            type(new_statements[0]) == list and
            (len(new_statements[0]) == 0 or
            type(new_statements[0][0]) == str)))
    for statement in new_statements:
        final_tokens += statement
        if ("".join(final_tokens) ==
                "".join(final_tokens).strip("\r\n")):
            final_tokens += ["\n"]
    if was_string:
        return untokenize(final_tokens)
    return final_tokens

def get_leading_whitespace(st):
    if type(st) == str:
        st = [st]
    len_st = len(st)
    leading = ""
    i = 0
    while i < len_st:
        lstrip = st[i].lstrip(" \r\n\t")
        if lstrip != "":
            len_diff = (len(st[i]) -
                len(lstrip))
            leading += st[i][:len_diff]
            return leading
        else:
            leading += st[i]
        i += 1
    return leading

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
                fname = "_f2anon" + str(uuid.uuid4()).replace("-", "")
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

cpdef transform_h64_with_to_do_rescue(_s):
    cdef int i, slen, bdepth
    cdef int has_later, was_string
    cdef list s, new_tokens

    s = []
    was_string = False
    if type(_s) == list:
        s = _s
    elif type(_s) == tuple:
        s = list(_s)
    else:
        was_string = True
        s = tokenize(
            _s.replace("\r\n", "\n").replace("\r", "\n")
        )
    new_tokens = []
    i = 0
    slen = len(s)
    while i < slen:
        if s[i] == "with":
            expr_with = []
            i += 1
            has_later = False
            bdepth = 0
            while i < slen and (
                    bdepth > 0 or s[i] != "as"
                    ):
                if s[i] in {"(", "{", "["}:
                    bdepth += 1
                    i += 1
                    continue
                if s[i] in {")", "}", "]"}:
                    bdepth -= 1
                    i -= 1
                    continue
                if s[i] ==  "later":
                    has_later = True
                expr_with.append(s[i])
                i += 1
            assert(s[i] == "as" and i + 2 < slen and
                   s[i + 2] == "{")
        new_tokens.append(s[i])
    if was_string:
        new_tokens = untokenize(new_tokens)
    return new_tokens

cpdef sanity_check_h64_codestring(s, filename="", modname=""):
    cdef int col, line, i
    cdef list tokens, bracket_nesting_orig_loc,\
        bracket_nesting
    cdef str reverse_bracket, token

    cdef set opening_brackets_set = {"(", "{", "["}
    cdef set closing_brackets_set = {")", "}", "]"}
    cdef set string_quote_set = {"'", '"'}

    tokens = []
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
    for _token in tokens:
        token = _token
        i += 1
        assert(tokens[i] == token)
        if (token == "else" and
                nextnonblank(tokens, i) == "if"):
            raise ValueError("found invalid 'else if'" + (
                " in " + modname if modname != None else ""))
        if ((is_identifier(token) and
                nextnonblanksameline(tokens, i)
                    in string_quote_set) or (
                bracket_nesting[-1:] == ["("] and
                is_identifier(tokens[i]) and
                nextnonblank(tokens, i) in string_quote_set)):
            raise ValueError(("" if (modname == "" or
                modname == None) else ("in module " +
                str(modname) + " ")) +
                ("" if (filename == "" or
                filename == None) else ("in file " +
                str(filename) + " ")) +
                "in line " + str(line) + ", col " + str(col) + ": "
                "identifier followed by spurious string literal, "
                "did you forget a '+'?")
        if ((is_identifier(nextnonblanksameline(tokens, i)) and
                tokens[i][:1] in string_quote_set) or (
                bracket_nesting[-1:] == ["("] and (
                is_identifier(nextnonblank(tokens, i)) and
                tokens[i][:1] in string_quote_set))):
            raise ValueError(("" if (modname == "" or
                modname == None) else ("in module " +
                str(modname) + " ")) +
                ("" if (filename == "" or
                filename == None) else ("in file " +
                str(filename) + " ")) +
                "in line " + str(line) + ", col " + str(col) + ": "
                "string literal followed by spurious identifier, "
                "did you forget a '+'?")
        if token == "," and nextnonblank(tokens, i) == ",":
            raise ValueError(("" if (modname == "" or
                modname == None) else ("in module " +
                str(modname) + " ")) +
                ("" if (filename == "" or
                filename == None) else ("in file " +
                str(filename) + " ")) +
                "in line " + str(line) + ", col " + str(col) + ": " +
                "invalid double use of ','")
        if token in opening_brackets_set:
            bracket_nesting_orig_loc.append((line, col))
            bracket_nesting.append(token)
        elif token in closing_brackets_set:
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
        if "\n" in token or "\r" in token:
            token_per_line = (token.replace("\r\n", "\n").
                replace("\r", "\n").split("\n"))
            line += len(token_per_line) - 1
            col = 1 + len(token_per_line[-1])
        else:
            col += len(token)

def get_indent(statement):
    s = statement
    if type(s) == list:
        if len(s) > 0 and type(s[0]) == list:
            s = flatten(s)
        s = untokenize(s)
    assert(type(s) == str)
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

def make_kwargs_in_call_tailing(s):
    was_str = False
    if type(s) == str:
        s = tokenize(s)
        was_str = True
    i = 1
    while i < len(s):
        if s[i] != "(":
            i += 1
            continue

        # Check if this is a function definition (which
        # we don't want to touch):
        is_fdef = False
        k = i - 1
        while k >= 0 and s[k].strip(" \t") == "":
            k -= 1
        if k >= 0 and (s[k] == "func" or (
                s[k].strip(" \t\r\n") == "" and
                prevnonblank(s, k) == "func")):
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
                if (s[k] in notdef_kw or (s[k].strip(" \t") != "" and
                        s[k].strip("\r\n") == "") or s[k] == "=" or
                        (len(s[k]) == 2 and s[k][1] == "=")):
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
                    (s[k + 1] == ")" or (s[k + 1] == "," and
                    nextnonblank(s, k + 1) == ")"))):
                arg_indexes.append((
                    current_arg_start,
                    current_arg_eq, k + 1))
                k += 1
                while (k < len(s) and s[k] != ")"):
                    k += 1
                break
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

def mirror_brackets(s):
    revs = {
        "(": ")",
        ")":"(",
        "[": "]",
        "]":"[",
        "{": "}",
        "}":"{"
    }
    snew = ""
    i = 0
    while i < len(s):
        if s[i] in revs:
            snew += revs[s[i]]
        else:
            snew += s[i]
        i += 1
    return snew

def idx_of_lineend(st, i, forward_first=False):
    assert(type(st) == list)
    assert(len(st) == 0 or type(st[0]) == str)
    assert(i >= 0 and i < len(st))
    if len(st) == 0:
        return None
    orig_i = i
    if st[i].strip(" \r\t\n") != "":
        return None

    if not forward_first:
        # First, search backward:
        while True:
            if st[i].startswith("\n"):
                return i
            if (i - 1 < 0 or
                    st[i - 1].strip(" \t\r\n") != ""):
                break
            i -= 1

    # Try a forward search then:
    i = orig_i
    while True:
        if st[i].startswith("\n"):
            return i
        if (i + 1 >= len(st) or
                (not st[i + 1].startswith("\n") and
                st[i + 1].strip(" \t\r\n") != "")):
            break
        i += 1

    if forward_first:
        # Finally, search backward:
        i = orig_i
        while True:
            if st[i].startswith("\n"):
                return i
            if (i - 1 < 0 or
                    st[i - 1].strip(" \t\r\n") != ""):
                break
            i -= 1

    return None

def cut_tokens_after_lineend(st, i):
    assert(type(st) == list)
    assert(len(st) == 0 or type(st[0]) == str)
    assert(i >= 0 and i < len(st))
    if len(st) == 0:
        return []
    i = idx_of_lineend(st, i)
    if i == None:
        raise ValueError("no line split point found")
    return st[:i]

def stmt_is_later_call(st, include_later_ignore=False,
        include_return_later=False):
    if type(st) == str:
        st = tokenize(st)
    bdepth = 0
    i = 0
    while i < len(st):
        if st[i] in {"(", "[", "{"}:
            bdepth += 1
        elif st[i] in {")", "]", "}"}:
            bdepth -= 1
            assert(bdepth >= 0)
        if bdepth == 0 and (st[i] == "later" and (
                include_return_later or
                prevnonblank(st, i) != "return")):
            if (include_later_ignore or
                    nextnonblank(st, i) != "ignore"):
                return True
        i += 1
    return False

def stmt_uses_banned_things(
        st, followup_sts, nestings=[]
        ):
    startkw = firstnonblank(st)

    # Figure out if this is banned:
    if stmt_is_later_call(st, include_later_ignore=False):
        i = len(nestings) - 1
        while i >= 0:
            if nestings[i] in {"rescue", "finally", "while",
                    "for"}:
                followed_by_return = False
                for followup_st in followup_sts:
                    if firstnonblank(followup_st) == "return":
                        followed_by_return = True
                if not followed_by_return:
                    raise ValueError("Use of 'later' inside '" +
                        str(nestings[i]) + "' blocks not "
                        "allowed unless followed by a 'return'. "
                        "(Other than 'later ignore'.)")
            i -= 1
    elif startkw in {"continue", "break", "return"}:
        i = len(nestings) - 1
        while i >= 0:
            if nestings[i] in {"finally"}:
                raise ValueError("Use of '" + str(startkw) +
                    "inside 'finally' blocks not allowed.")
            i -= 1

    # Okay, recurse deeper:
    nestingtracked = {"func", "do",
        "with", "while", "for", "if",
        "type"
    }
    add_nesting = None
    if startkw in nestingtracked:
        add_nesting = startkw
    ranges = get_statement_block_ranges(st)
    for block_range in ranges:
        add_nesting = None
        if startkw in nestingtracked:
            add_nesting = startkw
        sts = split_toplevel_statements(
            st[block_range[0]:block_range[1]]
        )
        if add_nesting == "do":
            add_nesting = block_range[2]
        result = stmt_list_uses_banned_things(
            sts, nestings=nestings + (
                [] if add_nesting is None else
                [add_nesting]
            )
        )
        if result != None:
            return result
    return None


def stmt_list_uses_banned_things(sts, nestings=[]):
    if type(sts) == str:
        sts = split_toplevel_statements(tokenize(sts))
    if (type(sts) == list and len(sts) > 0 and
            type(sts[0]) == str):
        sts = split_toplevel_statements(
            sts
        )
    assert(type(sts) == list and (
           len(sts) == 0 or (type(sts[0]) == list and (
           len(sts[0]) == 0 or type(sts[0][0]) == str))))
    idx = -1
    for st in sts:
        idx += 1
        assert(type(st) == list and
            (len(st) == 0 or type(st[0]) == str))
        assert(type(st) == list)
        assert(len(st) == 0 or type(st[0]) == str)
        result = stmt_uses_banned_things(
            st, sts[idx + 1:], nestings=nestings
        )
        if result != None:
            return result
    return None


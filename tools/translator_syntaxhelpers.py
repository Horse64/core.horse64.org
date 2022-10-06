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
            (ord(x[0]) < ord("A") or ord(x[0]) > ord("Z")))):
        return False
    if x in {"if", "func", "import", "else",
            "type", "do", "rescue", "finally",
            "from",
            "var", "const", "elseif", "while",
            "for", "in", "not", "and", "or"}:
        return False
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
                    ":"}):
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


def tokenize(s):
    tokens = []
    while len(s) > 0:
        t = get_next_token(s)
        if len(t) == 0:
            return tokens
        tokens.append(t)
        s = s[len(t):]
    return tokens


def is_h64_operator(v):
    if v in {"and", "or", "not", "+", "-", "*", "/",
            ">", "<", "->", ".", "!=", "=", "=="}:
        return True
    if len(v) == 2 and v[1] == "=":
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
                    "else"} and not is_h64_operator(s[j]) and
                    not s[j] in {"(", "{", "["}):
                return s[:token_count + 1]
        if (bracket_nesting == 0 and
                (t.endswith("\n") or t.endswith("\r")) and
                not is_h64_operator(last_nonwhitespace_token)
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


def split_toplevel_statements(s):
    def is_whitespace_statement(tokens):
        for token in tokens:
            for c in token:
                if c not in [" ", "\r", "\n", "\t"]:
                    return False
        return True
    assert(type(s) in {list, tuple})
    if len(s) == 0:
        return []
    statements = []
    while True:
        next_stmt = get_next_statement(s)
        if len(next_stmt) == 0:
            return statements
        if not is_whitespace_statement(next_stmt):
            statements.append(next_stmt)
        s = s[len(next_stmt):]
    return statements


def untokenize(tokens):
    assert(type(tokens) in {list, tuple})
    result = ""
    prevtoken = ""
    for token in tokens:
        assert(type(token) == str)
        if prevtoken != "" and \
                prevtoken not in {".", "(", "[", "{",
                    "}", "]", ")", ","} and \
                token not in {".", ",", "(", "[", "{",
                    "}", "]", ")", "\\"} and \
                not is_whitespace_token(token) and \
                not is_whitespace_token(prevtoken):
            result += " "
        result += token
        prevtoken = token
    return result




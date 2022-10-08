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
    tokenize, untokenize,
    is_identifier, as_escaped_code_string,
    is_whitespace_token, get_next_token,
    split_toplevel_statements, nextnonblank,
    nextnonblankidx,
    firstnonblank, firstnonblankidx,
    get_next_statement, prevnonblank, prevnonblankidx,
    sanity_check_h64_codestring,
    separate_out_inline_funcs,
    get_global_standalone_func_names,
    identifier_or_keyword, is_h64op_with_righthand,
    is_number_token, find_start_of_call_index_chain
)


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
                    s[i] in ("as_str", "as_bytes", "to_num") and
                        nextnonblank(s, i) == "(" and
                        nextnonblank(s, i, no=2) == ")") or (
                    s[i] in ("add", "sort", "trim", "find",
                        "reverse",
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
            elif cmd == "to_num":
                insert_call = ["float"]
            elif cmd == "add":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_add"]
            elif cmd == "join":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_join"]
            elif cmd == "trim":
                insert_call = ["_translator_runtime_helpers",
                    ".", "_container_trim"]
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
                    "repeat", "trim", "glyph_sub"):
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
            assert(istart <= i)
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


def get_first_nonempty_line_indent(s):
    if type(s) == list:
        s = untokenize(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    for sline in s.split("\n"):
        if sline.strip(" \t") == "":
            continue
        i = 0
        while (i < len(sline) and
                sline[i] == " " or sline[i] == "\t"):
            i += 1
        return sline[:i]
    return None

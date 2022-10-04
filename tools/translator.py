#!/usr/bin/python3

# Copyright (c) 2020-2022,  ellie/@ell1e & Horse64 Team (see AUTHORS.md).
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
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

VERSION="2022-09-16"

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
translated_files = {}

DEBUG_ENABLE = False
DEBUG_ENABLE_CONTENTS = False
DEBUG_ENABLE_TYPES = False
DEBUG_ENABLE_REMAPPED_USES = False

remapped_uses = {
    "compiler@core.horse64.org": {
        "compiler.run_file":
            "_translator_runtime_helpers._compiler_run_file",
    },
    "files@core.horse64.org": {
        "files.get_working_dir" : "_remapped_os.getcwd",
    },
    "math@core.horse64.org": {
        "math.min": "_translator_runtime_helpers._math_min",
        "math.max": "_translator_runtime_helpers._math_max",
        "math.round": "_translator_runtime_helpers._math_round",
    },
    "path@core.horse64.org": {
        "path.basename" : "_remapped_os.path.basename",
        "path.dirname": "_remapped_os.path.dirname",
    },
    "process@core.horse64.org": {
        "process.args": "(_remapped_sys.argv[1:])",
        "process.run":
            "_translator_runtime_helpers._process_run",
    },
    "system@core.horse64.org": {
        "system.exit" : "_remapped_sys.exit",
        "system.self_exec_path" :
            "(lambda: _translated_program_main_script_file)",
    },
}


class RegisteredType:
    def __init__(self, type_name, module_path, package_name):
        self.module = module_path
        self.pkgname = package_name
        self.name = type_name
        self.init_code = ""
        self.funcs = {}


known_types = {}


def register_type(type_name, module_path, package_name):
    global known_types
    package_name_part = ""
    if package_name is not None:
        package_name_part = "@" + package_name
    if (module_path + "." + type_name +
            package_name_part in known_types):
        raise ValueError("found duplicate type " +
            module_path + "." + type_name)
    known_types[module_path + "." + type_name + package_name_part] = (
        RegisteredType(type_name, module_path, package_name)
    )
    if DEBUG_ENABLE and DEBUG_ENABLE_TYPES:
        print("tools/translator.py: debug: registered type " +
            module_path + "." + type_name + package_name_part)


def get_type(type_name, module_path, package_name):
    if package_name is None:
        return known_types[module_path + "." + type_name]
    return known_types[module_path + "." + type_name + "@" +
        package_name]


class TranslatedProjectInfo:
    def __init__(self):
        self.code_folder = None
        self.repo_folder = None
        self.package_name = None
        self.code_relpath = None


def horp_ini_string_get_package_name(s):
    lines = s.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [(line.rpartition("#")[0].rstrip() if
        "#" in line else line.rstrip()) for line in lines]
    section = None
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
        if (section == "package" and
                line.startswith("name=") or line.startswith("name ")):
            while len(line) >= 5 and line[4] == " ":
                line = "name" + line[5:]
            if line.startswith("name="):
                result = line.partition("=")[2].strip()
                if "." in result:
                    return result
                return None
    return None


def sublist_index(full_list, sub_list):
    if len(sub_list) > len(full_list) or len(sub_list) == 0:
        return -1
    i = 0
    while i < len(full_list) - (len(sub_list) - 1):
        match = True
        k = 0
        while k < len(sub_list):
            if full_list[i + k] != sub_list[k]:
                match = False
                break
            k += 1
        if match:
            return i
        i += 1
    return -1


def is_whitespace_token(s):
    if len(s) == 0:
        return False
    for char in s:
        if char not in [" ", "\t", "\n", "\r"]:
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
                (t.endswith("\n") or t.endswith("\r")) and
                last_nonwhitespace_token not in {
                    "and", "or", "not", "+", "-", "*", "/",
                    ">", "<", "->",
                } and not last_nonwhitespace_token.endswith("=")):
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
                if c not in [" ", "\r", "\n", "|t"]:
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


def translate_expression_tokens(s, module_name, package_name,
        parent_statements=[], known_imports=None,
        add_indent="", repo_package_name=None):
    s = list(s)
    assert("_remapped_os" not in s)

    # Fix indent first:
    i = 0
    while i < len(s):
        t = s[i]
        if t.strip("\r\n ") == "" and (
                t.startswith("\r\n") or
                t.startswith("\n")):
            t += add_indent
            s[i] = t
        i += 1
    # Translate typename()/"throw"/"has_attr"/...:
    previous_token = None
    i = 0
    while i < len(s):
        if (s[i] == "typename" and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "h64_type"] + s[i + 1:]
        elif s[i] == "starts" and previous_token == ".":
            s[i] = "startswith"
        elif s[i] == "ends" and previous_token == ".":
            s[i] = "endswith"
        elif s[i] == "contains" and previous_token == ".":
            s[i] = "__contains__"
        elif s[i] == "throw" and previous_token != ".":
            s[i] = "raise"
        elif s[i] == "has_attr" and previous_token != ".":
            s[i] = "hasattr"
        if s[i].strip("\r\n\t ") != "":
            previous_token = s[i]
        i += 1

    # Add line continuation things:
    i = 0
    while i < len(s):
        if (s[i] in {">", "=", "<", "!", "+", "-", "/", "*",
                "%", "|", "^", "&", "~"} or
                s[i].endswith("=") or s[i] == "->") and (
                s[i + 1].strip(" \t\r\n") == "" and
                s[i + 1].strip(" \t") != ""):
            s = (s[:i + 1] + ["\\"] + [s[i + 1].lstrip(" \t")] +
                s[i + 2:])
        if ((s[i].endswith("\"") or s[i].endswith("'")) and
                i + 2 < len(s) and
                s[i + 1].strip(" \t\r\n") == "" and
                s[i + 1].strip(" \t") != ""):
            z = i + 2
            while z < len(s) and s[z].strip(" \t") == "":
                z += 1
            if (z < len(s) and (
                    s[z].endswith("\"") or s[z].endswith("'"))):
                s = (s[:i + 1] + ["+", "\\"] + [s[i + 1].lstrip(" \t")] +
                    s[i + 2:])
        i += 1
    # Translate remapped use to the proper remapped thing:
    i = 0
    while i < len(s):
        if (i > 1 and s[i - 1].strip(" \t\r\n") == "" and
                s[i - 2] == "import"):
            i += 1
            continue
        if len(s[i]) == 0 or (
                s[i][0] != "_" and
                (ord(s[i][0]) < ord("a") or
                    ord(s[i][0]) > ord("z")) and
                (ord(s[i][0]) < ord("A") or
                    ord(s[i][0]) > ord("Z"))):
            i += 1
            continue
        if len(known_imports) == 0:
            i += 1
            continue
        #print("s[i] " + str(s[i]))
        match = False
        match_package = None
        match_import_module = None
        match_item = None
        match_tokens = -1
        for known_import in known_imports:
            import_module_elements = (
                known_imports[known_import]
                    ["module"].split(".")
            )
            maybe_match = True
            k = 0
            while k < len(import_module_elements):
                if (k * 2 + i >= len(s) or
                        s[i + k * 2] !=
                        import_module_elements[k] or
                        (k + 1 < len(import_module_elements) and
                        (k * 2 + 1 + i >= len(s) or
                        s[i + k * 2 + 1] != "."))):
                    maybe_match = False
                    break
                k += 1
            def could_be_identifier(x):
                if (len(x) == 0 or (x[0] != "_" and
                        (ord(x[0]) < ord("a") or ord(x[0]) > ord("z")) and
                        (ord(x[0]) < ord("A") or ord(x[0]) > ord("Z")))):
                    return False
                if x in {"if", "func", "import", "else",
                        "var", "const", "elseif", "while",
                        "for", "in", "not", "and", "or"}:
                    return False
                return True
            maybe_match_tokens = -1
            maybe_match_item = None
            if (k * 2 + i < len(s) and
                    could_be_identifier(s[k * 2 + i])):
                maybe_match_item = s[k * 2 + i]
                maybe_match_tokens = k * 2 + i + 1 - i
            if maybe_match:
                #print((s[i], k, maybe_match_item, maybe_match,
                #    known_imports[known_import]
                #            ["module"],
                #    import_module_elements,
                #    maybe_match_tokens))
                pass
            if (maybe_match and (not match or
                    len(import_module_elements) >
                    len(match_import_module.split("."))) and
                    maybe_match_item != None):
                match = True
                match_import_module = (
                    known_imports[known_import]
                        ["module"]
                )
                match_package = (
                    known_imports[known_import]
                        ["package"]
                )
                match_tokens = maybe_match_tokens
                match_item = maybe_match_item
        if not match:
            i += 1
            continue
        remap_module_key = match_import_module + (
            "" if match_package is None else
            "@" + match_package)
        if remap_module_key in remapped_uses:
            remap_original_use = (
                match_import_module + "." + match_item
            )
            if DEBUG_ENABLE_REMAPPED_USES:
                print("tools/translator.py: debug: checking if " +
                    "use needs translation to remap: " +
                    remap_original_use + " in " + remap_module_key)
            for remapped_use in remapped_uses[remap_module_key]:
                if remapped_use == remap_original_use:
                    if DEBUG_ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: remapping " +
                            "use to the overridden expression: " +
                            remap_original_use + " in " + remap_module_key)
                    insert_tokens = tokenize(remapped_uses
                        [remap_module_key][remapped_use])
                    s = s[:i] + insert_tokens + s[i + match_tokens:]
                    i += len(insert_tokens)
                    continue
        i += 1

    # Remove "new" and "protect" since Python doesn't have these:
    i = 0
    while i < len(s):
        if s[i] == "new" or s[i] == "protect":
            s = s[:i] + s[i + 1:]
            continue
        i += 1
    # Translate {->} dict constructor:
    i = 0
    while i < len(s):
        if s[i] != "{":
            i += 1
            continue
        start_idx = i
        i += 1
        while i < len(s) and s[i].strip(" \t\r\n") == "":
            i += 1
            continue
        if s[i] != "->":
            i += 1
            continue
        i += 1
        while i < len(s) and s[i].strip(" \t\r\n") == "":
            i += 1
            continue
        if s[i] != "}":
            i += 1
            continue
        s = (s[:start_idx] +
            ["(", "dict", "(", ")", ")"] +
            s[i + 1:])
        i += 1
    # Translate inline "if":
    i = 0
    while i < len(s):
        if s[i] != "if":
            i += 1
            continue
        had_nonwhitespace_token = False
        z = i + 1
        condition_start_idx = z
        condition_end_idx = -1
        value_1_start_idx = -1
        value_1_end_idx = -1
        value_2_start_idx = -1
        value_2_end_idx = -1
        bracket_depth = 0
        while z < len(s):
            if (had_nonwhitespace_token and s[z] in {"(", "{"} and
                    bracket_depth == 0):
                condition_end_idx = z - 1
                break
            if s[z] in {"[", "(", "{"}:
                bracket_depth += 1
            if s[z] in {"]", ")", "}"}:
                bracket_depth -= 1
            if s[z].strip(" \t\r\n") == "":
                had_nonwhitespace_token = True
            z += 1
        if z >= len(s) or s[z] != "(":
            # Not an inline if.
            i += 1
            continue
        value_1_start_idx = z
        while z < len(s):
            if (z > value_1_start_idx and
                    bracket_depth == 0 and
                    s[z] == "else"):
                value_1_end_idx = z - 1
                break
            if s[z] in {"[", "(", "{"}:
                bracket_depth += 1
            if s[z] in {"]", ")", "}"}:
                bracket_depth -= 1
            z += 1
        assert(s[z] == "else")
        value_2_start_idx = z + 1
        while z < len(s):
            if (z > value_2_start_idx and
                    bracket_depth <= 1 and
                    s[z] == ")"):
                value_2_end_idx = z
                bracket_depth = 0
                break
            if s[z] in {"[", "(", "{"}:
                bracket_depth += 1
            if s[z] in {"]", ")", "}"}:
                bracket_depth -= 1
            z += 1
        #print("IF INLINE: " + str((
        #    s[condition_start_idx:condition_end_idx + 1],
        #    s[value_1_start_idx:value_1_end_idx + 1],
        #    s[value_2_start_idx:value_2_end_idx + 1])))
        transformed_tokens = (["("] + (["("] +
            s[value_1_start_idx:value_1_end_idx + 1] +
            [")"] + ["if"] +
            s[condition_start_idx:condition_end_idx + 1] +
            ["else"] +
            s[value_2_start_idx:value_2_end_idx + 1]
        ) + [")"])
        s = s[:i] + transformed_tokens + s[value_2_end_idx + 1:]
        i = i + len(transformed_tokens) + 1
    # Translate XYZ.as_str()/XYZ.len to str(XYZ)/len(XYZ)
    replaced_one = True
    while replaced_one:
        replaced_one = False
        i = 0
        while i < len(s):
            if (i > 0 and s[i - 1] == "." and (
                    s[i] in ("len") or (
                    i + 2 < len(s) and
                    s[i] in ("as_str", "to_num") and s[i + 1] == "(" and
                    s[i + 2] == ")") or (
                    i + 1 < len(s) and
                    s[i] in ("add", "sort", "find",
                        "join", "sub") and s[i + 1] == "("
                    ))):
                cmd = s[i]
                insert_call = ["str"]
                if cmd == "len":
                    insert_call = ["len"]
                elif cmd == "to_num":
                    insert_call = ["float"]
                elif cmd == "add":
                    insert_call = ["_translator_runtime_helpers",
                        ".", "_container_add"]
                elif cmd == "join":
                    insert_call = ["_translator_runtime_helpers",
                        ".", "_container_join"]
                elif cmd == "sub":
                    insert_call = ["_translator_runtime_helpers",
                        ".", "_container_sub"]
                elif cmd == "find":
                    insert_call = ["_translator_runtime_helpers",
                        ".", "_container_find"]
                elif cmd == "sort":
                    insert_call = ["_translator_runtime_helpers",
                        ".", "_container_sort"]
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
                if cmd in ("len"):
                    # Add in a ")":
                    s = s[:i - 1] + [")"] + s[i + 1:]
                elif cmd in ("add", "sort", "join", "find", "sub"):
                    # Truncate "(", ... and turn it to ",", ...
                    s = s[:i - 1] + [","] + s[i + 2:]
                else:
                    # Truncate "(", ")" to leave a ")":
                    s = s[:i - 1] + s[i + 2:]
                inserted_left_end = False
                bdepth = 0
                i -= 2
                while i >= 0:
                    if s[i] in {")", "]", "}"}:
                        bdepth += 1
                    elif s[i] in {"(", "[", "{"}:
                        bdepth -= 1
                    if (s[i] != "." and
                            not is_keyword_or_idf(s[i]) and
                            bdepth <= 0):
                        s = s[:i + 1] + insert_call + ["("] + s[i + 1:]
                        inserted_left_end = True
                        break
                    elif (i == 0 and is_keyword_or_idf(s[i]) and
                            bdepth <= 0):
                        s = insert_call + ["("] + s
                        inserted_left_end = True
                        break
                    i -= 1
                assert(inserted_left_end)
                #print("BEFORE REPLACEMENT: " +
                #    str(old_s[max(0, i - 10):i + 40]) +
                #    " AFTER: " +
                #    str(s[max(0, i - 10):i + 40]))
                break
            i += 1
    # Translate some keywords:
    i = 0
    while i < len(s):
        if s[i] == "yes":
            s[i] = "True"
        elif s[i] == "no":
            s[i] = "False"
        elif s[i] == "none":
            s[i] = "None"
        i += 1
    return s


def translate(s, module_name, package_name, parent_statements=[],
        extra_indent="", folder_path="", project_info=None,
        known_imports=None, translate_file_queue=None):
    if len(parent_statements) == 0 and DEBUG_ENABLE:
        print("tools/translator.py: debug: translating " +
            "module \"" + modname + "\" in folder: " + folder_path +
            (" (no package)" if package_name is None else
             " (package: " + str(package_name) + ")"))
    if known_imports is None:
        known_imports = {}
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    result = ""
    tokens = tokenize(s)
    statements = split_toplevel_statements(tokens)
    for statement in statements:
        assert("_remapped_os" not in statement)
        while is_whitespace_token(statement[-1]):
            statement = statement[:-1]
        indent = extra_indent
        if is_whitespace_token(statement[0]):
            indent += statement[0]
            statement = statement[1:]
            while is_whitespace_token(statement[0]):
                statement = statement[1:]
        if statement[0] == "var" or statement[0] == "const":
            statement_cpy = list(statement)
            statement = statement[1:]
            while is_whitespace_token(statement[0]):
                statement = statement[1:]
            i = 1
            while i < len(statement) and statement[i] != "=":
                if statement[i] == "protect":
                    statement[i] = ""  # Python doesn't have that.
                i += 1
            while (i < len(statement) and
                    is_whitespace_token(statement[i])):
                i += 1
            if i < len(statement) and statement[i] == "=":
                statement = (statement[:i + 1] + ["("] +
                    translate_expression_tokens(
                    statement[i + 1:], module_name, package_name,
                    parent_statements=(
                        parent_statements + [statement_cpy]),
                    known_imports=known_imports) + [")"])
                assert("no" not in statement)
            else:
                statement += ["=", "None"]
            if len(parent_statements) > 0 and \
                    "".join(parent_statements[0][:1]) == "type":
                type_name = parent_statements[0][2]
                get_type(type_name, module_name, package_name).\
                    init_code += "\n" + indent +\
                    ("\n" + indent).join((
                        "self." +
                        untokenize(statement) + "\n"
                    ).splitlines())
                continue
            result += indent + untokenize(statement) + "\n"
            # (we already did translate_expression_tokens above.)
            continue
        elif (statement[0] == "if" or statement[0] == "while" or
                statement[0] == "for"):
            statement_cpy = list(statement)
            j = 0
            while j < len(statement):
                if statement[j].strip(" \t\r\n") == "":
                    j += 1
                    continue
                assert(statement[j] in ("if", "while", "elseif",
                    "else", "for"))
                bracket_depth = 0
                i = j + 1
                while i < len(statement) and (
                        statement[i] != "{" or bracket_depth > 0):
                    if statement[i] in {"{", "(", "["}:
                        bracket_depth += 1
                    elif statement[i] in {"}", ")", "]"}:
                        bracket_depth -= 1
                    i += 1
                assert(i < len(statement) and statement[i] == "{")
                statement[i] = ":"
                begin_content_idx = i + 1
                condition = (
                    translate_expression_tokens(statement[j + 1:i],
                        module_name, package_name,
                        parent_statements=parent_statements,
                        known_imports=known_imports,
                        add_indent=extra_indent))
                assert("as_str" not in condition)
                assert(sublist_index(condition, [".", "len"]) < 0)
                bracket_depth = 0
                while statement[i] != "}" or bracket_depth > 0:
                    if statement[i] in {"{", "(", "["}:
                        bracket_depth += 1
                    elif statement[i] in {"}", ")", "]"}:
                        bracket_depth -= 1
                    i += 1
                assert(statement[i] == "}")
                content = statement[
                    begin_content_idx:i
                ]
                content_code = translate(
                    untokenize(content), module_name, package_name,
                    parent_statements=(
                        parent_statements + [statement_cpy]),
                    extra_indent=extra_indent,
                    folder_path=folder_path,
                    project_info=project_info,
                    known_imports=known_imports,
                    translate_file_queue=translate_file_queue
                )
                if statement[j] == "elseif":
                    statement[j] = "elif"
                if statement[j] != "for":
                    condition = ["("] + condition + [")"]
                else:
                    in_idx = -1
                    bracket_depth = 0
                    z = 0
                    while z < len(condition):
                        if condition[z] in {"{", "(", "["}:
                            bracket_depth += 1
                        elif condition[z] in {"}", ")", "]"}:
                            bracket_depth -= 1
                        if (condition[z] == "in" and
                                bracket_depth == 0):
                            in_idx = z
                            break
                        z += 1
                    assert(in_idx > 0)
                    condition = (["("] +
                        condition[:in_idx] + [")", " ", "in", " ", "("] +
                        condition[in_idx + 1:] + [")"])
                result += (indent + statement[j] + (
                    " " + untokenize(condition).strip(" ")
                    if statement[j] != "else" else "") +
                    ":\n" + content_code + (
                        "\n" if content_code.rstrip("\r\n") ==
                        content_code else ""))
                assert(statement[i] == "}")
                j = i + 1
            continue
        elif statement[0] == "import":
            assert(len(parent_statements) == 0)
            assert(len(statement) >= 2 and statement[1].strip() == "")
            i = 2
            while i + 2 < len(statement) and statement[i + 1] == ".":
                i += 2
            import_module = "".join([
                part.strip() for part in statement[1:i + 1]
                if part.strip() != ""
            ])
            import_package = project_info.package_name
            i += 1
            while i < len(statement) and statement[i].strip() == "":
                i += 1
            if i < len(statement) and statement[i] == "from":
                i += 1
                while i < len(statement) and statement[i].strip() == "":
                    i += 1
                import_package = statement[i]
                while i + 2 < len(statement) and statement[i + 1] == ".":
                    import_package += "." + statement[i + 2]
                    i += 2
            target_path = import_module.replace(".", "/") + ".h64"
            append_code = ""
            python_module = import_module
            if (import_package != None and
                    import_package !=
                    project_info.package_name):
                assert("." in import_package)
                python_module = "horse_modules." + (
                        import_package.replace(".", "_")
                    ) + "." + python_module
                if os.path.exists(os.path.join(
                        project_info.repo_folder,
                        "horse_modules/" + import_package + "/" +
                        "src/")) and (
                        "." in import_package):
                    target_path = ("horse_modules/" +
                        import_package
                    ) + "/src/" + target_path
                else:
                    target_path = ("horse_modules/" +
                        import_package
                    ) + "/" + target_path
                for module_part in import_module.split(".")[:-1]:
                    append_code += ("; (" + module_part +
                        " := dict() if \"" +
                        module_part + "\" not in locals and \"" +
                        module_part + "\" not in globals)")
                append_code += ("; " +
                    import_module + " = horse_modules." +
                    import_package.replace(".", "_") +
                    "." + import_module)
                target_path = os.path.normpath(
                    os.path.join(os.path.abspath(
                    project_info.repo_folder), target_path))
            else:
                target_path = os.path.normpath(
                    os.path.join(os.path.abspath(
                    project_info.code_folder), target_path))

            # Check if this module is only used for remapped uses:
            found_nonremapped_use = False
            found_remapped_use = False
            if DEBUG_ENABLE_REMAPPED_USES:
                print("tools/translator.py: debug: scanning \"" +
                    "import " + import_module +
                    (" from " + import_package
                    if import_package != None else "") + "\" for " +
                    "remapped uses...")
            import_module_elements = import_module.split(".")
            assert(len(import_module_elements) >= 1)
            i = 0
            while i < len(tokens):
                if (i > 1 and tokens[i - 1].strip(" \t\r\n") == "" and
                        (tokens[i - 2] == "import" or
                        tokens[i - 2] == "from")):
                    i += 1
                    continue
                match = True
                k = 0
                while k < len(import_module_elements):
                    if (k * 2 + i >= len(tokens) or
                            tokens[i + k * 2] !=
                            import_module_elements[k] or
                            (k + 1 < len(import_module_elements) and
                            (k * 2 + 1 + i >= len(tokens) or
                            tokens[i + k * 2 + 1] != "."))):
                        match = False
                        break
                    k += 1
                if not match:
                    i += 1
                    continue
                remapped_uses_key = import_module
                if import_package != None:
                    remapped_uses_key += "@" + import_package
                if remapped_uses_key not in remapped_uses:
                    if DEBUG_ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: found " +
                            "non-remapped use (no remaps for " +
                            "module " + str(remapped_uses_key) + "): " + str(
                            tokens[i:i + len(import_module_elements) + 10]))
                    found_nonremapped_use = True
                    break
                remapped_uses_list = list(
                    remapped_uses[remapped_uses_key].keys())
                matched_remap = False
                for remapped_use_entry in remapped_uses_list:
                    remapped_use_parts = (
                        remapped_use_entry.split("."))
                    if ("".join(tokens[i:
                            i + len(remapped_use_parts) * 2 - 1]) ==
                            remapped_use_entry):
                        matched_remap = True
                        break
                if not matched_remap:
                    found_nonremapped_use = True
                    if DEBUG_ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: found " +
                            "non-remapped use: " + str(
                            tokens[i:i + len(import_module_elements) + 10]))
                else:
                    found_remapped_use = True
                i += 1

            # Add import:
            known_imports[import_module] = {
                "package": import_package,
                "module": import_module,
                "python-module": python_module,
                "path": target_path,
            }

            # Skip import code if it only has remapped uses:
            if not found_nonremapped_use and found_remapped_use:
                if DEBUG_ENABLE_REMAPPED_USES:
                    print("tools/translator.py: debug: hiding " +
                        "import since all uses are remapped: " +
                        str(import_module) + ("" if
                        import_package is None else
                        "@" + import_package))
                known_imports[import_module]["python-module"] = (
                    None  # since it wasn't actually imported
                )
                continue

            # Add translated import code:
            result += "import " + python_module + append_code + "\n"
            translate_file_queue.append(
                (target_path,
                import_module, os.path.dirname(target_path),
                import_package)
            )
            for otherfile in os.listdir(os.path.dirname(target_path)):
                otherfilepath = os.path.normpath(os.path.join(
                    os.path.dirname(target_path), otherfile
                ))
                if (not otherfilepath.endswith(".h64") or
                        os.path.isdir(otherfilepath)):
                    continue
                otherfile_module = ".".join(
                    import_module.split(".")[:-1] +
                    [otherfile.rpartition(".h64")[0].strip()]
                )
                translate_file_queue.append(
                    (otherfilepath,
                    otherfile_module, os.path.dirname(target_path),
                    import_package)
                )
            continue
        elif statement[0] == "func":
            statement_cpy = list(statement)
            statement[0] = "def"
            bracket_depth = 0
            i = 1
            while statement[i] != "{" or bracket_depth > 0:
                if statement[i] in {"(", "[", "{"}:
                    bracket_depth += 1
                elif statement[i] in {")", "]", "}"}:
                    bracket_depth -= 1
                i += 1
            i += 1

            if statement[-1] != "}":
                print("tools/translator.py: error: " +
                    "got invalid func statement " +
                    "without closing bracket:", file=sys.stderr)
                print(untokenize(statement_cpy), file=sys.stderr)
                print("tools/translator.py: info: " +
                    "(statement repeated now as tokens list)",
                    file=sys.stderr)
                print(str(statement_cpy), file=sys.stderr)
                sys.stderr.flush()
            assert(statement[-1] == "}")
            contents = (
                statement[i:-1]
            )
            assert(statement[1].strip() == "")
            type_module = None
            type_name = None
            type_package = None
            type_python_module = None
            start_arguments_idx = 3
            name = statement[2]
            if statement[3] == ".":
                type_name = ""
                name = ""
                i2 = 2
                while i2 + 2 < len(statement) and statement[i2 + 1] == ".":
                    if len(type_name) > 0:
                        type_name += "."
                    type_name += statement[i2]
                    name = statement[i2 + 2]
                    i2 += 2
                start_arguments_idx = i2 + 1
                for import_mod_name in known_imports:
                    if type_name.startswith(import_mod_name + "."):
                        type_module = import_mod_name
                        type_name = type_name[len(type_module) + 1:]
                        type_package = known_imports\
                            [type_module]["package"]
                        type_python_module = known_imports[
                            type_module]["python-module"]
            while (start_arguments_idx < len(statement) and
                    statement[start_arguments_idx].
                        strip(" \t\r\n") == ""):
                start_arguments_idx += 1
            if type_module is None:
                type_module = module_name
                type_package = package_name
            argument_tokens = ["(", ")"]
            if statement[start_arguments_idx] == "(":
                bdepth = 1
                k = start_arguments_idx + 1
                while statement[k] != ")" or bdepth > 1:
                    if statement[k] == "(":
                        bdepth += 1
                    elif statement[k] == ")":
                        bdepth -= 1
                    k += 1
                assert(statement[k] == ")")
                argument_tokens = translate_expression_tokens(
                    statement[start_arguments_idx:k + 1],
                    module_name, package_name,
                    parent_statements=parent_statements,
                    known_imports=known_imports,
                    add_indent=extra_indent)
            assert("_remapped_os" not in contents)
            translated_contents = translate(
                untokenize(contents), module_name, package_name,
                parent_statements=(
                    parent_statements + [statement_cpy]),
                extra_indent=(extra_indent + ("    "
                    if type_name is not None else "")),
                folder_path=folder_path,
                project_info=project_info,
                known_imports=known_imports,
                translate_file_queue=translate_file_queue
            )
            (cleaned_argument_tokens,
                extra_init_code) = separate_func_keyword_arg_code(
                    argument_tokens, indent=(indent + "    " +
                    ("    " if type_name is not None else "")))
            if type_name is None:
                result += (indent + "def " + name +
                    untokenize(cleaned_argument_tokens) + ":\n")
                result += (extra_init_code + "\n" +
                    translated_contents + "\n")
            else:
                regtype = get_type(type_name, type_module, type_package)
                regtype.funcs[name] = {
                    "arguments": cleaned_argument_tokens,
                    "name": name,
                    "code": (extra_init_code + "\n" +
                    "\n".join(translated_contents.splitlines()) + "\n")
                }
            continue
        elif statement[0] == "type":
            statement_cpy = list(statement)
            i = 1
            while statement[i] != "{":
                i += 1
            i += 1
            assert(statement[-1] == "}")
            contents = (
                statement[i:-1]
            )
            register_type(statement[2], module_name, package_name)
            translated_contents = translate(
                untokenize(contents), module_name, package_name,
                parent_statements=(
                    parent_statements + [statement_cpy]),
                extra_indent=(extra_indent + "    "),
                folder_path=folder_path,
                project_info=project_info,
                known_imports=known_imports,
                translate_file_queue=translate_file_queue
            )
            continue
        result += indent + untokenize(translate_expression_tokens(
            statement, module_name, package_name,
            parent_statements=parent_statements,
            known_imports=known_imports,
            add_indent=extra_indent)) + "\n"
    return result


def separate_func_keyword_arg_code(
        func_argument_tokens, indent=""
        ):
    changed = True
    while changed:
        changed = False
        while (len(func_argument_tokens) > 0 and
                func_argument_tokens[0].strip(" \r\n\t") == ""):
            changed = True
            func_argument_tokens = func_argument_tokens[1:]
        while (len(func_argument_tokens) > 0 and
                func_argument_tokens[-1].strip(" \r\n\t") == ""):
            changed = True
            func_argument_tokens = func_argument_tokens[:-1]
        if (len(func_argument_tokens) > 1 and
                func_argument_tokens[0] == "(" and
                func_argument_tokens[-1] == ")"):
            func_argument_tokens = (
                func_argument_tokens[1:-1]
            )
            changed = True
    args_separated = []
    i = 0
    arg_start = 0
    bracket_depth = 0
    while i < len(func_argument_tokens):
        t = func_argument_tokens[i]
        if t in {"{", "[", "("}:
            bracket_depth += 1
        elif t in {"}", "]", ")"}:
            bracket_depth -= 1
        if t == "," and bracket_depth == 0:
            args_separated.append(
                func_argument_tokens[arg_start:i])
            arg_start = i + 1
            i += 1
            continue
        i += 1
    if arg_start < len(func_argument_tokens):
        args_separated.append(
            func_argument_tokens[arg_start:i])
    kw_arg_init_code = ""
    new_args_separated_flat = []
    for func_arg in args_separated:
        eq_index = -1
        try:
            eq_index = func_arg.index("=")
        except ValueError:
            pass
        if (eq_index > 0 and
                len(set(func_arg[:eq_index]).intersection(
                    {"(", "[", "{"})) > 0):
            eq_index = -1
        if eq_index > 0:
            if len(new_args_separated_flat) > 0:
                new_args_separated_flat.append(",")
            new_args_separated_flat += (
                func_arg[:eq_index+1] +
                ["(", "_translator_kw_arg_default_value",
                ")"])
            k = 0
            while k < len(func_arg):
                if func_arg[k].strip(" \t\r\n") == "":
                    k += 1
                    continue
                # FIXME: skip argument attribute keywords here
                break
            assert(k < eq_index)
            kw_arg_init_code += ("\n" + indent +
                "if " + func_arg[k] +
                " == _translator_kw_arg_default_value:\n" +
                indent + "    " + func_arg[k] + " = (" +
                untokenize(func_arg[eq_index+1:]) + ")")
        else:
            if len(new_args_separated_flat) > 0:
                new_args_separated_flat.append(",")
            new_args_separated_flat += func_arg
    result = (
        ["("] + (new_args_separated_flat) + [")"],
        kw_arg_init_code
    )
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    target_file = None
    target_file_args = []
    keep_files = False
    overridden_package_name = None
    i = 0
    while i < len(args):
        if args[i] == "--":
            if target_file is None and i + 1 < len(args):
                target_file = args[i + 1]
                target_file_args = args[i + 2:]
            else:
                target_file_args = args[i+1:]
            break
        elif args[i].startswith("-"):
            if args[i] == "--help":
                print("Usage: translator.py [(optional) options...] "
                      "path-to/h64-file.h64")
                print("Options:")
                print("    --help        Show this help text")
                print("    --keep-files  Keep translated files and ")
                print("                  print out path to them.")
                print("    --version     Print out program version")
                sys.exit(0)
            elif (args[i] == "--version" or args[i] == "-v" or
                    args[i] == "-V"):
                print("tools/translator.py version " + VERSION)
                sys.exit(0)
            elif args[i] == "--override-package-name":
                if i + 1 >= len(args):
                    print("tools/translator.py: error: " +
                        "missing argument for --override-package-name")
                    sys.exit(1)
                if ("." not in args[i + 1] or
                        args[i + 1].startswith("-") or
                        args[i + 1].endswith(".h64")):
                    print("tools/translator.py: error: " +
                        "invalid name specified for " +
                        "--override-package-name")
                    sys.exit(1)
                overridden_package_name = args[i + 1]
                i += 2
                continue
            elif args[i] == "--debug":
                DEBUG_ENABLE = True
                DEBUG_ENABLE_TYPES = True
                DEBUG_ENABLE_CONTENTS = True
                DEBUG_ENABLE_REMAPPED_USES = True
            elif args[i] == "--keep-files":
                keep_files = True
            else:
                print("tools/translator.py: warning: unknown " +
                    "option: " + args[i], file=sys.stderr)
        elif target_file is None:
            target_file = args[i]
            target_file_args = args[i + 1:]
            break
        i += 1
    if target_file is None:
        raise RuntimeError("please provide target file argument")
    modname = (os.path.basename(target_file).
        rpartition(".h64")[0].strip())
    project_info = TranslatedProjectInfo()
    project_info.package_name = overridden_package_name
    modfolder = os.path.abspath(os.path.dirname(target_file))
    if (not os.path.exists(target_file) or
            os.path.isdir(target_file) or
            not target_file.endswith(".h64") or
            len(modname) == 0 or "-" in modname or
            "." in modname):
        raise IOError("missing target file, " +
            "or target file not a .h64 file with proper " +
            "module name: " + str(target_file))
    project_info.repo_folder = modfolder
    while True:
        repo_folder_files = os.listdir(project_info.repo_folder)
        if ("horse_modules" in repo_folder_files or
                ".git" in repo_folder_files):
            break
        if ("horp.ini" in repo_folder_files and
                not os.path.isdir(os.path.join(
                project_info.repo_folder,
                "horp.ini"))):
            contents = ""
            with open(os.path.join(project_info.repo_folder,
                    "horp.ini"), "r", encoding='utf-8') as f:
                contents = f.read()
            pkg_name = horp_ini_string_get_package_name(contents)
            if pkg_name != None:
                if project_info.package_name is None:
                    project_info.package_name = pkg_name
                break
        project_info.repo_folder = os.path.normpath(
            os.path.abspath(project_info.repo_folder))
        if "windows" in platform.system().lower():
            project_info.repo_folder = (
                project_info.repo_folder.replace("\\", "/"))
        while "//" in project_info.repo_folder:
            project_info.repo_folder = (
                project_info.repo_folder.replace("//", "/"))
        if project_info.repo_folder.endswith("/") and (
                "windows" not in platform.system().lower() or
                len(project_info.repo_folder) > 3) and \
                project_info.repo_folder != "/":
            project_info.repo_folder = project_info.repo_folder[:-1]
        if (("windows" in platform.system().lower() and
                len(project_info.repo_folder) == 3) or
                "windows" not in platform.system().lower() and
                project_info.repo_folder == "/"):
            raise RuntimeError("failed to detect repository folder")
        project_info.repo_folder = os.path.normpath(
            os.path.abspath(
            os.path.join(project_info.repo_folder, "..")))
    if DEBUG_ENABLE:
        print("tools/translator.py: debug: " +
            "detected repository folder: " +
            project_info.repo_folder)
    project_info.code_relpath = ""
    if os.path.exists(os.path.join(project_info.repo_folder, "src")):
        project_info.code_relpath = "src/"
    project_info.code_folder = os.path.join(
        project_info.repo_folder, project_info.code_relpath)
    if (project_info.package_name is None and
            os.path.exists(os.path.join(
            project_info.repo_folder, "horp.ini"))):
        with open(os.path.join(project_info.repo_folder,
                "horp.ini"), "r", encoding='utf-8') as f:
            contents = f.read()
            pkg_name = horp_ini_string_get_package_name(contents)
            if pkg_name != None:
                project_info.package_name = pkg_name
            else:
                print("tools/translator.py: warning: " +
                    "failed to get package name from horp.ini: " +
                    str(os.path.join(repo_folder, "horp.ini")))
    if DEBUG_ENABLE:
        print("tools/translator.py: debug: " +
            "detected package name: " +
            str(project_info.package_name))
    translate_file_queue = [
        (os.path.normpath(os.path.abspath(target_file)),
        modname, modfolder, project_info.package_name)]
    mainfilepath = translate_file_queue[0][0]
    while len(translate_file_queue) > 0:
        (target_file, modname, modfolder,
         package_name) = translate_file_queue[0]
        translate_file_queue = translate_file_queue[1:]
        if target_file in translated_files:
            continue
        for otherfile in os.listdir(modfolder):
            otherfilepath = os.path.normpath(
                os.path.abspath(os.path.join(modfolder, otherfile)))
            if (os.path.isdir(otherfilepath) or
                    not otherfilepath.endswith(".h64") or
                    otherfilepath in translated_files):
                continue
            new_modname = (modname.rpartition(".")[0] + "."
                if "." in modname else "")
            new_modname += (os.path.basename(otherfile).
                rpartition(".h64")[0])
            translate_file_queue.append((otherfilepath,
                new_modname, modfolder, package_name))
        contents = None
        with open(target_file, "r", encoding="utf-8") as f:
            contents = f.read()
        contents_result = (
            translate(contents, modname, package_name,
                folder_path=modfolder,
                project_info=project_info,
                translate_file_queue=translate_file_queue))
        translated_files[target_file] = {
            "module-name": modname,
            "package-name": package_name,
            "module-folder": modfolder,
            "path": target_file,
            "disk-fake-folder": os.path.dirname(
                ("" if package_name is None else
                "horse_modules/" +
                package_name.replace(".", "_") + "/") +
                modname.replace(".", "/")),
            "output": contents_result
        }
    for translated_file in translated_files:
        contents_result = (
            "import os as _remapped_os;import sys as _remapped_sys;" +
            "_translator_kw_arg_default_value = object();" +
            "_translated_program_main_script_file = " +
            as_escaped_code_string(mainfilepath) + ";" +
            "import _translator_runtime_helpers;\n"
            ) + translated_files[translated_file]["output"]
        for regtype in known_types.values():
            if (regtype.module != translated_files
                    [translated_file]["module-name"] or
                    regtype.pkgname != translated_files
                    [translated_file]["package-name"]):
                continue
            contents_result += "\n"
            contents_result += "class " + regtype.name + ":\n"
            if "init" in regtype.funcs:
                assert(regtype.funcs["init"]["arguments"][0] == "(")
                regtype.funcs["init"]["arguments"] = (
                    regtype.funcs["init"]["arguments"][:1] +
                    ["self", ",", " "] +
                    regtype.funcs["init"]["arguments"][1:]
                )
                contents_result += ("    def __init__" +
                    untokenize(regtype.funcs["init"]["arguments"]) + ":\n")
                if regtype.init_code != None:
                    contents_result += regtype.init_code + "\n"
                contents_result += regtype.funcs["init"]["code"] + "\n"
            elif regtype.init_code != None:
                contents_result += ("    def __init__(self):\n")
                contents_result += regtype.init_code + "\n"
            for funcname in regtype.funcs:
                if funcname == "init":
                    continue
                assert(regtype.funcs[funcname]["arguments"][0] == "(")
                regtype.funcs[funcname]["arguments"] = (
                    regtype.funcs[funcname]["arguments"][:1] +
                    ["self", ",", " "] +
                    regtype.funcs[funcname]["arguments"][1:]
                )
                contents_result += ("    def " + funcname +
                    untokenize(regtype.funcs[funcname]["arguments"]) + ":\n")
                contents_result += regtype.funcs[funcname]["code"] + "\n"

        if (translated_files[translated_file]["path"] ==
                mainfilepath):
            contents_result += "\nif __name__ == '__main__':\n    main()\n"

        if DEBUG_ENABLE and DEBUG_ENABLE_CONTENTS:
            print("tools/translator.py: debug: have output of " +
                str(len(contents_result.splitlines())) + " lines for: " +
                translated_file)
            print(contents_result)
        translated_files[translated_file]["output"] = contents_result
        #print(tokenize(b" \n\r test".decode("utf-8")))
    output_folder = tempfile.mkdtemp(prefix="h64-tools-translator-")
    assert(os.path.isabs(output_folder) and "h64-tools" in output_folder)
    returncode = 0
    try:
        if keep_files:
            print("tools/translator.py: info: writing " +
                "translated files to (will be kept): " +
                output_folder)
        elif DEBUG_ENABLE:
            print("tools/translator.py: debug: writing temporary " +
                "result to (will be deleted): " +
                output_folder)
        run_py_path = None
        for translated_file in translated_files:
            name = os.path.basename(
                translated_files[translated_file]["path"]
            ).rpartition(".h64")[0].strip()
            contents = translated_files[translated_file]["output"]
            subfolder = translated_files[translated_file]["disk-fake-folder"]
            assert(not os.path.isabs(subfolder) and ".." not in subfolder)
            subfolder_abs = os.path.join(output_folder, subfolder)
            if not os.path.exists(subfolder_abs):
                os.makedirs(subfolder_abs)
            if not os.path.exists(os.path.join(subfolder_abs,
                    "_translator_runtime_helpers.py")):
                t = None
                with open(os.path.join(translator_py_script_dir,
                        "translator_runtime_helpers.py"), "r",
                        encoding="utf-8") as f:
                    t = f.read()
                    t = t.replace("__translator_py_path__",
                        as_escaped_code_string(translator_py_script_path))
                with open(os.path.join(subfolder_abs,
                        "_translator_runtime_helpers.py"), "w",
                        encoding="utf-8") as f:
                    f.write(t)
            with open(os.path.join(output_folder, subfolder,
                    name + ".py"), "w", encoding="utf-8") as f:
                f.write(contents)
            if translated_files[translated_file]["path"] == mainfilepath:
                run_py_path = os.path.join(output_folder, subfolder,
                    name + ".py")
        launch_cmd = [
            sys.executable, run_py_path
        ] + target_file_args
        if DEBUG_ENABLE:
            print("tools/translator.py: debug: launching program: " +
                str(launch_cmd))
        result = subprocess.run(launch_cmd)
        returncode = result.returncode
    finally:
        if not keep_files:
            shutil.rmtree(output_folder)
        else:
            print("Translated files left available in: " + output_folder)
    sys.exit(returncode)


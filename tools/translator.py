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

# !!!!!!!!! HEED THIS WARNING !!!!!!!!!
HACKY_WARNING=(
    "THIS TOOL (tools/translator.py) ONLY SUPPORTS A SUBSET OF " +
    "HORSE64 AND WILL OTHERWISE CRASH AND BURN. IT WON'T CATCH MANY " +
    "CODE ERRORS AND JUST EXPLODE OR RUN IT WRONG. " +
    "If you can, really use the official compiler horsec.")

VERSION="unknown"

import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap
import traceback

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)

import translator_debugvars
from translator_debugvars import DEBUGV

from translator_horphelpers import (
    horp_ini_string_get_package_name,
    horp_ini_string_get_package_version,
    horp_ini_string_get_package_license_files
)

from translator_transformhelpers import (
    transform_h64_misc_inline_to_python,
    get_first_nonempty_line_indent
)

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
    is_number_token, extract_all_imports
)

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)
translated_files = {}

# Set version:
if os.path.exists(os.path.join(translator_py_script_dir,
        "..", "horp.ini")):
    with open(os.path.join(translator_py_script_dir,
            "..", "horp.ini")) as f:
        _get_version = horp_ini_string_get_package_version(
            f.read()
        )
        if _get_version:
            VERSION = _get_version


def _splitpath(p):
    if os.path.sep == "\\" or platform.system().lower == "windows":
        p = p.replace("\\", "/")
    while p.endswith("/") and len(p) > 1:
        p = p[:-1]
    return p.split("/")


DEBUGV.ENABLE = False
DEBUGV.ENABLE_CONTENTS = False
DEBUGV.ENABLE_QUEUE = False
DEBUGV.ENABLE_TYPES = False
DEBUGV.ENABLE_REMAPPED_USES = False
DEBUGV.ENABLE_FILE_PATHS = False

remapped_uses = {
    "compiler@core.horse64.org": {
        "compiler.run_file":
            "_translator_runtime_helpers._compiler_run_file",
    },
    "files@core.horse64.org": {
        "files.get_working_dir" : "_remapped_os.getcwd",
    },
    "io@core.horse64.org": {
        "io.open":
            "(lambda path, mode: _translator_runtime_helpers." +
            "_FileObjFromDisk(path, mode))",
    },
    "math@core.horse64.org": {
        "math.min": "_translator_runtime_helpers._math_min",
        "math.max": "_translator_runtime_helpers._math_max",
        "math.floor": "_translator_runtime_helpers._math_floor",
        "math.ceil": "_translator_runtime_helpers.math_ceil",
        "math.round": "_translator_runtime_helpers._math_round",
    },
    "net@core.horse64.org": {
        "net.lookup_name":
            "_translator_runtime_helpers._net_lookup_name",
        "net.NetworkIOError":
            "_translator_runtime_helpers._NetworkIOError",
    },
    "net.fetch@core.horse64.org": {
        "net.fetch.get":
            "_translator_runtime_helpers._net_fetch_get",
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
        "system.program_compiled_with":
            "(lambda: \"horse64-translator-py v\" + " +
            as_escaped_code_string(VERSION) + ")",
        "system.program_licenses_as_list":
            "(lambda: _translator_runtime_helpers._return_licenses())",
        "system.program_version":
            "(lambda: _translated_program_version)",
        "system.self_exec_path" :
            "(lambda: _translated_program_main_script_file." +
            "rpartition(\".h64\")[0])",
    },
    "text@core.horse64.org": {
        "text.full_glyphs_in_sub":
            "(lambda a, b, c: _translator_runtime_helpers."
            "_container_sub(a, b, c))",
        "text.code":
            "(lambda x: int(ord(x)))",
    },
    "uri@core.horse64.org": {
        "uri.normalize":
            "(lambda v: _translator_runtime_helpers." +
            "_uri_normalize(v))",
        "uri.from_disk_path":
            "(lambda v: _translator_runtime_helpers." +
            "_file_uri_from_path(v))"
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
    if DEBUGV.ENABLE and DEBUGV.ENABLE_TYPES:
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
        self.package_version = None
        self.licenses = []

    def get_package_subfolder(self,
            package_name,
            for_output=True):
        if not for_output and (package_name is None or
                package_name == self.package_name):
            return ""
        if package_name == None:
            return "horse_modules/main/"
        assert("/" not in package_name and
                "\\" not in package_name and
                len(package_name) > 0 and
                not package_name.startswith("."))
        if for_output:
            return "horse_modules/" + str(package_name).\
                replace(".", "_") + "/"
        folder = "horse_modules/" + str(package_name) + "/"
        if (os.path.exists(os.path.join(
                self.repo_folder, folder, "src")) and
                os.path.isdir(os.path.join(
                self.repo_folder, folder, "src"))):
            folder = folder + "src/"
        return folder


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


def find_matching_remap_module(s, i, processed_imports={}):
    # See if any external, imported use needs a remap:
    match = False
    match_package = None
    match_import_module = None
    match_item = None
    match_tokens = -1
    for known_import in processed_imports:
        import_module_elements = (
            processed_imports[known_import]
                ["module"].split(".")
        )
        maybe_match = True

        # See if this matches our module:
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
        if not maybe_match:
            continue
        #print("MAYBE MATCH: " + str(import_module_elements))

        # Rule out, however, that this matches a module with
        # more components (so that net.fetch trumps net, for
        # example:
        for known_other_import in processed_imports:
            other_module_elements = (
                processed_imports[known_other_import]
                    ["module"].split(".")
            )
            if (len(other_module_elements) <=
                    len(import_module_elements)):
                # Uninteresting, doesn't have more components.
                continue
            #print("CHECKING AGAINST OTHER: " +str(other_module_elements))
            maybe_other_match = True
            k2 = 0
            while k2 < len(other_module_elements):
                if (k2 * 2 + i >= len(s) or
                        s[i + k2 * 2] !=
                        other_module_elements[k2] or
                        (k2 + 1 < len(other_module_elements) and
                        (k2 * 2 + 1 + i >= len(s) or
                        s[i + k2 * 2 + 1] != "."))):
                    maybe_other_match = False
                    break
                k2 += 1
            if maybe_other_match:
                # Trumped by longer remap module.
                maybe_match = False
                break
        if not maybe_match:
            continue
        maybe_match_tokens = -1
        maybe_match_item = None
        if (k * 2 + i < len(s) and
                is_identifier(s[k * 2 + i])):
            maybe_match_item = s[k * 2 + i]
            maybe_match_tokens = k * 2 + 1
        #print((s[i], k, maybe_match_item, maybe_match,
        #    processed_imports[known_import]
        #            ["module"],
        #    import_module_elements,
        #    maybe_match_tokens))
        if (maybe_match and (not match or
                len(import_module_elements) >
                len(match_import_module.split("."))) and
                maybe_match_item != None):
            match = True
            match_import_module = (
                processed_imports[known_import]
                    ["module"]
            )
            match_package = (
                processed_imports[known_import]
                    ["package"]
            )
            match_tokens = maybe_match_tokens
            match_item = maybe_match_item
    if match == True:
        return (match_import_module, match_package,
            match_item, match_tokens)
    else:
        return (None, None, None, None)


def translate_expression_tokens(s, module_name, package_name,
        parent_statements=[], processed_imports=None, project_info=None,
        add_indent="", repo_package_name=None, is_assign_stmt=False,
        assign_token_index=-1):
    s = list(s)
    assert("_remapped_os" not in s)
    assert("_remapped_sys" not in s)
    assert(sublist_index(s, ["sys", ".", "argv"]) < 0)

    # Fix indent first:
    i = 0
    while i < len(s):
        t = s[i]
        if t.strip("\t\r\n ") == "" and (
                t.startswith("\r\n") or
                t.startswith("\n")):
            t += add_indent
            s[i] = t
        elif t.strip("\t\r\n ") == "" and (
                t.endswith("\r\n") or
                t.endswith("\n")):
            t = add_indent + t
            s[i] = t
        i += 1
    # Fix assignments to square bracket accessed expression:
    if (is_assign_stmt and
            prevnonblank(s, assign_token_index) == "]"):
        i = prevnonblankidx(s, assign_token_index)
        # Find opening '[':
        bracket_depth = 0
        k = i - 1
        while (k >= 0 and (
                bracket_depth > 0 or
                s[k] != "[")):
            if s[k] in {")", "]", "}"}:
                bracket_depth += 1
            elif s[k] in {"(", "[", "{"}:
                bracket_depth -= 1
            k -= 1
        assert(k >= 0 and s[k] == "[")
        start_whitespace_len = 0
        while (start_whitespace_len < len(s) and
                is_whitespace_token(s[start_whitespace_len])):
            start_whitespace_len += 1
        end_whitepace_len = 0
        while (end_whitepace_len < len(s) and
                is_whitespace_token(
                s[len(s)-(end_whitepace_len + 1)])):
            end_whitepace_len -= 1
        orig_s = list(s)
        s = (["_translator_runtime_helpers", ".",
            "_container_squarebracketassign", "("] +
            s[start_whitespace_len:k] +
            [","] + s[k + 1:i] + [","] +
            tokenize(as_escaped_code_string(s[assign_token_index])) +
            [","] +
            s[assign_token_index+1:len(s) - end_whitepace_len] +
            [")"])
        #print("CHANGED TO ASSIGN: " + str(s))
        #print("ORIG: " + str(orig_s))
    # Translate typename()/"throw"/"has_attr"/...:
    previous_token = None
    i = 0
    while i < len(s):
        if (s[i] == "typename" and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "h64_type"] + s[i + 1:]
        elif s[i] == "ValueError" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_ValueError"] + s[i + 1:]
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
                "%", "|", "^", "&", "~", "."} or
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
                s = (s[:i + 1] + ["+", "\\"] +
                    [s[i + 1].lstrip(" \t")] + s[i + 2:])
        i += 1
    # Translate XYZ.as_str()/XYZ.len to str(XYZ)/len(XYZ),
    # important (!!!) this needs to be BEFORE remapping functions.
    s = transform_h64_misc_inline_to_python(s)
    # Translate remapped use to the proper remapped thing:
    i = 0
    while i < len(s):
        if (i > 1 and s[i - 1].strip(" \t\r\n") == "" and
                s[i - 2] in {"import", "func", ".", "var",
                "const"}):
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
        if len(processed_imports) == 0:
            i += 1
            continue
        #print("s[i] " + str(s[i]))

        # See if we are INSIDE a remapped module:
        for remap_module_key in remapped_uses:
            if (package_name == None or module_name == None or
                    module_name + "@" + package_name !=
                    remap_module_key):
                continue
            did_remap = False
            for remapped_use in remapped_uses[remap_module_key]:
                if (remapped_use == module_name + "." +
                        s[i]):
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: remapping " +
                            "use to the overridden expression: " +
                            module_name + "." + s[i] + " in " +
                            remap_module_key)
                    insert_tokens = tokenize(remapped_uses
                        [remap_module_key][remapped_use])
                    s = s[:i] + insert_tokens + s[i + 1:]
                    i += len(insert_tokens)
                    did_remap = True
                    break
            if did_remap:
                i += 1
                continue

        # See if any external, imported use needs a remap:
        (match_import_module, match_package,
         match_item, match_tokens) = find_matching_remap_module(
            s, i, processed_imports=processed_imports)
        if match_import_module is None:
            i += 1
            continue
        remap_module_key = match_import_module + (
            "" if match_package is None else
            "@" + match_package)
        if remap_module_key in remapped_uses:
            remap_original_use = (
                match_import_module + "." + match_item
            )
            if DEBUGV.ENABLE_REMAPPED_USES:
                print("tools/translator.py: debug: checking if " +
                    "use needs translation to remap: " +
                    remap_original_use + " in " + remap_module_key)
            for remapped_use in remapped_uses[remap_module_key]:
                if remapped_use == remap_original_use:
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: "
                            "remapping use of "
                            "the overridden expression: " +
                            remap_original_use + " in " +
                            remap_module_key)
                    insert_tokens = tokenize(remapped_uses
                        [remap_module_key][remapped_use])
                    s = s[:i] + insert_tokens + s[i + match_tokens:]
                    i += len(insert_tokens)
                    break
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


def queue_file_if_not_queued(
        translate_file_queue, entry,
        reason=None
        ):
    for queue_item in translate_file_queue:
        if (os.path.normpath(queue_item[0]) ==
                os.path.normpath(entry[0])):
            return
    if DEBUGV.ENABLE and DEBUGV.ENABLE_QUEUE:
        print("tools/translator.py: debug: queueing item: " +
            str(entry) + (
            " due to reason: " + str(reason) if
            reason != None and len(reason) > 0 else
            " with reason unknown"))
        traceback.print_stack()
    entry = tuple(list(entry) + [reason])
    translate_file_queue.append(entry)
    if "compiler/main.h64" in entry[0]:
        assert(entry[2] == "compiler.main")
    if "limits" in entry[0]:
        assert(entry[2] == "compiler.limits")


def translate(s, module_name, package_name, parent_statements=[],
        extra_indent="", folder_path="", project_info=None,
        processed_imports=None, translate_file_queue=None,
        orig_h64_imports=None):
    if orig_h64_imports == None:
        assert(parent_statements is None or
            len(parent_statements) == 0)
        assert(processed_imports is None or
            len(processed_imports) == 0)
        assert(type(s) == list)
        orig_h64_imports = extract_all_imports(s)
    if (len(parent_statements) == 0 and DEBUGV.ENABLE and
            DEBUGV.ENABLE_FILE_PATHS):
        print("tools/translator.py: debug: translating " +
            "module \"" + module_name + "\" in folder: " +
            folder_path +
            (" (no package)" if package_name is None else
             " (package: " + str(package_name) + ")"))
    if processed_imports is None:
        processed_imports = {}
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    result = ""
    if type(s) != list or (len(s) > 0 and type(s[0]) != str):
        assert(type(s) == str)
        tokens = tokenize(s)
    else:
        tokens = s
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
                    project_info=project_info,
                    parent_statements=(
                        parent_statements + [statement_cpy]),
                    processed_imports=processed_imports) + [")"]
                    )
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
        elif statement[0] == "do":
            statement_cpy = list(statement)
            j = 1
            while (j < len(statement) and
                    statement[j].strip(" \t\r\n") == ""):
                j += 1
            assert(statement[j] == "{")
            do_block_content_first = j + 1
            bracket_depth = 0
            j += 1
            while (j < len(statement) and
                    (statement[j] != "}" or
                    bracket_depth > 0)):
                if statement[j] in {"(", "[", "{"}:
                    bracket_depth += 1
                elif statement[j] in {")", "]", "}"}:
                    bracket_depth -= 1
                j += 1
            do_block_content_last = j - 1
            assert(statement[j] == "}")
            j += 1  # Go past '}'
            while (j < len(statement) and
                    statement[j].strip(" \t\r\n") == ""):
                j += 1
            rescue_block_content_first = -1
            rescue_block_content_last = -1
            rescue_error_label_name = None
            rescue_error_types_first = -1
            rescue_error_types_last = -1
            finally_block_content_first = -1
            finally_block_content_last = -1
            if (j < len(statement) and
                    statement[j] == "rescue"):
                j += 1  # Past 'rescue' keyword.
                while (j < len(statement) and
                         statement[j].strip(" \t\r\n") == ""):
                    j += 1
                assert(statement[j] != "{")
                rescue_error_types_first = j
                bracket_depth = 0
                while (j < len(statement) and
                        ((statement[j] != "{" and
                        statement[j] != "as") or
                        bracket_depth > 0)):
                    if statement[j] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif statement[j] in {")", "]", "}"}:
                        bracket_depth -= 1
                    j += 1
                rescue_error_types_last = j - 1
                while (rescue_error_types_last >
                        rescue_error_types_first and
                        statement[rescue_error_types_last].
                        strip(" \r\n\t") == ""):
                    rescue_error_types_last -= 1
                assert(statement[j] == "{" or
                    statement[j] == "as")
                if statement[j] == "as":
                    j += 1
                    while (j < len(statement) and
                            statement[j].strip(" \t\r\n") == ""):
                        j += 1
                    assert(is_identifier(statement[j]))
                    rescue_error_label_name = statement[j]
                    j += 1
                    while (j < len(statement) and
                            statement[j].strip(" \t\r\n") == ""):
                        j += 1
                assert(statement[j] == "{")
                j += 1  # Go past the opening '{'
                rescue_block_content_first = j
                bracket_depth = 0
                while (j < len(statement) and
                        (statement[j] != "}" or
                        bracket_depth > 0)):
                    if statement[j] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif statement[j] in {")", "]", "}"}:
                        bracket_depth -= 1
                    j += 1
                rescue_block_content_last = j - 1
                assert(statement[j] == "}")
                j += 1
                while (j < len(statement) and
                         statement[j].strip(" \t\r\n") == ""):
                    j += 1
            if (j < len(statement) and
                    statement[j] == "finally"):
                j += 1  # Past 'finally' keyword.
                while (j < len(statement) and
                         statement[j].strip(" \t\r\n") == ""):
                    j += 1
                assert(statement[j] == "{")
                j += 1
                finally_block_content_first = j
                bracket_depth = 0
                while (j < len(statement) and
                        (statement[j] != "}" or
                        bracket_depth > 0)):
                    if statement[j] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif statement[j] in {")", "]", "}"}:
                        bracket_depth -= 1
                    j += 1
                finally_block_content_last = j - 1
                assert(statement[j] == "}")
                j += 1
            while (j < len(statement) and
                     statement[j].strip(" \t\r\n") == ""):
                j += 1
            assert(j >= len(statement))  # Require no trailing data.
            rescued_errors_expr = None
            rescue_block_code = None
            do_block_code = translate(
                    untokenize(statement[
                        do_block_content_first:
                        do_block_content_last+1
                    ]), module_name, package_name,
                    parent_statements=(
                        parent_statements + [statement_cpy]),
                    extra_indent=extra_indent,
                    folder_path=folder_path,
                    project_info=project_info,
                    processed_imports=processed_imports,
                    translate_file_queue=translate_file_queue,
                    orig_h64_imports=orig_h64_imports
                )
            if rescue_block_content_first >= 0:
                rescue_block_code = translate(
                    untokenize(statement[
                        rescue_block_content_first:
                        rescue_block_content_last+1
                    ]), module_name, package_name,
                    parent_statements=(
                        parent_statements + [statement_cpy]),
                    extra_indent=extra_indent,
                    folder_path=folder_path,
                    project_info=project_info,
                    processed_imports=processed_imports,
                    translate_file_queue=translate_file_queue,
                    orig_h64_imports=orig_h64_imports
                )
                rescued_errors_tokens = statement[
                    rescue_error_types_first:
                    rescue_error_types_last+1]
                while (len(rescued_errors_tokens) > 1 and
                        rescued_errors_tokens[0].strip(" \r\n\t") == ""):
                    rescued_errors_tokens = (
                        rescued_errors_tokens[1:])
                while (len(rescued_errors_tokens) > 1 and
                        rescued_errors_tokens[-1].strip(" \r\n\t") == ""):
                    rescued_errors_tokens = (
                        rescued_errors_tokens[:-1])
                assert(len(rescued_errors_tokens) > 0)
                # Ensure rescue a, b is translated to except (a, b):
                if rescued_errors_tokens[0] != "(":
                    rescued_errors_tokens = (["("] +
                        rescued_errors_tokens + [")"])
                rescued_errors_expr = translate_expression_tokens(
                    rescued_errors_tokens,
                    module_name, package_name,
                    project_info=project_info,
                    parent_statements=parent_statements,
                    processed_imports=processed_imports,
                    add_indent=extra_indent)
            finally_block_code = None
            if finally_block_content_first >= 0:
                finally_block_code = translate(
                    untokenize(statement[
                        finally_block_content_first:
                        finally_block_content_last+1
                    ]), module_name, package_name,
                    parent_statements=(
                        parent_statements + [statement_cpy]),
                    extra_indent=extra_indent,
                    folder_path=folder_path,
                    project_info=project_info,
                    processed_imports=processed_imports,
                    translate_file_queue=translate_file_queue,
                    orig_h64_imports=orig_h64_imports
                )
            result += (indent + "try:\n")
            result += do_block_code + "\n"
            result += (indent + "    pass\n")
            if (rescue_block_code is None
                    and finally_block_code is None):
                result += (indent + "finally:\n")
                result += (indent + "    pass\n")
            else:
                if rescue_block_code != None:
                    result += (indent + "except " +
                        untokenize(rescued_errors_expr))
                    if rescue_error_label_name != None:
                        result += (" as " +
                            rescue_error_label_name)
                    result += ":\n"
                    result += rescue_block_code + "\n"
                    result += (indent + "    pass\n")
                if finally_block_code != None:
                    result += (indent + "finally:\n")
                    result += finally_block_code + "\n"
                    result += (indent + "    pass\n")
            continue
        elif statement[0] == "with":
            statement_cpy = list(statement)
            bracket_depth = 0
            assign_obj_first = 1
            j = 1  # Past 'with' keyword.
            while (j < len(statement) and (
                    statement[j] != "as" or
                    bracket_depth > 0)):
                if statement[j] in {"(", "[", "{"}:
                    bracket_depth += 1
                elif statement[j] in {")", "]", "}"}:
                    bracket_depth -= 1
                j += 1
            assign_obj_last = j - 1
            assert(statement[j] == "as")
            j += 1  # Past 'as' keyword.
            while (j < len(statement) and
                     statement[j].strip(" \t\r\n") == ""):
                j += 1
            assert(j < len(statement) and
                is_identifier(statement[j]))
            assign_obj_label = statement[j]
            j += 1
            while (j < len(statement) and
                     statement[j].strip(" \t\r\n") == ""):
                j += 1
            assert(statement[j] == "{")
            j += 1  # Past content opening '{'
            with_block_first = j
            bracket_depth = 0
            while (j < len(statement) and
                    (statement[j] != "}" or
                    bracket_depth > 0)):
                if statement[j] in {"(", "[", "{"}:
                    bracket_depth += 1
                elif statement[j] in {")", "]", "}"}:
                    bracket_depth -= 1
                j += 1
            assert(statement[j] == "}")
            with_block_last = j - 1
            j += 1  # Past closing '}'
            while (j < len(statement) and
                     statement[j].strip(" \t\r\n") == ""):
                j += 1
            assert(j >= len(statement))
            assigned_expr = translate_expression_tokens(
                statement[assign_obj_first:
                    assign_obj_last+1],
                module_name, package_name,
                project_info=project_info,
                parent_statements=parent_statements,
                processed_imports=processed_imports,
                add_indent=extra_indent)
            with_block_code = translate(
                untokenize(statement[
                    with_block_first:
                    with_block_last+1]), module_name, package_name,
                parent_statements=(
                    parent_statements + [statement_cpy]),
                extra_indent=extra_indent,
                folder_path=folder_path,
                project_info=project_info,
                processed_imports=processed_imports,
                translate_file_queue=translate_file_queue,
                orig_h64_imports=orig_h64_imports
            )
            result += (indent + assign_obj_label + " = (" +
                untokenize(assigned_expr) + ")\n")
            result += (indent + "try:\n")
            result += with_block_code + "\n"
            result += (indent + "    pass\n")
            result += (indent + "finally:\n")
            result += (indent + "    if hasattr(" +
                assign_obj_label + ", \"close\"):\n")
            result += (indent + "        " +
                assign_obj_label + ".close()\n")
            result += (indent + "    elif hasattr(" +
                assign_obj_label + ", \"destroy\"):\n")
            result += (indent + "        " +
                assign_obj_label + ".destroy()\n")
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
                        project_info=project_info,
                        parent_statements=parent_statements,
                        processed_imports=processed_imports,
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
                    processed_imports=processed_imports,
                    translate_file_queue=translate_file_queue,
                    orig_h64_imports=orig_h64_imports
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
            in_orig_imports = False
            for orig_h64_import in orig_h64_imports:
                if (orig_h64_import[0] == import_module and
                        (orig_h64_import[1] == import_package or
                        import_package == project_info.package_name)):
                    in_orig_imports = True
            if not in_orig_imports:
                raise RuntimeError(
                    "encountered import statement for " +
                    str((import_module, import_package)) +
                    ", but it's not listed in orig_h64_imports???")
            target_path = import_module.replace(".", "/") + ".h64"
            target_filename = import_module.split(".")[-1] + ".py"
            append_code = ""
            python_module = import_module
            package_python_subfolder = project_info.\
                get_package_subfolder(import_package,
                for_output=True)
            package_source_subfolder = project_info.\
                get_package_subfolder(import_package,
                for_output=False)
            if (package_python_subfolder != None and
                    len(package_python_subfolder) > 0):
                if package_python_subfolder.endswith("/"):
                    package_python_subfolder = (
                        package_python_subfolder[:-1])
                python_module = package_python_subfolder.\
                    replace("/", ".") + "." + python_module
                for module_part in import_module.split(".")[:-1]:
                    append_code += ("; ((" + module_part +
                        " := _translator_runtime_helpers." +
                        "_ModuleObject()) if (\"" +
                        module_part + "\" not in locals() and \"" +
                        module_part + "\" not in globals()) else None)")
                append_code += ("; " +
                    import_module + " = " +
                    package_python_subfolder.replace("/", ".") +
                    "." + import_module)
            if len(package_source_subfolder) > 0:
                target_path = os.path.normpath(
                    os.path.join(os.path.abspath(
                    project_info.repo_folder),
                    package_source_subfolder, target_path))
            else:
                target_path = os.path.normpath(
                    os.path.join(os.path.abspath(
                    project_info.code_folder), target_path))
            if (not os.path.exists(target_path) and
                    os.path.isdir(target_path.rpartition(".h64")[0])):
                # Case of 'import bla' targeting 'bla/bla.h64'
                alternate_path = os.path.join(
                    target_path.rpartition(".h64")[0],
                    import_module.split(".")[-1] + ".h64")
                if os.path.exists(alternate_path):
                    target_path = alternate_path
                    target_filename = "__init__.py"

            # Check if this module is only used for remapped uses:
            found_nonremapped_use = False
            found_remapped_use = False
            if DEBUGV.ENABLE_REMAPPED_USES:
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
                # See if it matches our current import:
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
                # Make sure it doesn't match another known import
                # that has more components:
                for orig_h64_import in orig_h64_imports:
                    other_elements = orig_h64_import[0].split(".")
                    if (len(other_elements) <=
                            len(import_module_elements)):
                        continue
                    other_match = True
                    k2 = 0
                    while k2 < len(other_elements):
                        if (k2 * 2 + i >= len(tokens) or
                                tokens[i + k2 * 2] !=
                                other_elements[k2] or
                                (k2 + 1 < len(other_elements) and
                                (k2 * 2 + 1 + i >= len(tokens) or
                                tokens[i + k2 * 2 + 1] != "."))):
                            other_match = False
                            break
                        k2 += 1
                    if other_match:
                        match = False
                        break
                if not match:
                    i += 1
                    continue
                # If we arrive here, it's a definite match:
                remapped_uses_key = import_module
                if import_package != None:
                    remapped_uses_key += "@" + import_package
                if remapped_uses_key not in remapped_uses:
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: found " +
                            "non-remapped use (no remaps for " +
                            "module " + str(remapped_uses_key) +
                            "): " + str(
                            tokens[i:i +
                            len(import_module_elements) + 10]))
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
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print("tools/translator.py: debug: found " +
                            "non-remapped use: " + str(
                            tokens[i:i + len(import_module_elements) + 10]))
                else:
                    found_remapped_use = True
                i += 1

            # Add import:
            processed_imports[import_module] = {
                "package": import_package,
                "module": import_module,
                "python-module": python_module,
                "path": target_path,
                "target-filename": target_filename,
            }

            # Skip import code if it only has remapped uses:
            if not found_nonremapped_use and found_remapped_use:
                if DEBUGV.ENABLE_REMAPPED_USES:
                    print("tools/translator.py: debug: hiding " +
                        "import since all uses are remapped: " +
                        str(import_module) + ("" if
                        import_package is None else
                        "@" + import_package))
                processed_imports[import_module]["python-module"] = (
                    None  # since it wasn't actually imported
                )
                continue

            # Add translated import code:
            result += "import " + python_module + append_code + "\n"
            queue_file_if_not_queued(translate_file_queue,
                (target_path, target_filename,
                import_module, os.path.dirname(target_path),
                import_package), reason="imported from " +
                "module " + str(module_name) + (
                "" if package_name is None else "@" + package_name) +
                " with non-remapped uses")
            for otherfile in os.listdir(os.path.dirname(target_path)):
                otherfilepath = os.path.normpath(os.path.join(
                    os.path.dirname(target_path), otherfile
                ))
                if (not otherfilepath.endswith(".h64") or
                        os.path.isdir(otherfilepath)):
                    continue
                otherfilename = os.path.basename(
                    otherfilepath.rpartition(".h64")[0]
                ) + ".py"
                if (otherfilename.rpartition(".py")[0] ==
                        _splitpath(os.path.dirname(target_path))[-1]):
                    otherfilename = "__init__.py"
                otherfile_module = ".".join(
                    import_module.split(".")[:-1] +
                    [otherfile.rpartition(".h64")[0].strip()]
                )
                queue_file_if_not_queued(translate_file_queue,
                    (otherfilepath, otherfilename,
                    otherfile_module, os.path.dirname(target_path),
                    import_package))
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
                for import_mod_name in processed_imports:
                    if type_name.startswith(import_mod_name + "."):
                        type_module = import_mod_name
                        type_name = type_name[len(type_module) + 1:]
                        type_package = processed_imports\
                            [type_module]["package"]
                        type_python_module = processed_imports[
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
                    project_info=project_info,
                    parent_statements=parent_statements,
                    processed_imports=processed_imports,
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
                processed_imports=processed_imports,
                translate_file_queue=translate_file_queue,
                orig_h64_imports=orig_h64_imports
            )
            (cleaned_argument_tokens,
                extra_init_code) = separate_func_keyword_arg_code(
                    argument_tokens, indent=(indent + "    " +
                    ("    " if type_name is not None else "")))
            if type_name is None:
                result += (indent + "def " + name +
                    untokenize(cleaned_argument_tokens) + ":\n")
                suggested_indent = (
                    get_first_nonempty_line_indent(
                    extra_init_code + "\n" +
                    translated_contents + "\n"))
                result += (extra_init_code + "\n" +
                    translated_contents + "\n")
                if suggested_indent != None:
                    result += (suggested_indent + "pass\n")
                else:
                    result += (indent + "    pass\n")
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
                processed_imports=processed_imports,
                translate_file_queue=translate_file_queue,
                orig_h64_imports=orig_h64_imports
            )
            continue
        # See if this is an assignment:
        assign_token_idx = -1
        bracket_depth = 0
        k = 0
        while (k < len(statement) and ((
                statement[k] != "=" and
                (len(statement[k]) != 2 or
                statement[k][1] != "=")) or
                bracket_depth > 0)):
            if statement[k] in {"(", "[", "{"}:
                bracket_depth += 1
            elif statement[k] in {")", "]", "}"}:
                bracket_depth -= 1
            k += 1
        if k < len(statement):
            assert("=" in statement[k])
            if statement[k] not in {"==", ">=", "<="}:
                assign_token_idx = k
        # Process as generic unknown statement:
        result += indent + untokenize(translate_expression_tokens(
            statement, module_name, package_name,
            project_info=project_info,
            parent_statements=parent_statements,
            processed_imports=processed_imports,
            add_indent=extra_indent,
            is_assign_stmt=(assign_token_idx >= 0),
            assign_token_index=assign_token_idx)) + "\n"
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


def run_translator_main():
    args = sys.argv[1:]
    target_file = None
    target_file_args = []
    keep_files = False
    run_as_test = False
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
                print("\n" + "\n".join(textwrap.wrap(
                    HACKY_WARNING.strip(), width=70)) + "\n")
                print("Options:")
                print("    --as-test              "
                      "Don't look for a main func,")
                print("                           "
                      "instead run all test_* funcs.")
                print("    --debug                "
                      "Show debug output.")
                print("    --debug-async          "
                      "Show info on async operations.")
                print("    --debug-python-output  "
                      "Show the generated python.")
                print("    --debug-queue          "
                      "Show info about queueing files.")
                print("    --help                 "
                      "Show this help text")
                print("    --keep-files           "
                      "Keep translated files and ")
                print("                           "
                      "print out path to them.")
                print("    --version              "
                      "Print out program version")
                sys.exit(0)
            elif args[i] == "--as-test":
                run_as_test = True
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
            elif args[i] == "--debug-async":
                DEBUGV.ENABLE = True
                DEBUGV.ENABLE_ASYNC_OPS = True
            elif args[i] == "--debug":
                DEBUGV.ENABLE = True
                DEBUGV.ENABLE_FILE_PATHS = True
                DEBUGV.ENABLE_TYPES = True
                DEBUGV.ENABLE_REMAPPED_USES = True
            elif args[i] == "--debug-queue":
                DEBUGV.ENABLE = True
                DEBUGV.ENABLE_QUEUE = True
            elif args[i] == "--debug-python-output":
                DEBUGV.ENABLE = True
                DEBUGV.ENABLE_CONTENTS = True
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
        # Normalize and make to absolute path, and clean it up:
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
        # Detect if we hit the root folder, and hence found nothing:
        if (("windows" in platform.system().lower() and
                len(project_info.repo_folder) == 3) or
                "windows" not in platform.system().lower() and
                project_info.repo_folder == "/"):
            raise RuntimeError("failed to detect repository folder")
        # Go up by one:
        modname = os.path.basename(
            os.path.normpath(os.path.normpath(
            project_info.repo_folder))) + "." + modname
        project_info.repo_folder = os.path.normpath(
            os.path.abspath(
            os.path.join(project_info.repo_folder, "..")))
    if DEBUGV.ENABLE:
        print("tools/translator.py: debug: " +
            "detected repository folder: " +
            project_info.repo_folder)
    project_info.code_relpath = ""
    if os.path.exists(os.path.join(project_info.repo_folder, "src")):
        project_info.code_relpath = "src/"
        assert(modname.startswith("src."))
        modname = modname[len("src."):]
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
                pkg_version = horp_ini_string_get_package_version(contents)
                if pkg_version != None:
                    project_info.package_version = pkg_version
                flicenses = horp_ini_string_get_package_license_files(contents)
                if flicenses != None:
                    flicenses = flicenses.split(",")
                    for fname in sorted(flicenses):
                        if (".." in fname or fname == "." or "/" in fname or
                                "\\" in fname or fname == "" or
                                "?" in fname or "*" in fname):
                            continue
                        fpath = os.path.join(
                            project_info.repo_folder, fname)
                        if (os.path.exists(fpath) and
                                not os.path.isdir(fpath)):
                            with open(fpath, "r", encoding="utf-8") as f:
                                text = f.read()
                                text = (text.replace("\r\n", "\n").
                                    replace("\r", "\n"))
                                project_info.licenses.append(
                                    (fname, text))
            else:
                print("tools/translator.py: warning: " +
                    "failed to get package name from horp.ini: " +
                    str(os.path.join(repo_folder, "horp.ini")))
    if DEBUGV.ENABLE:
        print("tools/translator.py: debug: " +
            "detected package name: " +
            str(project_info.package_name))
    translate_file_queue = []
    queue_file_if_not_queued(translate_file_queue,
        (os.path.normpath(os.path.abspath(target_file)),
        os.path.basename(target_file.rpartition(".h64")[0]) + ".py",
        modname, modfolder, project_info.package_name))
    mainfilepath = translate_file_queue[0][0]
    while len(translate_file_queue) > 0:
        (target_file, target_filename, modname, modfolder,
         package_name, reason) = translate_file_queue[0]
        original_queue_tuple = translate_file_queue[0]
        translate_file_queue = translate_file_queue[1:]
        if target_file in translated_files:
            continue
        if DEBUGV.ENABLE and DEBUGV.ENABLE_QUEUE:
            print("tools/translator.py: debug: looking at "
                "queue item: " + str(
                list(original_queue_tuple)[:-1]) +
                " (queue reason" +
                (" not given" if (reason is None or reason == "") else
                ": " + reason) + ")")
        for otherfile in os.listdir(modfolder):
            otherfilepath = os.path.normpath(
                os.path.abspath(os.path.join(modfolder, otherfile)))
            if (os.path.isdir(otherfilepath) or
                    not otherfilepath.endswith(".h64") or
                    otherfilepath in translated_files or
                    otherfilepath == target_file):
                continue
            otherfilename = os.path.basename(
                otherfilepath.rpartition(".h64")[0]) + ".py"
            if (otherfilename.rpartition(".py")[0] ==
                    _splitpath(modfolder)[-1]):
                otherfilename = "__init__.py"
            new_modname = (modname.rpartition(".")[0] + "."
                if "." in modname else "")
            if otherfilename != "__init__.py":
                new_modname += (os.path.basename(otherfile).
                    rpartition(".h64")[0])
            queue_file_if_not_queued(translate_file_queue,
                (otherfilepath, otherfilename,
                new_modname, modfolder, package_name))
        contents = None
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                contents = f.read()
        except FileNotFoundError as e:
            print("translator.py: error: trying to locate module " +
                modname + " in package " + package_name +
                " but file is missing: " + str(target_file))
            sys.exit(1)
        original_contents = contents
        sanity_check_h64_codestring(contents, modname=modname,
            filename=target_file)
        assert(type(contents) == str)
        contents = separate_out_inline_funcs(tokenize(contents))
        assert(type(contents) == list and
            (len(contents) == 0 or type(contents[0]) == str))
        contents_result = (
            translate(contents, modname, package_name,
                folder_path=modfolder,
                project_info=project_info,
                translate_file_queue=translate_file_queue))
        disk_target_folder = (
            project_info.get_package_subfolder(
                package_name, for_output=True) +
            modname.replace(".", "/"))
        if target_filename != "__init__.py":
            disk_target_folder = os.path.dirname(disk_target_folder)
        if DEBUGV.ENABLE and DEBUGV.ENABLE_QUEUE:
            print("tools/translator.py: debug: will write "
                "queue item " + str(target_file) + " to "
                "disk target folder: " + str(disk_target_folder))
        translated_files[target_file] = {
            "module-name": modname,
            "package-name": package_name,
            "module-folder": modfolder,
            "target-filename": target_filename,
            "path": target_file,
            "disk-fake-folder": disk_target_folder,
            "output": contents_result,
            "original-source": original_contents,
        }
    output_folder = tempfile.mkdtemp(prefix="h64-tools-translator-")
    assert(os.path.isabs(output_folder) and "h64-tools" in output_folder)
    try:
        for translated_file in translated_files:
            associated_package_output_folder = os.path.join(
                output_folder,
                project_info.get_package_subfolder(
                    translated_files[translated_file]
                        ["package-name"], for_output=True))
            contents_result = (
                "import os as _remapped_os;import sys as _remapped_sys;" +
                "_remapped_sys.path.insert(1, " +
                    as_escaped_code_string(os.path.join(
                        output_folder, "_translator_runtime")) + ");" +
                "_remapped_sys.path.insert(1, " +
                    as_escaped_code_string(
                    associated_package_output_folder) + ");" +
                "_remapped_sys.path.append(" +
                    as_escaped_code_string(output_folder) + ");" +
                "_translator_kw_arg_default_value = object();" +
                "_translated_program_version = " +
                as_escaped_code_string(
                    project_info.package_version if
                    project_info.package_version != None else
                    "unknown") + ";" +
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
                        untokenize(regtype.funcs
                            ["init"]["arguments"]) + ":\n")
                    if regtype.init_code != None:
                        contents_result += regtype.init_code + "\n"
                    contents_result += regtype.funcs["init"]["code"] + "\n"
                    contents_result += ("        pass\n")
                elif regtype.init_code != None:
                    contents_result += ("    def __init__(self):\n")
                    contents_result += regtype.init_code + "\n"
                    contents_result += ("        pass\n")
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
                        untokenize(regtype.funcs
                            [funcname]["arguments"]) + ":\n")
                    contents_result += (
                        regtype.funcs[funcname]["code"] + "\n")

            if (translated_files[translated_file]["path"] ==
                    mainfilepath):
                if run_as_test:
                    test_funcs = get_global_standalone_func_names(
                        translated_files[translated_file]
                            ["original-source"])
                    test_funcs = [tf for tf in test_funcs if
                        tf.startswith("test_")]
                    if len(test_funcs) == 0:
                        print("tools/translator.py: error: "
                            "no test functions found in this file")
                        sys.exit(1)
                    contents_result += ("\nif __name__ == '__main__':" +
                        "\n    ")
                    for tf in test_funcs:
                        contents_result += tf + "(); "
                else:
                    contents_result += (
                        "\nif __name__ == '__main__':" +
                        "\n    _remapped_sys.exit(" +
                        "\n        _translator_runtime_helpers." +
                                    "_run_main(main))\n")

            if DEBUGV.ENABLE and DEBUGV.ENABLE_CONTENTS:
                print("tools/translator.py: debug: have output of " +
                    str(len(contents_result.splitlines())) + " lines for: " +
                    translated_file + " (module: " +
                    translated_files[translated_file]["module-name"] + ")")
                print(contents_result)
            translated_files[translated_file]["output"] = contents_result
            #print(tokenize(b" \n\r test".decode("utf-8")))
        returncode = 0
        if keep_files:
            print("tools/translator.py: info: writing " +
                "translated files to (will be kept): " +
                output_folder)
        elif DEBUGV.ENABLE and DEBUGV.ENABLE_FILE_PATHS:
            print("tools/translator.py: debug: writing temporary " +
                "result to (will be deleted): " +
                output_folder)
        for helper_file in os.listdir(translator_py_script_dir):
            if (not helper_file.startswith("translator_runtime") or
                    not helper_file.endswith(".py")):
                continue
            if not os.path.exists(os.path.join(output_folder,
                    "_translator_runtime")):
                os.mkdir(os.path.join(output_folder,
                    "_translator_runtime"))
            t = None
            with open(os.path.join(translator_py_script_dir,
                    helper_file), "r", encoding="utf-8") as f:
                t = f.read()
                t = (translator_debugvars.
                    get_debug_var_strings() + "\n" + t)
                t = t.replace("__translator_py_path__",
                    as_escaped_code_string(translator_py_script_path))
                license_list_str = "["
                for linfo in project_info.licenses:
                    if len(license_list_str) > 1:
                        license_list_str += ","
                    license_list_str += ("_LicenseObj(" +
                        as_escaped_code_string(linfo[0]) + "," +
                        "text=" +
                        as_escaped_code_string(linfo[1]) + ")")
                license_list_str += "]"
                t = t.replace("__translator_licenses_list",
                    license_list_str)
            with open(os.path.join(output_folder,
                    "_translator_runtime", "_" + helper_file),
                    "w", encoding="utf-8") as f:
                f.write(t)
            if DEBUGV.ENABLE and DEBUGV.ENABLE_FILE_PATHS:
                print("tools/translator.py: debug: wrote file: " +
                    os.path.join(output_folder,
                    "_translator_runtime", "_" + helper_file))
        run_py_path = None
        for translated_file in translated_files:
            name = os.path.basename(
                translated_files[translated_file]["path"]
            ).rpartition(".h64")[0].strip()
            targetfilename = os.path.basename(
                translated_files[translated_file]["target-filename"]
            )
            contents = translated_files[translated_file]["output"]
            subfolder = translated_files[translated_file]["disk-fake-folder"]
            assert(not os.path.isabs(subfolder) and ".." not in subfolder)
            subfolder_abs = os.path.join(output_folder, subfolder)
            if not os.path.exists(subfolder_abs):
                os.makedirs(subfolder_abs)
            with open(os.path.join(output_folder, subfolder,
                    targetfilename), "w", encoding="utf-8") as f:
                f.write(contents)
            if DEBUGV.ENABLE and DEBUGV.ENABLE_FILE_PATHS:
                print("tools/translator.py: debug: wrote file: " +
                    os.path.join(output_folder, subfolder,
                    targetfilename) + " (module: " +
                    translated_files[translated_file]["module-name"] + ")")
            if translated_files[translated_file]["path"] == mainfilepath:
                run_py_path = os.path.join(output_folder, subfolder,
                    targetfilename)
        launch_cmd = [
            sys.executable, run_py_path
        ] + target_file_args
        if DEBUGV.ENABLE:
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


if __name__ == "__main__":
    run_translator_main()


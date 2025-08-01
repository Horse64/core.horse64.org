#!/usr/bin/python3
# Copyright (c) 2020-2025, ellie/@ell1e & Horse64's contributors
# (see AUTHORS.md).
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

# !!!!!!!!! HEED THIS WARNING !!!!!!!!!
HACKY_WARNING=(
    "THIS TOOL (translator.py) ONLY SUPPORTS A SUBSET OF " +
    "HORSE64 AND WILL OTHERWISE CRASH AND BURN. IT WON'T CATCH MANY " +
    "CODE ERRORS AND JUST EXPLODE OR RUN IT WRONG. " +
    "If you can, really use the official compiler horsec.")

VERSION="unknown"

import functools
import math
import os
import platform
import pywildcard
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import uuid

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.join(
    translator_py_script_dir, "translator.py"
)

sys.path.insert(1, os.path.join(translator_py_script_dir,
    "translator_modules"))

import translator_debugvars
from translator_debugvars import DEBUGV
import translator_hacks_registry

from translator_horphelpers import (
    horp_ini_string_get_package_name,
    horp_ini_string_get_package_version,
    horp_ini_string_get_package_license_files
)

import translator_runtime_helpers_preprocessor as \
    translator_preprocessor

from translator_transformhelpers cimport (
    is_problematic_identifier_name,
    transform_h64_misc_inline_to_python,
    transform_h64_with_to_do_rescue,
    indent_sanity_check,
)

from translator_transformhelpers import (
    get_declared_local_globals_simple,
    apply_make_set_call,
    set_expr_len_if_any,
    make_string_literal_python_friendly,
    is_isolated_pure_assign,
    vec_expr_len_if_any,
    apply_make_vec_call,
)

from translator_scopehelpers import (
    get_global_standalone_func_names,
    extract_all_imports,
    get_names_defined_in_func,
    get_global_names,
    statement_declared_identifiers,
    get_undefined_uses_in_func,
)

from translator_syntaxhelpers cimport (
    is_identifier, identifier_or_keyword,
    nextnonblank, nextnonblankidx,
    firstnonblank, firstnonblankidx,
    prevnonblank, prevnonblankidx,
    get_next_token,
    is_h64op_with_righthand,
    is_h64op_with_lefthand,
    is_whitespace_token,
    sanity_check_h64_codestring,
    tokenize, untokenize,
    split_toplevel_statements,
)
from translator_syntaxhelpers import (
    get_indent,
    as_escaped_code_string,
    stmt_list_uses_banned_things,
    get_next_statement,
    separate_out_inline_funcs,
    is_number_token,
    make_kwargs_in_call_tailing,
)

from translator_latertransform import (
    transform_later_to_closures,
    transform_later_ifs_to_closures,
)

translated_files = {}

# Set version:
if os.path.exists(os.path.join(translator_py_script_dir,
        "..", "horp.conf")):
    with open(os.path.join(translator_py_script_dir,
            "..", "horp.conf")) as f:
        _get_version = horp_ini_string_get_package_version(
            f.read()
        )
        if _get_version:
            VERSION = _get_version

# XXX HACK alert (written by ell1e):
# The mpath() function is needed because python's module handling is
# hazardously simplistic, and if any submodule anywhere matches a
# standalone module like `token.py` it'll just happily import the
# wrong one with no good way to prevent this other than renaming
# your own module to never have naming conflicts.
# To solve this, all horse modules are *actually* named _h64mod_...
# on disk, which we achieve by piping only the final output paths
# through this hacky transformation function (so that we can otherwise
# pretend to have sane module names):
def mpath(p, sep="/"):
    if sep == "/":
        p = p.replace("\\", "/")
    parts = list(p.split(sep))
    i = len(parts)
    while i - 1 >= 0:
        i -= 1
        if (parts[i] == "main" and i >= 1 and
                parts[i - 1] == "horse_modules"):
            break
        if ("_" in parts[i] and
                parts[i].index("_") != parts[i].rindex("_") and
                i >= 1 and parts[i - 1] == "horse_modules"):
            break
        if parts[i] == "horse_modules":
            break
        if (not parts[i].startswith("_h64mod_") and
                not parts[i] in {"__init__", "__init__.py"}):
            parts[i] = "_h64mod_" + parts[i]
    return sep.join(parts)

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
DEBUGV.ENABLE_MODLOAD = False

remapped_uses = {
    "bignum@core.horse64.org": {
        "bignum.compare_nums":
            "_translator_runtime_helpers._bignum_compare_nums",
    },
    "compiler@core.horse64.org": {
        "compiler.run_file":
            "_translator_runtime_helpers._compiler_run_file",
    },
    "date@core.horse64.org": {
        "date.get_year":
            "_translator_runtime_helpers._date_get_year",
    },
    "debugger@core.horse64.org": {
        "debugger.is_debug_build":
            "(lambda: True)",
        "debugger.get_addr":
            "_translator_runtime_helpers._internals_get_addr",
    },
    "translator_internals@core.horse64.org": {
        "translator_internals.preprocess_file_in_translator":
            "_translator_runtime_helpers."
                "preprocess_file_in_translator",
    },
    "io@core.horse64.org": {
        "io.working_dir":
            "_translator_runtime_helpers._get_cwd_async",
        "io.open":
            "_translator_runtime_helpers._io_open",
        "io.make_dir":
            "_translator_runtime_helpers._io_make_dir",
        "io.exists":
            "_translator_runtime_helpers._io_exists",
        "io.is_dir":
            "_translator_runtime_helpers._io_is_dir",
        "io.list_dir":
            "_translator_runtime_helpers._io_ls_dir",
        "io.tree_list_walker":
            "_translator_runtime_helpers._io_tree_list_walker",
        "io.make_or_get_appcache":
            "_translator_runtime_helpers._make_or_get_appcache",
        "io.remove_file":
            "_translator_runtime_helpers._io_remove_file",
        "io.copy_file":
            "_translator_runtime_helpers._io_copy_file",
        "io.copy_dir":
            "_translator_runtime_helpers._io_copy_dir",
        "io.remove_dir":
            "_translator_runtime_helpers._io_remove_dir",
        "io.rename":
            "_translator_runtime_helpers._io_rename_dir",
        "io.make_tmpdir":
            "_translator_runtime_helpers._make_tmpdir",
    },
    "html@core.horse64.org": {
        "html.escape":
            "_translator_runtime_helpers._html_escape",
    },
    "json@core.horse64.org": {
        "json.dump":
            "_translator_runtime_helpers._json_dump",
        "json.parse":
            "_translator_runtime_helpers._json_parse",
    },
    "base64@core.horse64.org": {
        "base64.parse":
            "_translator_runtime_helpers._base64_parse",
        "base64.dump":
            "_translator_runtime_helpers._base64_dump",
    },
    "math@core.horse64.org": {
        "math.abs": "_translator_runtime_helpers._math_abs",
        "math.min": "_translator_runtime_helpers._math_min",
        "math.max": "_translator_runtime_helpers._math_max",
        "math.floor": "_translator_runtime_helpers._math_floor",
        "math.ceil": "_translator_runtime_helpers._math_ceil",
        "math.round": "_translator_runtime_helpers._math_round",
        "math.parse_hex":
            "_translator_runtime_helpers._math_parse_hex",
    },
    "net@core.horse64.org": {
        "net.lookup_name":
            "_translator_runtime_helpers._net_lookup_name",
        "net.NetworkIOError":
            "_translator_runtime_helpers._NetworkIOError",
        "net.ServerError":
            "_translator_runtime_helpers._ServerError",
        "net.ClientError":
            "_translator_runtime_helpers._ClientError",
    },
    "net.serve@core.horse64.org": {
        "net.serve.http":
            "_translator_runtime_helpers._net_serve_http",
    },
    "net.fetch@core.horse64.org": {
        "net.fetch.open":
            "_translator_runtime_helpers._net_fetch_open",
    },
    "path@core.horse64.org": {
        "path.make_abs": "_remapped_os.path.abspath",
        "path.normalize":
            "_remapped_os.path.normpath",
        "path.is_abs": "_remapped_os.path.isabs",
        "path.join":
            "_translator_runtime_helpers._path_join",
        "path.basename" : "_remapped_os.path.basename",
        "path.dirname": "_remapped_os.path.dirname",
        "path.sep": "_remapped_os.path.sep",
    },
    "process@core.horse64.org": {
        "process.args": "(_remapped_sys.argv[1:])",
        "process.get_env":
            "_translator_runtime_helpers._get_env",
        "process.run":
            "_translator_runtime_helpers._process_run_async",
    },
    "random@core.horse64.org": {
        "random.gen_id":
            "(lambda: str(_remapped_uuid."
                "uuid4()).replace('-', ''))",
        "random.fac":
            "(lambda: float(_remapped_random."
                "SystemRandom().random()))",
        "random.int":
            "(lambda x, y: int(_remapped_random."
                "SystemRandom().randint(x, y)))",
        "random.choice":
            "_translator_runtime_helpers._random_choice",
    },
    "system@core.horse64.org": {
        "system.exit" : "_remapped_sys.exit",
        "system.osname":
            "(_translator_runtime_helpers._system_osname())",
        "system.program_compiler_name":
            "(\"horse64-translator-py v\" + " +
            as_escaped_code_string(VERSION) + ")",
        "system.program_licenses_as_list":
            "(_translator_runtime_helpers._return_licenses)",
        "system.program_version":
            "(_translated_program_version)",
        "system.self_exec_path" :
            "(lambda x:_translator_runtime_helpers._return_str_async(" +
            "x, _translated_program_main_script_file." +
            "rpartition(\".h64\")[0]))",
    },
    "terminal@core.horse64.org": {
        "terminal.get_line":
            "_translator_runtime_helpers._terminal_get_line",
        "terminal.open_input":
            "_translator_runtime_helpers._terminal_open_input",
    },
    "text@core.horse64.org": {
        "text.pos_from_line_col":
            "_translator_runtime_helpers."
                "_text_pos_from_line_col",
        "text.code_to_bytes":
            "(lambda x: chr(x).encode('utf-8', 'surrogateescape'))",
        "text.from_code":
            "(lambda x: chr(x))",
        "text.glyph_codepoint_len":
            "(lambda s, pos=1: max(0, len(s) - (pos - 1)))",
        "text.full_glyphs_in_sub":
            "(lambda a, b, c: _translator_runtime_helpers."
            "_container_sub(a, b, c))",
        "text.code":
            "(lambda x: int(ord(x)))",
        "text.is_digits":
            "(lambda x: _translator_runtime_helpers."
                "_h64_is_digits(x))",
    },
    "textfmt@core.horse64.org": {
        "textfmt.outdent":
            "_translator_runtime_helpers._textformat_outdent",
        "textfmt.template_from_str":
            "_translator_runtime_helpers_templating." +
                "load_honse_html_tmpl_from_str",
    },
    "threading@core.horse64.org": {
        "threading.make_lock":
            "_translator_runtime_helpers._make_lock",
    },
    "time@core.horse64.org": {
        "time.sleep":
            "_translator_runtime_helpers._time_sleep",
        "time.ticks":
            "_translator_runtime_helpers._time_ts",
    },
    "uri@core.horse64.org": {
        "uri.get_protocol":
            "_translator_runtime_helpers._uri_get_protocol",
        "uri.to_file_or_vfs_path":
            "_translator_runtime_helpers."
                "_uri_to_file_or_vfs_path",
        "uri.unencode_path":
            "_translator_runtime_helpers._uri_unencode_path",
        "uri.encode_path":
            "_translator_runtime_helpers._uri_encode_path",
        "uri.dirname":
            "_translator_runtime_helpers._uri_dirname",
        "uri.basename":
            "_translator_runtime_helpers._uri_basename",
        "uri.add_part":
            "_translator_runtime_helpers._uri_add_part",
        "uri.traverse_up":
            "_translator_runtime_helpers._uri_traverse_up",
        "uri.get_path":
            "_translator_runtime_helpers." +
            "_uri_extract_path",
        "uri.normalize":
            "_translator_runtime_helpers." +
            "_uri_normalize",
        "uri.from_disk_path":
            "_translator_runtime_helpers." +
            "_file_uri_from_path",
        "uri.from_vfs_path":
            "_translator_runtime_helpers." +
            "_file_uri_from_vfs_path",
    },
    "wildcard@core.horse64.org": {
        "wildcard.match":
            "_translator_runtime_helpers._wildcard_match",
    },
}

class RegisteredType:
    def __init__(self, type_name, module_path, package_name,
            extends_tokens=None):
        self.module = module_path
        self.pkgname = package_name
        self.name = type_name
        self.init_code = ""
        self.order_no = 0
        self.extends_tokens = extends_tokens
        self.funcs = {}
        self.seen_in_type_stmt = False

known_types = {}

ensure_type_order_no = 0

def ordered_known_types():
    global known_types
    names = known_types.keys()
    def cmp_names(a, b):
        return (known_types[a].order_no -
            known_types[b].order_no)
    return sorted(
        names, key=functools.cmp_to_key(cmp_names)
    )

def ensure_type(
        type_name, module_path, package_name,
        extends_tokens=None,
        from_type_stmt=True):
    global known_types, ensure_type_order_no
    assert(not type_name.startswith("test_"))
    assert(type_name != None and module_path != None)
    if not from_type_stmt:
        extends_tokens = None
    package_name_part = ""
    if package_name is not None:
        package_name_part = "@" + package_name
    if (module_path + "." + type_name +
            package_name_part not in known_types):
        known_types[module_path + "." + type_name +
                package_name_part] = (
            RegisteredType(type_name, module_path, package_name)
        )
        if DEBUGV.ENABLE and DEBUGV.ENABLE_TYPES:
            print("translator.py: debug: registered type " +
                module_path + "." + type_name + package_name_part)
    if from_type_stmt:
        if known_types[module_path + "." +
                type_name + package_name_part].seen_in_type_stmt:
            raise ValueError("duplicate 'type' definition for " +
                (module_path + "." + type_name + package_name_part))
        known_types[module_path + "." +
            type_name + package_name_part].seen_in_type_stmt = True
        known_types[module_path + "." +
                type_name + package_name_part].extends_tokens = (
            extends_tokens
        )
        ensure_type_order_no += 1
        known_types[module_path + "." +
                type_name + package_name_part].order_no = (
            ensure_type_order_no
        )
        if DEBUGV.ENABLE and DEBUGV.ENABLE_TYPES:
            print("translator.py: debug: assigned order no. " +
                str(ensure_type_order_no) + " to type: " +
                module_path + "." + type_name + package_name_part)
    return known_types[module_path + "." +
        type_name + package_name_part]

def parse_type_import_ref(
        ref, i, sc=None, is_func=False,
        purpose="unknown", debug=False
        ):
    if debug:
        print("translator.py: debug: " +
            "parse_type_import_ref(..." +
            str(ref[max(0, i - 10):i + 10]) + "..., i=" + str(i) +
            ", purpose='" + str(purpose) + "', ...)")
    assert(sc != None)
    assert(i >= 0)
    while (i < len(ref) and
            ref[i].strip(" \r\t\n") == ""):
        i += 1
    assert(i < len(ref) and is_identifier(ref[i])), (
        "expected ref[" + str(i) + "] to be identifier: " +
        "i=" + str(i) + ",ref=" + str(ref)
    )
    type_modpath = ""
    type_package = None
    type_python_module = None
    type_name = None
    func_name = None
    raw_tokens = [ref[i]]
    if not is_func:
        type_name = ref[i]
    else:
        func_name = ref[i]
    index_after = i + 1
    if ref[i + 1] == ".":
        i2 = i
        while (i2 + 2 < len(ref) and
                ref[i2 + 1] == "."):
            if type_name is None and is_func:
                type_name = func_name
                func_name = ref[i2 + 2]
            else:
                if len(type_modpath) > 0:
                    type_modpath += "."
                if is_func:
                    type_modpath += type_name
                    type_name = ref[i2]
                    func_name = ref[i2 + 2]
                else:
                    type_modpath += ref[i2]
                    type_name = ref[i2 + 2]
            raw_tokens += ref[i2 + 1:i2 + 3]
            i2 += 2
            index_after += 2
        past_idx = i2 + 1
        found = False
        for import_mod_name in sc.processed_imports:
            effective_name = import_mod_name
            if (sc.processed_imports
                    [import_mod_name]["rename"] != None):
                effective_name = (
                    sc.processed_imports
                        [import_mod_name]["rename"]
                )
            if type_modpath == effective_name:
                found = True
                type_modpath = import_mod_name
                type_package = sc.processed_imports\
                    [type_modpath]["package"]
                type_python_module = sc.processed_imports[
                    type_modpath]["python-module"]
                break
        if not found and len(type_modpath) > 0:
            raise ValueError(
                "Encountered type import ref '" + type_modpath + "' "
                "(type_name=" + str(type_name) + ", "
                "purpose: " + str(purpose) + ") "
                "without corresponding import in same code file (" +
                sc.module_name + "): " +
                str(sc.processed_imports.keys())
            )
    if type_modpath == "":
        type_modpath = None
    if type_name != None and type_modpath is None:
        type_modpath = sc.module_name
        assert(type_modpath != None)
    if type_name != None and type_package is None:
        type_package = sc.package_name
    while (index_after < len(ref) and
            ref[index_after].strip(" \r\n\t") == ""):
        index_after += 1
    result = {
        "index-after": index_after,
        "modpath": type_modpath,
        "type-name": type_name,
        "func-name": func_name,
        "python-module": type_python_module,
        "package": type_package,
        "raw-tokens": raw_tokens,
    }
    return result
 
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

def make_valid_identifier(idf, sc=None):
    if (not is_identifier(idf) or
            is_problematic_identifier_name(
            idf, h64_problematic_only=True,
                python_problematic_only=False)):
        raise ValueError("Syntax error or problem " +
            (("in " + sc.module_name + (" in " + sc.package_name
             if sc.package_name != None else "")) if
             sc != None else "") + ": " +
            "horse64 doesn't allow redeclaring this name: " +
            idf)
    if (idf.startswith("_translator_renamed_") or
            idf == "assert"):
        raise ValueError("Syntax error or problem " +
            (("in " + sc.module_name + (" in " + sc.package_name
             if sc.package_name != None else "")) if
             sc != None else "") + ": " +
            "only horsec allows redeclaring this, the translator "
            "can't due to implementation limitations: " +
            idf)
    if is_problematic_identifier_name(
            idf, h64_problematic_only=False,
            python_problematic_only=True):
        return "_translator_renamed_" + idf
    return idf

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

def transform_for_file_output(
        contents, with_linenos=False
        ):
    if type(contents) == list:
        contents = untokenize(contents)
    if not with_linenos:
        return contents
    def padno(no):
        s = str(no)
        while len(s) < 4:
            s += " "
        return s
    result = ""
    lineno = 0
    for content_line in contents.splitlines():
        lineno += 1
        result += (
            ("\n" if lineno > 1 else "") +
            padno(lineno) + "|" + content_line.rstrip())
    return result

cdef _find_matching_remap_module__modcmp(e1, e2):
    if e1[0] == e2[0]:
        return (-1 if str(e1[1]) < str(e2[1]) else 1)
    return (-1 if e2[0] < e2[0] else 1)

cdef find_matching_remap_module(s, _i, sc):
    cdef int k, k2, i, debug_details
    cdef int match_tokens, maybe_match_tokens, \
        maybe_other_match, maybe_match, match
    i = _i

    if i >= len(s) or not is_identifier(s[i]):
        return (None, None, None, None)
    if prevnonblank(s, i) == "." or nextnonblank(s, i) != ".":
        return (None, None, None, None)

    debug_details = False

    # Output some start info:
    if debug_details:
        print("translator.py: debug: " +
            "find_matching_remap_module() " +
            "considering expression of: " +
            str(s[i:i + 5]))

    # See if we are INSIDE a remapped module:
    found_remapped_module = None
    found_remapped_package = None
    found_remapped_item = None
    found_remapped_tokens = None
    for remap_module_key in remapped_uses:
        if (sc.package_name == None or sc.module_name == None or
                sc.module_name + "@" + sc.package_name !=
                remap_module_key):
            continue

        if debug_details:
            print("translator.py: debug: " +
                "find_matching_remap_module() " +
                "checking a remap that happens in our own " +
                "module without import: " +
                str(remap_module_key))

        # See if module name actually occurs in token stream here:
        remapped_elements = (
            remap_module_key.partition("@")[0].split(".")
        )
        remapped_elements_len = len(remapped_elements)
        could_match = True
        k = 0
        while k < remapped_elements_len:
            if (k * 2 + i >= len(s) or
                    s[i + k * 2] !=
                    remapped_elements[k] or
                    (k + 1 < remapped_elements_len and
                    (k * 2 + 1 + i >= len(s) or
                    s[i + k * 2 + 1] != "."))):
                could_match = False
                break
            k += 1
        if not could_match:
            continue
        if (k * 2 + i >= len(s) or
                s[k * 2 + i - 1] != "."):
            continue
        could_match_item = s[k * 2 + i]
        if not is_identifier(could_match_item):
            continue
        # So this COULD match an item in this remapped module.
        # See if any item actually fits:
        for remapped_use in remapped_uses[remap_module_key]:
            if (remapped_use == sc.module_name + "." +
                    could_match_item):
                found_remapped_module = sc.module_name
                found_remapped_package = sc.package_name
                found_remapped_item = could_match_item
                found_remapped_tokens = k * 2 + 1
                break
        if found_remapped_module != None:
            break
    if found_remapped_module != None:
        # Found remap that is exact match in our own module.
        # Return that early:
        if debug_details:
            print("translator.py: debug: " +
                "find_matching_remap_module() " +
                "FOUND REMAP THAT BELONGS TO OWN MODULE " +
                found_remapped_module)
        return (found_remapped_module, found_remapped_package,
            found_remapped_item, found_remapped_tokens)

    # See if any external, imported use matches a remap:
    match = False
    match_package = None
    match_import_module = None
    match_item = None
    match_tokens = -1

    processed_imports_pairs = []
    for known_import in sc.processed_imports:
        processed_imports_pairs.append((
            sc.processed_imports[known_import]
                ["module"],
            sc.processed_imports[known_import]
                ["package"]))
    processed_imports_pairs = sorted(
        list(set(processed_imports_pairs).union(
            set([(a[0], a[1]) for a in sc.orig_h64_imports]))),
        key=functools.cmp_to_key(
            _find_matching_remap_module__modcmp
        )
    )

    for check_import in processed_imports_pairs:
        import_module_elements = (
            check_import[0].split(".")
        )
        maybe_match = True
        if debug_details:
            print("translator.py: debug: " +
                "find_matching_remap_module() " +
                "CHECKING " + str(s[i:i + 15]) +
                " AGAINST IMPORT " + str(check_import))

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
        # example).
        # We do this first on actual imports we've already seen:
        for known_other_import in processed_imports_pairs:
            other_module_elements = (
                known_other_import[0].split(".")
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
        if not maybe_match:
            continue
        maybe_match_tokens = -1
        maybe_match_item = None
        if (k * 2 + i < len(s) and
                is_identifier(s[k * 2 + i])):
            maybe_match_item = s[k * 2 + i]
            maybe_match_tokens = k * 2 + 1
        #print((s[i], k, maybe_match_item, maybe_match,
        #    sc.processed_imports[known_import]
        #            ["module"],
        #    import_module_elements,
        #    maybe_match_tokens))
        if (maybe_match and (not match or
                len(import_module_elements) >
                len(match_import_module.split("."))) and
                maybe_match_item != None):
            match = True
            match_import_module = check_import[0]
            match_package = check_import[1]
            match_tokens = maybe_match_tokens
            match_item = maybe_match_item
    if match == True:
        return (match_import_module, match_package,
            match_item, match_tokens)
    else:
        return (None, None, None, None)

cdef paired_roundbracket_close_has_else(s, _z):
    cdef int bdepth, z
    cdef int slen
    z = _z
    assert(s[z] == "(")
    bdepth = 0
    slen = len(s)
    z += 1
    while z < slen and (bdepth > 0 or s[z] != ")"):
        if s[z] in {"(", "{", "["}:
            bdepth += 1
        elif s[z] in {")", "}", "]"}:
            bdepth -= 1
        z += 1
    if (z > slen or s[z] != ")" or
            nextnonblank(s, z) != "else"):
        return False
    return True

cpdef translate_expression_tokens(list s, sc,
        is_assign_stmt=False, assign_token_index=-1):
    cdef int i, k, z
    cdef int bdepth, start_idx, slen

    cdef list orig_s

    s = list(s)
    assert("_remapped_os" not in s)
    assert("_remapped_sys" not in s)
    assert(sublist_index(s, ["sys", ".", "argv"]) < 0)

    # Fix indent first:
    slen = len(s)
    i = 0
    while i < slen:
        t = s[i]
        if t.strip("\t\r\n ") == "" and (
                t.startswith("\r\n") or
                t.startswith("\n")):
            t += sc.extra_indent
            s[i] = t
        elif t.strip("\t\r\n ") == "" and (
                t.endswith("\r\n") or
                t.endswith("\n")):
            t = sc.extra_indent + t
            s[i] = t
        i += 1
    # Fix assignments to square bracket accessed expression:
    if (is_assign_stmt and
            prevnonblank(s, assign_token_index) == "]"):
        i = prevnonblankidx(s, assign_token_index)
        # Find opening '[':
        bdepth = 0
        k = i - 1
        while (k >= 0 and (
                bdepth > 0 or
                s[k] != "[")):
            if s[k] in {")", "]", "}"}:
                bdepth += 1
            elif s[k] in {"(", "[", "{"}:
                bdepth -= 1
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

    # Translate typename()/assert()/"throw"/"has_attr"/...:
    previous_token = None
    i = 0
    while i < len(s):
        if (is_identifier(s[i]) and
                is_problematic_identifier_name(s[i],
                    h64_problematic_only=False,
                    python_problematic_only=True)) and (
                (s[i] != "len" and s[i] != "del" and
                s[i] != "copy") or
                previous_token != "."):
            s[i] = "_translator_renamed_" + s[i]
        if (s[i] == "typename" and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "h64_type"] + s[i + 1:]
        elif (s[i] == "assert" and
                previous_token != "." and
                nextnonblank(s, i) == "("):
            i2 = nextnonblankidx(s, i)
            assert(s[i2] == "(")
            open_bracket_idx = i2
            comma_idx = None
            bdepth = 0
            while i2 < len(s):
                if s[i2] in {"(", "[", "{"}:
                    bdepth += 1
                elif s[i2] == "," and bdepth == 1:
                    if comma_idx == None:
                        comma_idx = i2
                elif s[i2] in {")", "]", "}"}:
                    bdepth -= 1
                    if bdepth <= 0:
                        assert(s[i2] == ")")
                        break
                i2 += 1
            assert(i2 < len(s) and s[i2] == ")")
            if comma_idx != None:
                s = s[:comma_idx] + [")",
                    ",", "("] + s[comma_idx + 1:]
            i += 1
            continue
        elif (s[i] == "later" and
                previous_token == "return"):
            # Simply skip this.
            s = s[:i] + s[i + 1:]
            continue
        elif s[i].lower() in {"true",
                "_translator_renamed_true", "false",
                "_translator_renamed_false"}:
            idf = s[i]
            if "_" in idf:
                idf = s[i].rpartition("_")[2]
            print("translator.py: warning: "
                "Suspicious use in " +
                sc.module_name + (" in " + sc.package_name
                if sc.package_name != None else "") + ": "
                "found \"" + idf + "\" identifier, if you "
                "meant to use a bool, use: yes, no")
        elif s[i] in {"super", "_translator_renamed_super"}:
            print("translator.py: warning: "
                "Suspicious use in " +
                sc.module_name + (" in " + sc.package_name
                if sc.package_name != None else "") + ": "
                "found \"super\" identifier, if you meant to "
                "use the base class please use \"base\".")
        elif s[i] in {"class", "_translator_renamed_class"}:
            print("translator.py: warning: "
                "Suspicious use in " +
                sc.module_name + (" in " + sc.package_name
                if sc.package_name != None else "") + ": "
                "found \"class\" identifier, if you meant to "
                "declare a type please use \"type\".")
        elif s[i] in {"def", "_translator_renamed_def"}:
            print("translator.py: warning: "
                "Suspicious use in " +
                sc.module_name + (" in " + sc.package_name
                if sc.package_name != None else "") + ": "
                "found \"def\" identifier, if you meant to "
                "declare a function please use \"func\".")
        elif s[i] in {"contains", "_translator_renamed_contains"}:
            print("translator.py: warning: "
                "Suspicious use in " +
                sc.module_name + (" in " + sc.package_name
                if sc.package_name != None else "") + ": "
                "found \"contains\" identifier, if you meant to "
                "check a container for an item please use \"has\".")
        elif s[i] == "base":
            if i + 1 < len(s) and s[i + 1] == "(":
                raise ValueError("The expression base() in " +
                    sc.module_name + (" in " + sc.package_name
                    if sc.package_name != None else "") +
                    " is invalid, "
                    "a base type cannot be called. Did you mean to "
                    "use it without call brackets?")
            if (i + 2 < len(s) and s[i + 1] == "." and
                    s[i + 2] == "init"):
                s = s[:i] + ["_do_super_init"] + s[i + 3:]
                i += 3
                continue
            s = s[:i] + ["super", "(", ")"] + s[i + 1:]
        elif s[i] == "ValueError" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_ValueError"] + s[i + 1:]
        elif s[i] == "TypeError" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_TypeError"] + s[i + 1:]
        elif s[i] == "IOError" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_IOError"] + s[i + 1:]
        elif (s[i] == "Error" and
                previous_token != "."):
            s[i] = "BaseException"
        elif (s[i] == "ResourceMisuseError" and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_ResourceMisuseError"] + s[i + 1:]
        elif (s[i:i + 3] == ["io", ".", "PathNotFoundError"] and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_PathNotFoundError"] + s[i + 3:]
        elif (s[i] == "PermissionError" and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_PermissionError"] + s[i + 1:]
        elif (s[i] == "RuntimeError" and
                previous_token != "."):
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_RuntimeError"] + s[i + 1:]
        elif s[i] == "starts" and previous_token == ".":
            s[i] = "startswith"
        elif s[i] == "ends" and previous_token == ".":
            s[i] = "endswith"
        elif s[i] == "has" and previous_token == ".":
            s[i] = "__contains__"
        elif s[i] == "throw" and previous_token != ".":
            s[i] = "raise"
        elif s[i] == "alike_num" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_alike_num"] + s[i + 1:]
        elif s[i] == "print" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_h64_print"] + s[i + 1:]
        elif s[i] == "has_attr" and previous_token != ".":
            s = s[:i] + ["_translator_runtime_helpers",
                ".", "_has_attr"] + s[i + 1:]
        if s[i] == "[":
            vlen = vec_expr_len_if_any(s, i)
            if vlen != None:
                s = (s[:i] + apply_make_vec_call(s[i:i+vlen]) +
                    s[i + vlen:])
        if s[i] == "{":
            vlen = set_expr_len_if_any(s, i)
            if vlen != None:
                s = (s[:i] + apply_make_set_call(s[i:i+vlen]) +
                    s[i + vlen:])
        if s[i].strip("\r\n\t ") != "":
            previous_token = s[i]
        i += 1
    # Translate inline "if":
    slen = len(s)
    cdef set inline_if_expr_end_set = {"else", "{", "("}
    cdef set open_bracket_set = {"(", "[", "{"}
    cdef set close_bracket_set = {")", "]", "}"}
    cdef int value_1_start_idx, value_1_end_idx
    cdef int value_2_start_idx, value_2_end_idx
    i = 0
    while i < slen:
        if s[i] != "if":
            i += 1
            continue
        prev_nonblank_token = None
        had_nonwhitespace_token = False
        z = i + 1
        condition_start_idx = z
        condition_end_idx = -1
        value_1_start_idx = -1
        value_1_end_idx = -1
        value_2_start_idx = -1
        value_2_end_idx = -1
        bdepth = 0
        while z < slen:
            if (had_nonwhitespace_token and
                    s[z] in inline_if_expr_end_set and
                    bdepth == 0 and
                    not is_h64op_with_righthand(
                        prev_nonblank_token) and
                    (s[z] != "(" or
                     paired_roundbracket_close_has_else(s, z))
                    ):
                condition_end_idx = z - 1
                break
            if s[z] in open_bracket_set:
                bdepth += 1
            if s[z] in close_bracket_set:
                bdepth -= 1
            if s[z].strip(" \t\r\n") != "":
                prev_nonblank_token = s[z]
                had_nonwhitespace_token = True
            z += 1
        if z >= slen or s[z] != "(":
            # Not an inline if.
            if z < slen and (s[z] == "{" or s[z] == "else"):
                raise ValueError("Syntax error with 'if' in module " +
                    sc.module_name + ("" if sc.package_name is None else
                    " in " + sc.package_name))
            i += 1
            continue
        bdepth = 0
        value_1_start_idx = z + 1
        while z < slen:
            if (z > value_1_start_idx and
                    bdepth == 1 and
                    s[z] == ")" and
                    nextnonblank(s, z) == "else"):
                value_1_end_idx = z - 1
                break
            if s[z] in open_bracket_set:
                bdepth += 1
            if s[z] in close_bracket_set:
                bdepth -= 1
            z += 1
        assert(s[z] == ")")
        z += 1  # Go past ')'.
        while z < slen and s[z] != "else":
            z += 1
        z += 1  # Go past 'else'.
        while z < slen and s[z].strip(" \t\r\n") == "":
            z += 1
        if z >= slen or s[z] != "(":
            raise ValueError("Syntax error with 'if' in module " +
                sc.module_name + ("" if sc.package_name is None else
                " in " + sc.package_name))
        bdepth = 0
        full_end_idx = -1
        had_value2_nonblank = False
        value_2_start_idx = z + 1
        value_2_end_idx = -1
        while z < slen:
            if (z > value_2_start_idx and
                    had_value2_nonblank and
                    bdepth <= 1 and
                    s[z] == ")"):
                value_2_end_idx = z - 1
                full_end_idx = z
                bdepth = 0
                break
            if s[z] in open_bracket_set:
                bdepth += 1
            if s[z] in close_bracket_set:
                bdepth -= 1
            if s[z].strip("\r\t\n ") != "":
                had_value2_nonblank = True
            z += 1
        if value_2_end_idx < 0:
            raise ValueError("Syntax error with 'if' in module " +
                sc.module_name + ("" if sc.package_name is None else
                " in " + sc.package_name))
        assert(value_2_end_idx > value_1_start_idx)
        #print("IF INLINE: " + str((
        #    s[condition_start_idx:condition_end_idx + 1],
        #    s[value_1_start_idx:value_1_end_idx + 1],
        #    s[value_2_start_idx:value_2_end_idx + 1])))
        transformed_tokens = (["("] + (["("] +
            s[value_1_start_idx:value_1_end_idx + 1] +
            [")"] + ["if", "("] +
            s[condition_start_idx:condition_end_idx + 1] +
            [")", "else", "("] +
            s[value_2_start_idx:value_2_end_idx + 1] + [")"]
        ) + [")"])
        s = s[:i] + transformed_tokens + s[full_end_idx + 1:]
        slen = len(s)
        i = i + len(transformed_tokens) + 1

    # Translate XYZ.as_str()/XYZ.len to str(XYZ)/len(XYZ),
    # XXX: important (!!!) this needs to be BEFORE remapping functions
    #      translator built-ins, and BEFORE inserting Python line
    #      continuations
    s = transform_h64_misc_inline_to_python(s)

    # Translate remapped use to the proper remapped thing:
    slen = len(s)
    i = 0
    while i < slen:
        if (prevnonblank(s, i) in {
                "import", "func", ".", "var",
                "const"}):
            i += 1
            continue
        if not is_identifier(s[i]):
            i += 1
            continue
        #print("s[i] " + str(s[i]))

        # See if any external, imported use needs a remap:
        (match_import_module, match_package,
         match_item, match_tokens) = find_matching_remap_module(
            s, i, sc
        )
        if match_import_module is None:
            if (sc.module_name != None and sc.package_name != None and
                    (sc.module_name + "@" + sc.package_name) in
                    remapped_uses):
                remap_module_key = sc.module_name +\
                    "@" + sc.package_name
                for remapped_use in remapped_uses[remap_module_key]:
                    remap_original_use = sc.module_name + "." + s[i]
                    if remapped_use == remap_original_use:
                        if DEBUGV.ENABLE_REMAPPED_USES:
                            print("translator.py: debug: "
                                "remapping use of "
                                "the overridden expression: " +
                                remap_original_use + " in " +
                                remap_module_key)
                        insert_tokens = tokenize(remapped_uses
                            [remap_module_key][remapped_use])
                        oldtail = s[i + 1:]
                        del(s[i:])
                        s += insert_tokens
                        s += oldtail
                        slen = len(s)
                        i += len(insert_tokens)
                        break
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
                print("translator.py: debug: checking if " +
                    "use needs translation to remap: " +
                    remap_original_use + " in " + remap_module_key)
            for remapped_use in remapped_uses[remap_module_key]:
                if remapped_use == remap_original_use:
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print("translator.py: debug: "
                            "remapping use of "
                            "the overridden expression: " +
                            remap_original_use + " in " +
                            remap_module_key)
                    insert_tokens = tokenize(remapped_uses
                        [remap_module_key][remapped_use])
                    oldtail = s[i + match_tokens:]
                    del(s[i:])
                    s += insert_tokens
                    s += oldtail
                    slen = len(s)
                    i += len(insert_tokens)
                    break
        i += 1

    # Handle a bunch of things in one go:
    bdepth = 0
    slen = len(s)
    i = 0
    while i < slen:
        if s[i] in {"{", "(", "["}:
            bdepth += 1
        if s[i] in {"}", ")", "]"}:
            bdepth -= 1
        # Add line continuation things if not inside brackets:
        if bdepth <= 0:
            if (s[i] in {">", "=", "<", "!", "+", "-", "/", "*",
                    "%", "|", "^", "&", "~", ".", "in",
                    "and", "or", "not", ","} or
                    s[i].endswith("=") or s[i] == "->") and (
                    i + 1 < len(s) and
                    s[i + 1].strip(" \t\r\n") == "" and
                    s[i + 1].strip(" \t") != ""):
                tail = ([s[i + 1].lstrip(" \t")] +
                    s[i + 2:])
                del(s[i + 1:])
                s += ["\\"]
                s += tail
                slen = len(s)
            if ((s[i].endswith("\"") or s[i].endswith("'")) and
                    i + 2 < len(s) and
                    s[i + 1].strip(" \t\r\n") == "" and
                    s[i + 1].strip(" \t") != ""):
                z = i + 2
                while z < len(s) and s[z].strip(" \t") == "":
                    z += 1
                if (z < len(s) and (
                        s[z].endswith("\"") or s[z].endswith("'"))):
                    tail = ([s[i + 1].lstrip(" \t")] + s[i + 2:])
                    del(s[i + 1:])
                    s += ["+", "\\"]
                    s += tail
                    slen = len(s)
        # Remove "new" and "protect" since Python doesn't have these,
        # and translate some keywords:
        if s[i] == "new" or s[i] == "protect":
            tail = s[i + 1:]
            del(s[i:])
            s += tail
            slen -= 1
            continue
        if s[i] == "yes":
            s[i] = "True"
        elif s[i] == "no":
            s[i] = "False"
        elif s[i] == "none":
            s[i] = "None"
        i += 1

    return translate_map_constructors(s)

def translate_map_constructors(list s):
    cdef int i, slen
    i = 0
    slen = len(s)

    # Translate {->} map constructor:
    def try_handle_as_map(i):
        nonlocal s, slen
        if i >= slen or s[i] != "{":
            return 0
        starti = i

        # Special case of empty map first:
        if nextnonblank(s, i) == "->":
            assert(nextnonblank(s, i, no=2) == "}")
            s[:] = (s[:i] +
                ["(", "dict", "(", ")", ")"] +
                s[nextnonblankidx(s, i, no=2) + 1:])
            slen = len(s)
            i += 1
            return i - starti

        # Okay we're maybe in a map now. We'll see by checking
        # if we find any -> outside of brackets:
        start_idx = i
        bdepth = 0
        is_map = False
        might_have_nestings = False
        i += 1  # Go past '{'
        while i < slen and (s[i] != "}" or
                bdepth > 0):
            if s[i] in {"(", "{", "["}:
                if bdepth >= 0 and s[i] == "{":
                    might_have_nestings = True
                bdepth += 1
            elif s[i] in {")", "}", "]"}:
                bdepth -= 1
            if bdepth == 0 and s[i] == "->":
                # We're in a map!
                is_map = True
                s[i] = ":"  # Translate to python syntax.
            i += 1
        if i < slen:
            assert(s[i] == "}")
            i += 1
        if is_map and might_have_nestings:
            k = starti
            k += 1  # Go past '{'
            bdepth = 0
            while k < slen and (s[k] != "}" or
                    bdepth > 0):
                if s[k] in {"(", "{", "["}:
                    if bdepth >= 0 and s[k] == "{":
                        try_handle_as_map(k)
                        slen = len(s)
                    bdepth += 1
                elif s[k] in {")", "}", "]"}:
                    bdepth = max(0, bdepth - 1)
                k += 1
        if not is_map:
            return 0
        return i - starti
        
    # Map constructor loop:
    i = 0
    while i < slen:
        handled_len = try_handle_as_map(i)
        if handled_len == 0:
            i += 1
            continue
        slen = len(s)
        i += handled_len
    return s

def queue_module_neighbors(
        translate_file_queue,
        module_source_file_path, module_name, package_name,
        reason=None
        ):
    assert(type(translate_file_queue) == list)
    module_source_file_path = os.path.normpath(
        os.path.abspath(module_source_file_path))
    assert(module_source_file_path.endswith(".h64"))
    mod_base_dir = os.path.dirname(module_source_file_path)
    if not os.path.exists(mod_base_dir):
        def parent_dir_info(b):
            while not os.path.exists(b):
                b = os.path.normpath(os.path.join(b, ".."))
            return [b, os.listdir(b)]
        raise ValueError("somehow failed to access module "
            "base directory for module '" + module_name + "'" +
            (" @ '" + str(package_name) + "'" if
             package_name != None else "") + " with module file: " +
            module_source_file_path + " and base directory: " +
            mod_base_dir + " (first found parent dir info: " +
            str(parent_dir_info(mod_base_dir)) + ", " +
            "queue reason: '" + str(reason) + "')")
    for otherfile in os.listdir(mod_base_dir):
        otherfilepath = os.path.normpath(os.path.join(
            os.path.dirname(module_source_file_path), otherfile
        ))
        if (not otherfilepath.endswith(".h64") or
                os.path.isdir(otherfilepath) or
                otherfilepath.startswith("test_")):
            continue
        otherfilename = os.path.basename(
            otherfilepath.rpartition(".h64")[0]
        ) + ".py"
        otheraddsubmodule = [os.path.basename(
            otherfilepath.rpartition(".h64")[0])]
        if (otherfilename.rpartition(".py")[0] ==
                _splitpath(os.path.dirname(
                module_source_file_path))[-1]):
            otherfilename = "__init__.py"
            otheraddsubmodule = []
        otherfile_module = None
        if os.path.normpath(module_source_file_path).endswith(
                os.path.sep +
                module_name.split(".")[-1] +
                os.path.sep +
                module_name.split(".")[-1] + ".h64"):
            # Special case: target path must be bla/bla.h64
            # with code file matching folder, so the module
            # must be "bla" (not "bla.bla"). Hence, don't
            # strip off final module part:
            otherfile_module = (".".join(
                module_name.split(".") + otheraddsubmodule))
        else:
            # Target path is something like
            # bla/otherwordthanbla.h64 and
            # we want "otherwordthanbla" added:
            otherfile_module = (".".join(
                module_name.split(".")[:-1] +
                otheraddsubmodule))
        assert("/" not in otherfile_module)
        queue_file_if_not_queued(translate_file_queue,
            (otherfilepath, otherfilename,
            otherfile_module, os.path.dirname(
            module_source_file_path),
            package_name), reason="neighboring file to " +
            "imported module " + module_name)


def queue_file_if_not_queued(
        translate_file_queue, entry,
        reason=None
        ):
    assert(entry[2] != None and entry[2] != "")
    # Brief sanity check:
    source_path_parts = entry[0].replace("\\", "/").split("/")
    if (len(source_path_parts) >= 2 and
            source_path_parts[-1].rpartition(".h64")[0] ==
            source_path_parts[-2]):
        assert("__init__" in entry[1]), ("invalid "
            "queued entry that is main module file, "
            "but python file isn't __init__.py: " + str(entry))
    # Abort if already queued:
    for queue_item in translate_file_queue:
        if (os.path.normpath(queue_item[0]) ==
                os.path.normpath(entry[0])):
            return
    if DEBUGV.ENABLE and DEBUGV.ENABLE_QUEUE:
        print("translator.py: debug: queuing item: " +
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


class TranslateInfoScope:
    def __init__(self):
        self.module_name = None
        self.package_name = None
        self.parent_statements = []
        self.extra_indent = ""
        self.folder_path = ""
        self.project_info = None
        self.processed_imports = None
        self.translate_file_queue = None
        self.h64_local_global_simple_vars_consts = None
        self.orig_h64_imports = None
        self.orig_h64_globals = None
        self.paranoid = False
        self.global_init_func_code = dict()

    def copy(self):
        sc = TranslateInfoScope()
        sc.paranoid = self.paranoid
        sc.h64_local_global_simple_vars_consts = (
            list(self.h64_local_global_simple_vars_consts)
        )
        sc.module_name = self.module_name
        sc.package_name = self.package_name
        sc.parent_statements = list(self.parent_statements)
        sc.extra_indent = self.extra_indent
        sc.folder_path = self.folder_path
        sc.project_info = self.project_info
        sc.processed_imports = self.processed_imports
        sc.translate_file_queue = self.translate_file_queue
        sc.orig_h64_imports = self.orig_h64_imports
        sc.orig_h64_globals = self.orig_h64_globals
        sc.global_init_func_code = self.global_init_func_code
        return sc


def translate(s, sc):
    if sc.orig_h64_imports == None:
        assert(sc.orig_h64_globals == None)
        assert(sc.parent_statements is None or
            len(sc.parent_statements) == 0)
        assert(sc.processed_imports is None or
            len(sc.processed_imports) == 0)
        assert(type(s) == list)
        sc.h64_local_global_simple_vars_consts = (
            get_declared_local_globals_simple(s)
        )
        sc.orig_h64_imports = extract_all_imports(s)
        if sc.paranoid:
            assert(type(sc.orig_h64_imports) == list)
            for import_entry in sc.orig_h64_imports:
                assert(type(import_entry) == list and
                        len(import_entry) == 3 and
                        type(import_entry[0]) == str and
                        type(import_entry[1]) in {type(None), str} and
                        type(import_entry[2]) in {type(None), str}), (
                    "invalid import result: " + str(import_entry) +
                    " when processing module: " + str(sc.module_name)
                )
                assert(import_entry[0].strip() == import_entry[0])
                assert(len(import_entry[0]) > 0)
        try:
            sc.orig_h64_globals = get_global_names(
                s, error_on_duplicates=True
            )
        except ValueError as e:
            if not "syntax error" in str(e.args[0]).lower():
                raise e
            raise ValueError(
                "Error from get_global_names() for "
                "module \"" +
                sc.module_name + "\" in folder \"" +
                sc.folder_path + "\": " + str(e.args[0]))

    if (len(sc.parent_statements) == 0 and DEBUGV.ENABLE and
            DEBUGV.ENABLE_FILE_PATHS):
        assert(sc.module_name != "")
        print("translator.py: debug: translating " +
            "module \"" + sc.module_name + "\" in folder: " +
            sc.folder_path +
            (" (no package)" if sc.package_name is None else
             " (package: " + str(sc.package_name) + ")"))
    if sc.processed_imports is None:
        sc.processed_imports = {}
    sc.folder_path = os.path.normpath(os.path.abspath(
        sc.folder_path))
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
        indent = sc.extra_indent
        if is_whitespace_token(statement[0]):
            indent += statement[0]
            statement = statement[1:]
            while is_whitespace_token(statement[0]):
                statement = statement[1:]
        if statement[0] == "var" or statement[0] == "const":
            statement_cpy = list(statement)

            # Check if this is a global var declaration:
            is_global = (len(sc.parent_statements) == 0)
            allow_global_simple_vars_access_list = None
            if is_global:
                allow_global_simple_vars_access_list = list(
                    sc.h64_local_global_simple_vars_consts
                )
            is_nonisolated_or_nonpure = (
                is_isolated_pure_assign(statement,
                    debug=is_global,
                    allow_these_local_globals=\
                        allow_global_simple_vars_access_list)
            )

            # Hack: for various reasons, easiest to just nuke
            # unbracketed line breaks after commas:
            bdepth = 0
            j = 0
            while j < len(statement):
                if statement[j] == "," and bdepth == 0:
                    # Nuke all whitespace after this comma:
                    while (j + 1 < len(statement) and
                            statement[j + 1].strip(" \r\n\t") == ""):
                        statement = (statement[:j + 1] +
                            statement[j + 2:])
                elif statement[j] in {"(", "[", "{"}:
                    bdepth += 1
                elif statement[j] in {")", "]", "}"}:
                    bdepth -= 1
                j += 1

            # Collect identifiers this var/const declares:
            identifiers = []
            i = 1
            while True:
                while (i < len(statement) and
                        is_whitespace_token(statement[i])):
                    i += 1
                assert(is_identifier(statement[i]))
                identifiers.append(make_valid_identifier(
                    statement[i], sc=sc
                ))
                i += 1  # Go past identifier.
                while (i < len(statement) and
                        is_whitespace_token(statement[i])):
                    i += 1
                if (i < len(statement) and statement[i] == "protect"):
                    i += 1
                    while (i < len(statement) and
                            is_whitespace_token(statement[i])):
                        i += 1
                if i >= len(statement) or statement[i] == "=":
                    assert(i >= len(statement) or statement[i] == "=")
                    break
                assert(statement[i] == ","), ("Bogus var statement: " +
                    str(statement) + " in module " + str(sc.module_name))
                i += 1  # Past comma.
                continue  # Get following identifiers!
            if i < len(statement):
                i += 1  # Past "=".

            # Collect all the assigned values:
            value_exprs = []
            z = 0
            while z < len(identifiers) and i < len(statement):
                # Find end of next assigned expression:
                bracket_depth = 0
                value_start = i
                while i < len(statement) and (
                        statement[i] != "," or
                        bracket_depth > 0):
                    if statement[i] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif statement[i] in {")", "]", "}"}:
                        bracket_depth -= 1
                    i += 1

                # Translate it over:
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                value_exprs.append(
                    translate_expression_tokens(
                    statement[value_start:i], new_sc))
                gotnonblank = False
                for value_token in value_exprs[-1]:
                    if not is_whitespace_token(value_token):
                        gotnonblank = True
                assert(gotnonblank), ("must have non-blank " +
                    "assigned value for var statement")

                # Hack to make assigned sets work:
                if (len(value_exprs[-1]) > 0 and
                        firstnonblank(value_exprs[-1]) == "{"):
                    value_exprs[-1] = apply_make_set_call(
                        value_exprs[-1]
                    )

                z += 1  # Go to next assigned value.
                if i >= len(statement):
                    break
                assert(statement[i] == ",")
                i += 1
                continue

            # Some error checking:
            if z != 0 and z != len(identifiers):
                raise ValueError("mismatched var statement " +
                    "with identifiers " +
                    (", ".join(identifiers)) + " " +
                    (("in " + sc.module_name + (" in " + sc.package_name
                     if sc.package_name != None else "")) if
                     sc != None else "") + ": "
                    "wrong assigend value count " + str(z))
            if i < len(statement):
                raise ValueError("can't have trailing " +
                    "tokens for var statement with identifiers " +
                    (", ".join(identifiers)) + " " +
                    (("in " + sc.module_name + (" in " + sc.package_name
                     if sc.package_name != None else "")) if
                     sc != None else "") + ": " + str(statement[i:]))

            # Finally, generate the code:
            z = -1
            for idf in identifiers:
                z += 1
                value_expr = (value_exprs[z] if
                    len(value_exprs) > 0 else None)
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                pstatement = ([idf + "="] + ["("] + (
                    value_expr if value_expr != None else ["None"]) +
                    [")", "\n"])
                direct_parent_first_tok = None
                direct_parent_2nd_tok = None
                direct_parent_2nd_tok_idx = None
                if len(sc.parent_statements) > 0:
                    direct_parent_first_tok = (
                        "".join(sc.parent_statements[0][:1]))
                    nonblankidx = nextnonblankidx(
                        sc.parent_statements[0], 0)
                    if nonblankidx != None and nonblankidx > 0:
                        direct_parent_2nd_tok_idx = nonblankidx
                        direct_parent_2nd_tok = (
                            "".join(sc.parent_statements[0][
                                nonblankidx:nonblankidx + 1]))
                type_name = None
                type_module = None
                type_package = None
                if direct_parent_first_tok == "type":
                    type_name = nextnonblank(sc.parent_statements[0], 0)
                    type_module = sc.module_name
                    type_package = sc.package_name
                elif (direct_parent_first_tok == "extend" and \
                        direct_parent_2nd_tok == "type"):
                    type_info = parse_type_import_ref(
                        sc.parent_statements[0],
                        nextnonblankidx(sc.parent_statements[0],
                            direct_parent_2nd_tok_idx),
                        sc=sc, is_func=False,
                        purpose="var statement inside 'extend type'")
                    type_name = type_info["type-name"]
                    type_module = type_info["modpath"]
                    type_package = type_info["package"]
                if type_name != None:
                    ensure_type(type_name, type_module,
                            type_package, from_type_stmt=False).\
                        init_code += ("\n" + indent +
                            ("\n" + indent).join((
                                "self." +
                                untokenize(pstatement)
                            ).splitlines()))
                    continue
                if not is_global or is_nonisolated_or_nonpure:
                    result += indent + untokenize(pstatement) + "\n"
                else:
                    # This might access something that accesses a
                    # different module (e.g. indirectly via call, too).
                    # Python may explode unless we defer this until after
                    # all import processing of python is done:
                    key = (sc.module_name, sc.package_name)
                    assert(key[0] != None)
                    if not key in sc.global_init_func_code:
                        sc.global_init_func_code[key] = ""
                    sc.global_init_func_code[key] += ("    " +
                        "global " + idf + "\n")
                    sc.global_init_func_code[key] += ("    " +
                        "\n    ".join(untokenize(pstatement).
                            splitlines()) + "\n")
                    # We still should reserve the names as globals,
                    # so in the original spot, assign 'None':
                    result += indent + idf + " = None\n"
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
            rescue_block_content_first = []
            rescue_block_content_last = []
            rescue_error_label_name = []
            rescue_error_types_first = []
            rescue_error_types_last = []
            finally_block_content_first = -1
            finally_block_content_last = -1
            while (j < len(statement) and
                    statement[j] == "rescue"):
                j += 1  # Past 'rescue' keyword.
                while (j < len(statement) and
                         statement[j].strip(" \t\r\n") == ""):
                    j += 1
                assert(j < len(statement) and
                       statement[j] != "as")
                rescue_error_types_first.append(j)
                hadnonblank = False
                bracket_depth = 0
                while (j < len(statement) and
                        (((statement[j] != "{" or
                        not hadnonblank) and
                        statement[j] != "as") or
                        bracket_depth > 0)):
                    if statement[j] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif statement[j] in {")", "]", "}"}:
                        bracket_depth -= 1
                    if statement[j].strip(" \r\t\b"):
                        hadnonblank = True
                    j += 1
                rescue_error_types_last.append(j - 1)
                while (rescue_error_types_last[-1] >
                        rescue_error_types_first[-1] and
                        statement[rescue_error_types_last[-1]].
                        strip(" \r\n\t") == ""):
                    rescue_error_types_last[-1] = (
                        rescue_error_types_last[-1] - 1
                    )
                assert(statement[j] == "{" or
                    statement[j] == "as")
                if statement[j] == "as":
                    j += 1
                    while (j < len(statement) and
                            statement[j].strip(" \t\r\n") == ""):
                        j += 1
                    assert(is_identifier(statement[j]))
                    rescue_error_label_name.append(statement[j])
                    j += 1
                    while (j < len(statement) and
                            statement[j].strip(" \t\r\n") == ""):
                        j += 1
                else:
                    rescue_error_label_name.append(None)
                assert(statement[j] == "{")
                j += 1  # Go past the opening '{'
                rescue_block_content_first.append(j)
                bracket_depth = 0
                while (j < len(statement) and
                        (statement[j] != "}" or
                        bracket_depth > 0)):
                    if statement[j] in {"(", "[", "{"}:
                        bracket_depth += 1
                    elif statement[j] in {")", "]", "}"}:
                        bracket_depth -= 1
                    j += 1
                rescue_block_content_last.append(j - 1)
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
            rescued_errors_expr = []
            rescue_block_code = []
            new_sc = sc.copy()
            new_sc.parent_statements += [statement_cpy]
            do_block_code = translate(
                    untokenize(statement[
                        do_block_content_first:
                        do_block_content_last+1
                    ]), new_sc
                )
            z = -1
            for block_content_first in rescue_block_content_first:
                z += 1
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                rescue_block_code.append(translate(
                    untokenize(statement[
                        rescue_block_content_first[z]:
                        rescue_block_content_last[z]+1
                    ]), new_sc))
                rescued_errors_tokens = (statement[
                    rescue_error_types_first[z]:
                    rescue_error_types_last[z]+1])
                if rescued_errors_tokens == ["any"]:
                    rescued_errors_tokens = ["Error"]
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
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                rescued_errors_expr.append(
                    translate_expression_tokens(
                        rescued_errors_tokens,
                        new_sc
                    ))
                assert(rescued_errors_expr[-1] != None)
            finally_block_code = None
            if finally_block_content_first >= 0:
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                finally_block_code = translate(
                    untokenize(statement[
                        finally_block_content_first:
                        finally_block_content_last+1
                    ]), new_sc)
            result += (indent + "try:\n")
            result += do_block_code + "\n"
            result += (indent + "    pass\n")
            if (len(rescue_block_code) == 0 and
                    finally_block_code is None):
                result += (indent + "finally:\n")
                result += (indent + "    pass\n")
            else:
                z = -1
                for block in rescue_block_code:
                    z += 1
                    assert(rescued_errors_expr[z] != None)
                    result += (indent + "except " +
                        untokenize(rescued_errors_expr[z]))
                    if rescue_error_label_name[z] != None:
                        result += (" as " +
                            rescue_error_label_name[z])
                    result += ":\n"
                    result += rescue_block_code[z] + "\n"
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
            new_sc = sc.copy()
            new_sc.parent_statements += [statement_cpy]
            assigned_expr = translate_expression_tokens(
                statement[assign_obj_first:
                    assign_obj_last+1],
                new_sc)
            new_sc = sc.copy()
            new_sc.parent_statements += [statement_cpy]
            with_block_code = translate(
                untokenize(statement[
                    with_block_first:
                    with_block_last+1]), new_sc)
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
                if not statement[j] in ("if", "while", "elseif",
                        "else", "for"):
                    raise ValueError("Syntax error or problem " +
                        (("in " + sc.module_name + (" in " + sc.package_name
                         if sc.package_name != None else "")) if
                         sc != None else "") + ": parsing " +
                        str(statement[0]) + " statement, and got " +
                        "unexpected token: " + str(statement[j]))
                bracket_depth = 0
                lastnonblanktoken = ""
                hadnonwhitespace = False
                i = j + 1
                while i < len(statement) and (
                        statement[i] != "{" or bracket_depth > 0 or
                        (statement[j] != "else" and (
                            not hadnonwhitespace or
                            lastnonblanktoken == "in" or
                            is_h64op_with_righthand(
                            lastnonblanktoken)))):
                    if (bracket_depth == 0 and
                            statement[i] in {",", ":"}):
                        assert(i < len(statement) and statement[i] == "{"), \
                            ("in module " + sc.module_name +
                            (" in " + sc.package_name if
                            sc.package_name != None else "") +
                            ", found invalid '" + str(statement[i]) +
                            "' in " + statement[j] + " condition")
                    if statement[i] in {"{", "(", "["}:
                        bracket_depth += 1
                    elif statement[i] in {"}", ")", "]"}:
                        bracket_depth -= 1
                        if bracket_depth < 0:
                            break
                    if statement[i].strip(" \t\r\n") != "":
                        hadnonwhitespace = True
                        lastnonblanktoken = statement[i]
                    i += 1
                assert(i < len(statement) and statement[i] == "{"), \
                    ("in module " + sc.module_name +
                    (" in " + sc.package_name if
                    sc.package_name != None else "") +
                    ", failed finding '{' for \"" + str(statement[j]) +
                    "\" inner block, instead reached " +
                    ("end of stream: " if i >= len(statement) else
                    "character '" + str(statement[i]) + "': ") +
                    str(statement))
                statement[i] = ":"
                begin_content_idx = i + 1
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                condition = (
                    translate_expression_tokens(statement[j + 1:i],
                        new_sc))
                assert("as_str" not in condition)
                assert(sublist_index(condition, [".", "len"]) < 0)
                bracket_depth = 0
                while (i < len(statement) and
                        (statement[i] != "}" or bracket_depth > 0)):
                    if statement[i] in {"{", "(", "["}:
                        bracket_depth += 1
                    elif statement[i] in {"}", ")", "]"}:
                        bracket_depth -= 1
                    i += 1
                if (i >= len(statement) or
                        statement[i] != "}"):
                    raise ValueError("Broken " +
                        str(statement[j]) +
                        " statement in module " +
                        sc.module_name + ("" if sc.package_name is None
                        else " (pkg: " + sc.package_name + ")") +
                        " without properly closing code block: " +
                        str(statement[j:j + 20]))
                content = statement[
                    begin_content_idx:i
                ]
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                content_code = translate(
                    untokenize(content), new_sc)
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
            assert(len(sc.parent_statements) == 0)
            assert(len(statement) >= 2 and statement[1].strip() == "")
            i = 2
            while i + 2 < len(statement) and statement[i + 1] == ".":
                i += 2
            import_module = "".join([
                part.strip() for part in statement[1:i + 1]
                if part.strip() != ""
            ])
            default_import_package = sc.package_name
            if default_import_package is None:
                default_import_package = sc.project_info.package_name
            import_package = default_import_package
            i += 1
            while i < len(statement) and statement[i].strip() == "":
                i += 1
            import_rename = None
            if i < len(statement) and statement[i] == "as":
                nexti = nextnonblankidx(statement, i)
                assert(nexti < len(statement) and
                       is_identifier(statement[nexti]))
                import_rename = statement[nexti]
                i = nextnonblankidx(statement, nexti, no=2)
            if i < len(statement) and statement[i] == "from":
                i += 1
                while i < len(statement) and statement[i].strip() == "":
                    i += 1
                import_package = statement[i]
                while i + 2 < len(statement) and statement[i + 1] == ".":
                    import_package += "." + statement[i + 2]
                    i += 2
            in_orig_imports = False
            for orig_h64_import in sc.orig_h64_imports:
                if (orig_h64_import[2] == import_module and
                        (orig_h64_import[1] == import_package or
                        (orig_h64_import[1] == None and
                            import_package ==
                            default_import_package))):
                    in_orig_imports = True
            if not in_orig_imports:
                raise RuntimeError(
                    "encountered import statement for " +
                    str((import_module, import_package)) +
                    ", but it's not listed in orig_h64_imports??? "
                    "here are the imports: " + str(sc.orig_h64_imports))
            target_path = import_module.replace(".", os.path.sep) + ".h64"
            target_filename = import_module.split(".")[-1] + ".py"
            append_code = ""
            python_module = mpath(import_module, sep=".")
            package_python_subfolder = sc.project_info.\
                get_package_subfolder(import_package,
                for_output=True)
            package_source_subfolder = sc.project_info.\
                get_package_subfolder(import_package,
                for_output=False)
            if (len(import_module.split(".")) >= 2 and
                    import_module.split(".")[-1] ==
                    import_module.split(".")[-2]):
                # Suspicious, something like mod.mod. This is only valid
                # if there's a folder mod/mod/, NOT for mod/mod.h64.
                assert(os.path.exists(
                    os.path.join(os.path.abspath(
                    sc.project_info.repo_folder),
                    package_source_subfolder,
                    import_module.replace(".", os.path.sep) +
                    os.path.sep))), (
                    "module import seems invalid and doesn't reflect "
                    "folder structure: " + str(import_module))
            if (package_python_subfolder != None and
                    len(package_python_subfolder) > 0):
                if package_python_subfolder.endswith("/"):
                    package_python_subfolder = (
                        package_python_subfolder[:-1])
                python_module = mpath(package_python_subfolder +
                    "/" + python_module).replace("/", ".")
                module_basename = import_module.split(".")[0]
                rename_pair = None
                if import_rename != None:
                    module_basename = import_rename
                    rename_pair = (import_module, import_rename)
                append_code += ("; ((" + module_basename +
                    " := _translator_runtime_helpers." +
                    "_ModuleObject(" +
                    as_escaped_code_string(
                        import_module.split(".")[0]) + "," +
                    (as_escaped_code_string(import_package) if
                     import_package != None else "None") +
                    ", renamed=" + str(rename_pair) + ")) if (\"" +
                    module_basename + "\" not in locals() and \"" +
                    module_basename + "\" not in globals()) else None)")
            if len(package_source_subfolder) > 0:
                target_path = os.path.normpath(
                    os.path.join(os.path.abspath(
                    sc.project_info.repo_folder),
                    package_source_subfolder, target_path))
            else:
                target_path = os.path.normpath(
                    os.path.join(os.path.abspath(
                    sc.project_info.code_folder), target_path))
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
            nonremapped_use_example = None
            found_remapped_use = False
            if DEBUGV.ENABLE_REMAPPED_USES:
                print("translator.py: debug: scanning \"" +
                    "import " + import_module +
                    (" from " + import_package
                    if import_package != None else "") + "\" in " +
                    "module " + str(sc.module_name) + " for " +
                    "remapped uses...")
            import_module_elements = import_module.split(".")
            assert(len(import_module_elements) >= 1)
            token_len = len(tokens)
            i = 0
            while i < token_len:
                if not is_identifier(tokens[i]):
                    i += 1
                    continue
                if prevnonblank(tokens, i) in {"import", "from", "."}:
                    i += 1
                    continue
                # See if this exact token matches an import, and if it's ours:
                (match_import_module, match_package,
                 match_item, match_tokens) = find_matching_remap_module(
                    s, i, sc
                )
                if (match_import_module != import_module or
                        match_package != import_package):
                    i += 1
                    continue
                remapped_uses_key = import_module
                if import_package != None:
                    remapped_uses_key += "@" + import_package
                if remapped_uses_key not in remapped_uses:
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print("translator.py: debug: found " +
                            "non-remapped use (no remaps for " +
                            "module " + str(remapped_uses_key) +
                            "): " + str(
                            tokens[i:i +
                            len(import_module_elements) + 10]))
                    if nonremapped_use_example == None:
                        nonremapped_use_example =\
                            str(tokens[i:i + 5]) + "..."
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
                    if nonremapped_use_example == None:
                        nonremapped_use_example =\
                            str(tokens[i:i + 5]) + "..."
                    if DEBUGV.ENABLE_REMAPPED_USES:
                        print(
                            "translator.py: debug: found "
                            "non-remapped use: " +
                            str(tokens[i:i +
                                len(import_module_elements) + 10])
                        )
                else:
                    found_remapped_use = True
                i += 1
            del(i)
            if DEBUGV.ENABLE_REMAPPED_USES:
                print("translator.py: debug: completed " +
                    "scanning import.")

            # Add import:
            sc.processed_imports[import_module] = {
                "rename": import_rename,
                "package": import_package,
                "module": import_module,
                "python-module": mpath(python_module, sep="."),
                "path": target_path,
                "target-filename": target_filename,
            }

            # Skip import code if it only has remapped uses:
            if not found_nonremapped_use and found_remapped_use:
                if DEBUGV.ENABLE_REMAPPED_USES:
                    print("translator.py: debug: hiding " +
                        "import since all uses are remapped: " +
                        str(import_module) + ("" if
                        import_package is None else
                        "@" + import_package))
                sc.processed_imports[import_module]["python-module"] = (
                    None  # since it wasn't actually imported
                )
                continue

            # Add translated import code:
            result += ("import " + mpath(python_module, sep=".") +
                append_code + "\n")
            queue_reason = ("imported from " +
                "module " + str(sc.module_name) + (
                "" if sc.package_name is None else
                    "@" + sc.package_name) +
                    " with " + (("non-remapped uses, like " +
                        str(nonremapped_use_example)) if
                        found_nonremapped_use else
                        "zero remapped uses"))
            queue_file_if_not_queued(sc.translate_file_queue,
                (target_path, target_filename,
                import_module, os.path.dirname(target_path),
                import_package), reason=queue_reason)
            queue_module_neighbors(
                sc.translate_file_queue, target_path,
                import_module, import_package, reason=queue_reason)
            continue
        elif statement[0] == "enum":
            statement_cpy = list(statement)
            nameidx = nextnonblankidx(statement, 0)
            assert(nameidx >= 0)
            enumname = statement[nameidx]
            assert(is_identifier(enumname))
            i = nameidx + 1
            while i < len(statement) and statement[i] != "{":
                i += 1
            assert(i < len(statement) and statement[i] == "{")
            i += 1  # Go past '{'.

            used_values = set()
            enum_map = dict()
            enum_list = []
            while i < len(statement) and statement[i] != "}":
                nexti = nextnonblankidx(statement, i)
                if nexti < 0:
                    break
                i = nexti
                enum_valname = None
                enum_valnum = None
                if is_identifier(statement[i]):
                    enum_valname = statement[i]
                    nexti = nextnonblankidx(statement, i)
                    if nexti >= 0 and statement[nexti] == "=":
                        i = nexti
                        nexti = nextnonblankidx(statement, i)
                        if is_number_token(statement[i]):
                            enum_valnum = int(statement[i])
                        i = nexti + 1
                    else:
                        i += 1
                else:
                    continue
                assert(enum_valname not in enum_map)
                assert(enum_valnum is None or
                    enum_valnum not in used_values)
                enum_map[enum_valname] = enum_valnum
                if enum_valnum is not None:
                    used_values.add(enum_valnum)
                enum_list.append([enum_valname, enum_valnum])
                continue
            assert(i < len(statement) and statement[i] == "}")
            count_from = 0
            i = 0
            while i < len(enum_list):
                if enum_list[i][1] == None:
                    count_from += 1
                    while count_from in used_values:
                        count_from += 1
                    enum_list[i][1] = count_from
                    enum_map[enum_list[i][0]] = count_from
                    used_values.add(count_from)
                else:
                    count_from = enum_list[i][1]
                i += 1
            result += ("class " +
                enumname + ":\n")
            result += ("    @staticmethod\n")
            result += ("    def num_label(x):\n")
            for enum_entry in enum_list:
                result += ("        " +
                    "if (x == " + str(enum_entry[1]) + "):\n")
                result += ("        " +
                    "    return \"" + str(enum_entry[0]) + "\"\n")
            result += ("        raise " +
                "_translator_runtime_helpers._ValueError(\"" +
                "Not a known enum value.\")\n")
            for enum_entry in enum_list:
                result += (enum_entry[0] + " = " +
                    str(enum_entry[1]) + "\n")
            continue
        elif statement[0] == "func" or (
                statement[0] == "extend" and
                nextnonblank(statement, 0) == "func"):
            statement_cpy = list(statement)
            is_extend = (statement[0] == "extend")
            interesting_nonlocals = (
                get_func_interesting_nonlocals(
                    statement, sc.parent_statements,
                    debug=debug
                ))
            nameidx = nextnonblankidx(statement, 0)
            assert(nameidx >= 0)
            if is_extend:
                nameidx = nextnonblankidx(statement, nameidx)

            # Catch this programming error: type bla { func bli { } }
            for pstatement in sc.parent_statements:
                if (len(pstatement) > 0 and
                        pstatement[0] == "type"):
                    raise ValueError("Syntax error in " +
                        sc.module_name + (" in " + sc.package_name
                        if sc.package_name != None else "") + ": " +
                        "found invalid \"func\" nested in \"type\"")

            # First, see what globals Python might need a hint:
            function_outer_scope_names = (
                get_names_defined_in_func(statement_cpy,
                    is_anonymous_inline=False))
            tell_python_about_globals = []
            for entry in sc.orig_h64_globals:
                if (sc.orig_h64_globals[entry]["type"]
                        in {"var"} and
                        not entry in function_outer_scope_names):
                    # For some operations like +=, Python
                    # won't believe us we're using a global
                    # unless we explicitly list it:
                    tell_python_about_globals.append(entry)

            # Also, get any names that might be relevant if this
            # is a type func attribute expanded from outside:
            undefined_names = get_undefined_uses_in_func(
                statement, ignore_later_generated=True,
            )
            globals_accessed = set()
            for undefined_name in undefined_names:
                if (undefined_name in sc.orig_h64_globals and
                        sc.orig_h64_globals[undefined_name]["type"]
                            != "import"):
                    globals_accessed.add(undefined_name)

            # Make sure the name of the func is valid:
            statement[nameidx] = make_valid_identifier(
                statement[nameidx], sc=sc)
            k = nameidx + 1
            while k + 1 < len(statement) and statement[k] == ".":
                k += 1
                statement[k] = make_valid_identifier(
                    statement[k], sc=sc)
                k += 1

            # Transform to "def" and see where content begins:
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
                print("translator.py: error: " +
                    "got invalid func statement " +
                    "without closing bracket:", file=sys.stderr)
                print(untokenize(statement_cpy), file=sys.stderr)
                print("translator.py: info: " +
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
            type_info = parse_type_import_ref(
                statement, nameidx, sc=sc, is_func=True,
                purpose="resolving extended type of " +
                    ("'extend func' statement" if is_extend else
                    "'func' statement")
            )
            type_module = type_info["modpath"]
            type_python_module = type_info["python-module"]
            type_package = type_info["package"]
            type_name = type_info["type-name"]
            type_is_external = type_name != None and (
                type_info["modpath"] != sc.module_name or
                type_info["package"] != sc.package_name
            )
            prefix_globals_code = ""
            if type_is_external and len(globals_accessed) > 0:
                #print("GOT EXTERNAL TYPE FUNC: " + str((
                #    type_info["func-name"],
                #    undefined_names,
                #    sc.orig_h64_globals.keys(),
                #    globals_accessed, type_info["modpath"],
                #    type_info["package"],
                #    sc.module_name,
                #    sc.package_name)))
                ind = (indent + "    " +
                    ("    " if type_name != None else ""))
                for gaccessed in globals_accessed:
                    prefix_globals_code += (ind + gaccessed + " = "
                        "_translator_runtime_helpers."
                        "_global_module_registry[" +
                            as_escaped_code_string(
                                sc.module_name +
                                "@" + str(sc.package_name)
                            ) + "]." + (
                                gaccessed
                            ) + "\n")
            name = type_info["func-name"]
            register_as_modinit = (
                type_name == None and (
                name == "modinit" or
                name.startswith("modinit_"))
            )
            start_arguments_idx = type_info["index-after"]
            while (start_arguments_idx < len(statement) and
                    statement[start_arguments_idx].
                        strip(" \t\r\n") == ""):
                start_arguments_idx += 1
            argument_tokens = ["(", ")"]
            if statement[start_arguments_idx] == "(":
                # Extract the arguments:
                bdepth = 1
                k = start_arguments_idx + 1
                while statement[k] != ")" or bdepth > 1:
                    if statement[k] == "(":
                        bdepth += 1
                    elif statement[k] == ")":
                        bdepth -= 1
                    k += 1
                assert(statement[k] == ")")
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                argument_tokens = translate_expression_tokens(
                    statement[start_arguments_idx:k + 1],
                    new_sc)
            assert("_remapped_os" not in contents)

            # Prepare the final args and code to be spit out:
            new_sc = sc.copy()
            new_sc.parent_statements += [statement_cpy]
            new_sc.extra_indent += ("    "
                if type_name is not None else "")
            translated_contents = translate(
                untokenize(contents), new_sc)
            (cleaned_argument_tokens,
                extra_init_code) = separate_func_keyword_arg_code(
                    argument_tokens, indent=(indent + "    " +
                    ("    " if type_name is not None else "")))
            inner_indent = (get_indent(
                extra_init_code + "\n" +
                translated_contents + "\n"))
            if inner_indent is None:
                inner_indent = indent + "    "
            inner_code = (prefix_globals_code +
                extra_init_code + "\n" +
                translated_contents + "\n")
            if len(tell_python_about_globals) > 0:
                inner_code = (inner_indent +
                    "global " + ",".join(
                    tell_python_about_globals) +
                    "\n" + inner_code)
            if len(interesting_nonlocals) > 0:
                inner_code = (inner_indent +
                    "nonlocal " + ",".join(
                    [make_valid_identifier(nl)
                    for nl in interesting_nonlocals]) +
                    "\n" + inner_code)
            inner_code += (inner_indent + "pass\n")
            if type_name is None:
                assert(not is_extend)
                result += (indent + "def " + name +
                    untokenize(cleaned_argument_tokens) + ":\n")
                result += inner_code
                if register_as_modinit:
                    result += (
                        "_translator_runtime_helpers.regmodinit(" +
                        name + ")"
                    )
            else:
                assert(type_module != None)
                regtype = ensure_type(
                    type_name, type_module, type_package,
                    from_type_stmt=False
                )
                actual_name = name
                if not name in regtype.funcs:
                    regtype.funcs[name] = {"name": name}
                if is_extend:
                    actual_name = ("__extends__" + name +
                        "__id_" + str(uuid.uuid4()).replace("-", ""))
                    if not actual_name in regtype.funcs:
                        regtype.funcs[actual_name] = {"name": actual_name}
                    regtype.funcs[name]["ever-extended"] = True
                    ext_list = []
                    if "extend-names" in regtype.funcs[name]:
                        ext_list = regtype.funcs[name]["extend-names"]
                    ext_list.append(actual_name)
                    regtype.funcs[name]["extend-names"] = ext_list
                regtype.funcs[actual_name]["arguments"] = \
                    cleaned_argument_tokens
                regtype.funcs[actual_name]["code"] = inner_code
                if not "ever-extended" in regtype.funcs[actual_name]:
                    regtype.funcs[actual_name]["ever-extended"] = False
            continue
        elif statement[0] == "type" or (statement[0] == "extend"
                and nextnonblank(statement, 0) == "type"):
            statement_cpy = list(statement)
            namelbl = None
            is_extend = (statement[0] == "extend")
            debug = False

            i = 0
            if not is_extend:
                nameidx = nextnonblankidx(statement, 0)

                # Make sure the name of the type is valid:
                statement[nameidx] = make_valid_identifier(
                    statement[nameidx], sc=sc)
                namelbl = statement[nameidx]

                # Forward past name:
                i = nameidx
                while i < len(statement) and (
                        statement[i] != "{" and
                        statement[i] != "base"):
                    i += 1
            else:
                i = nextnonblankidx(statement, 0)
                assert(statement[i] == "type")
            type_package = sc.package_name
            type_module = sc.module_name
            ext_tokens = None
            if is_extend or (i < len(statement) and
                    statement[i] == "base"):
                ext_tokens = []
                assert(not is_extend or statement[i] == "type")
                i = nextnonblankidx(
                    statement, i)  # Past 'base' or 'extend' keyword.
                assert(i < len(statement))
                assert(not is_extend or statement[i] != "type")
                start_idx = i
                type_info = parse_type_import_ref(statement, i, sc=sc,
                    debug=debug,
                    purpose="resolving extended type of " +
                        ("'extend type' statement" if is_extend else
                         "'base' of 'type' statement") +
                        ", statement: " + str(statement[0:5]) + "...")
                if is_extend:
                    type_module = type_info["modpath"]
                    type_python_module = type_info["python-module"]
                    type_package = type_info["package"]
                    namelbl = type_info["type-name"]
                i = type_info["index-after"]
                ext_tokens = type_info["raw-tokens"]
                ext_clean = []
                for ew in ext_tokens:
                    if ew.strip(" \r\n\t") == "":
                        continue
                    ext_clean.append(ew.strip(" \r\n\t"))
                new_sc = sc.copy()
                new_sc.parent_statements += [statement_cpy]
                if is_extend:
                    assert(len(ext_clean) >= 1)
                    namelbl = make_valid_identifier(
                        ext_clean[-1], sc=sc)
                ext_tokens = translate_expression_tokens(
                    ext_clean, new_sc)
            i += 1  # Go past '{' token.
            assert(statement[-1] == "}")
            contents = (
                statement[i:-1]
            )
            ensure_type(
                namelbl, type_module, type_package,
                extends_tokens=(ext_tokens),
                from_type_stmt=(not is_extend))
            new_sc = sc.copy()
            new_sc.parent_statements += [statement_cpy]
            new_sc.extra_indent += "    "
            translated_contents = translate(
                untokenize(contents), new_sc)
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
        new_sc = sc.copy()
        new_sc.parent_statements += [list(statement)]
        result += indent + untokenize(translate_expression_tokens(
            statement, new_sc, is_assign_stmt=(assign_token_idx >= 0),
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


def get_func_interesting_nonlocals(st, parent_sts, debug=False):
    if firstnonblank(st) != "func" and (
            firstnonblank(st) != "extend" or
            nextnonblank(st, firstnonblankidx(st)) != "func"):
        raise ValueError("meant to be used on funcs")
    current_inner_vars_all = statement_declared_identifiers(
        st, recurse=True
    )
    collect = set()
    i = len(parent_sts)
    while i - 1 >= 0:
        i -= 1
        if firstnonblank(parent_sts[i]) == "func":
            if debug:
                print("translator.py: debug: Collecting "
                    "vars from: " + str(parent_sts[i:i+30])[:1000])
            collect = collect.union(
                set(statement_declared_identifiers(
                parent_sts[i],
                exclude_direct_func_name=True)))
            if debug:
                print("translator.py: debug: Collected vars "
                    "so far: " + str(collect))
    result = []
    for varname in list(collect):
        if not varname in current_inner_vars_all:
            result.append(varname)

    if False:
        # Extensive debug info:
        print("get_interesting_nonlocals(): on: " + str(st))
        print("INNER: " + str(current_inner_vars))
        print("OUTER: " + str(collect))
        print("PARENTS:\n")
        parent_no = 0
        for p in parent_sts:
            parent_no += 1
            print("PARENT #" + str(parent_no) +
                  "/" + str(len(parent_sts)))
            print(untokenize(p))
            print("PARENT IDENTIFIERS: " + str(
                statement_declared_identifiers(
                p, exclude_direct_func_name=True)))
        print("RESULT: " + str(result))
    return result


def locate_repo_folder(startpath, repo_dir_override=None):
    if repo_dir_override != None:
        repo_dir_override = os.path.normpath(os.path.abspath(
            repo_dir_override
        ))
    startpath = os.path.normpath(os.path.abspath(startpath))
    if (not os.path.isfile(startpath) or
            not startpath.endswith(".h64")):
        raise ValueError("invalid start path")
    modname = (os.path.basename(startpath).
        rpartition(".h64")[0].strip())
    assert(modname != "")
    startpath = os.path.dirname(startpath)

    repo_dir = startpath
    while True:
        if (repo_dir_override != None and
                repo_dir_override ==
                os.path.normpath(repo_dir)):
            break
        repo_folder_files = os.listdir(repo_dir)
        if ("horse_modules" in repo_folder_files or
                ".git" in repo_folder_files) and \
                repo_dir_override is None:
            break
        if ("horp.conf" in repo_folder_files and
                not os.path.isdir(os.path.join(
                repo_dir, "horp.conf"))) and \
                repo_dir_override is None:
            contents = ""
            with open(os.path.join(repo_dir,
                    "horp.conf"), "r", encoding='utf-8') as f:
                contents = f.read()
            pkg_name = horp_ini_string_get_package_name(contents)
            if pkg_name != None:
                break
        # Normalize and make to absolute path, and clean it up:
        repo_dir = os.path.normpath(
            os.path.abspath(repo_dir)
        )
        if "windows" in platform.system().lower():
            repo_dir = repo_dir.replace("\\", "/")
        while "//" in repo_dir:
            repo_dir = repo_dir.replace("//", "/")
        if repo_dir.endswith("/") and (
                "windows" not in platform.system().lower() or
                len(repo_dir) > 3) and \
                repo_dir != "/":
            repo_dir = repo_dir[:-1]
        # Detect if we hit the root folder, and hence found nothing:
        if (("windows" in platform.system().lower() and
                len(repo_dir) == 3) or
                "windows" not in platform.system().lower() and
                repo_dir == "/"):
            raise RuntimeError("failed to detect repository folder")
        # Go up by one:
        modname = os.path.basename(
            os.path.normpath(os.path.normpath(
            repo_dir))) + "." + modname
        repo_dir = os.path.normpath(
            os.path.abspath(
            os.path.join(repo_dir, "..")))

    # Handle special case of mod/mod.h64:
    modname_parts = modname.split(".")
    if (len(modname_parts) >= 2 and
            modname_parts[-1] == modname_parts[-2]):
        # For 'bla/mod/mod.h64', the correct module is 'bla.mod'
        # (without the last component repeated):
        modname = modname.rpartition(".")[0]
    return (repo_dir, modname)


def run_translator_main():
    args = sys.argv[1:]
    single_file = False
    output_h64_file = False
    horse_mod_dir = None
    stdlib_dir = None
    output_py_file = False
    output_file_linenos = False
    target_file = None
    target_file_args = []
    keep_files = False
    paranoid = False
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
                print("    --debug-modload        "
                      "Show info on modules being loaded.")
                print("    --debug-python-output  "
                      "Show the generated python.")
                print("    --debug-queue          "
                      "Show info about queueing files.")
                print("    --help                 "
                      "Show this help text")
                print("    --horse-modules        "
                      "Load horse modules from different folder.")
                print("    --keep-files           "
                      "Keep folder with translated files to look at.")
                print("    --output-h64-file      "
                      "Don't run, just output half-translated .h64 file.")
                print("    --output-py-file       "
                      "Don't run, just output final translated Python.")
                print("    --single-file          "
                      "Don't treat as project but one-shot single file.")
                print("    --stdlib               "
                      "Override 'core.horse64.org' with given folder.")
                print("    --paranoid             "
                      "Do extra checking of internal operations.")
                print("    --version              "
                      "Print out program version")
                sys.exit(0)
            elif args[i] == "--as-test":
                run_as_test = True
            elif args[i] == "--single-file":
                single_file = True
            elif args[i] == "--horse-modules":
                if (i + 1 >= len(args) or
                        args[i + 1].startswith("-")):
                    print("translator.py: error: " +
                        "missing argument for --horse-modules")
                    sys.exit(1)
                horse_mod_dir = args[i + 1]
                i += 2
                continue
            elif args[i] == "--stdlib":
                if (i + 1 >= len(args) or
                        args[i + 1].startswith("-")):
                    print("translator.py: error: " +
                        "missing argument for "
                        "--stdlib")
                    sys.exit(1)
                stdlib_dir = args[i + 1]
                i += 2
                continue
            elif args[i] == "--paranoid":
                paranoid = True
            elif args[i] == "--output-h64-file":
                output_h64_file = True
            elif args[i] == "--output-py-file":
                output_py_file = True
            elif args[i] == "--output-h64-file-with-linenos":
                output_h64_file = True
                output_file_linenos = True
            elif args[i] == "--output-py-file-with-linenos":
                output_py_file = True
                output_file_linenos = True
            elif (args[i] == "--version" or args[i] == "-v" or
                    args[i] == "-V"):
                print("translator.py version " + VERSION)
                sys.exit(0)
            elif args[i] == "--override-package-name":
                if i + 1 >= len(args):
                    print("translator.py: error: " +
                        "missing argument for --override-package-name")
                    sys.exit(1)
                if ("." not in args[i + 1] or
                        args[i + 1].startswith("-") or
                        args[i + 1].endswith(".h64")):
                    print("translator.py: error: " +
                        "invalid name specified for " +
                        "--override-package-name")
                    sys.exit(1)
                overridden_package_name = args[i + 1]
                i += 2
                continue
            elif args[i] == "--debug-async":
                DEBUGV.ENABLE = True
                DEBUGV.ENABLE_ASYNC_OPS = True
            elif args[i] == "--debug-modload":
                DEBUGV.ENABLE = True
                DEBUGV.ENABLE_MODLOAD = True
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
                print("translator.py: warning: unknown " +
                    "option: " + args[i], file=sys.stderr)
        elif target_file is None:
            target_file = args[i]
            target_file_args = args[i + 1:]
            break
        i += 1
    if target_file is None:
        raise RuntimeError("please provide target file argument")
    target_file = os.path.abspath(target_file)
    original_target_file = target_file

    # Locate code repository:
    repo_dir_override = None
    if single_file:
        # Always treat the folder the file is in as repo.
        repo_dir_override = os.path.normpath(
            os.path.abspath(os.path.dirname(target_file))
        )
        if not os.path.exists(os.path.join(
                repo_dir_override, "horse_modules")) and \
                horse_mod_dir is None:
            horse_mod_dir = os.path.normpath(os.path.join(
                translator_py_script_dir, ".."
            ))
    (repo_dir, _) = locate_repo_folder(
        target_file, repo_dir_override=repo_dir_override
    )
    assert(os.path.exists(repo_dir))

    # See where we'll take horse_modules from:
    if (horse_mod_dir is None and
            os.path.exists(os.path.join(repo_dir,
            "horse_modules"))):
        horse_mod_dir = os.path.join(repo_dir, "horse_modules")

    # Assemble everything:
    assembled_dir = tempfile.mkdtemp(prefix="h64-project-run-copy-")
    try:
        if DEBUGV.ENABLE:
            print("translator.py: debug: " +
                "path configuration: " + str({"repo dir":
                repo_dir,
                "horse_modules dir": horse_mod_dir,
                "stdlib override dir: ": stdlib_dir,
                "project copy temp dir": assembled_dir}))

        # Copy entire project into temp folder, so we can e.g.
        # add in a different horse_modules folder:
        target_file = os.path.normpath(os.path.abspath(
            target_file
        ))
        assert(target_file.startswith(repo_dir))
        target_file_rel = target_file[len(repo_dir):]
        while target_file_rel.startswith(os.path.sep):
            target_file_rel = target_file_rel[1:]
        old_target_file = target_file
        target_file = os.path.join(assembled_dir, "project",
            target_file_rel)
        if not single_file:
            shutil.copytree(repo_dir, os.path.join(
                assembled_dir, "project"),
                ignore=shutil.ignore_patterns('*.jpg',
                    '*.xcf', '*.png', '*.mp3',
                    '*.ttf', '*.svg', '*.zip',
                    '*.tar', '*.gz', '*.woff',
                    '*.eot', '*.woff2', '*.wav',
                    '*.ogg', '*.flac', '*.bmp',
                    '*.ico'))
        else:
            os.mkdir(os.path.join(assembled_dir, "project"))
            shutil.copyfile(old_target_file,
                os.path.join(assembled_dir, "project",
                    os.path.basename(target_file)))
        assert(os.path.exists(target_file))

        # Copy in chosen horse_modules:
        if os.path.exists(os.path.join(assembled_dir,
                "project", "horse_modules")):
            shutil.rmtree(os.path.join(
                assembled_dir, "project", "horse_modules"))
        if horse_mod_dir != None:
            shutil.copytree(horse_mod_dir, os.path.join(
                assembled_dir, "project", "horse_modules"))
        else:
            os.mkdir(os.path.join(
                assembled_dir, "project", "horse_modules"))

        # Default to taking our repo as stdlib if there's none:
        if (not os.path.exists(os.path.join(
                assembled_dir, "project",
                "horse_modules", "core.horse64.org")) and
                stdlib_dir is None):
            stdlib_dir = os.path.normpath(
                os.path.join(translator_py_script_dir,
                ".."))

        # Copy in chosen stdlib:
        if stdlib_dir != None:
            if os.path.exists(os.path.join(assembled_dir,
                    "project", "horse_modules",
                    "core.horse64.org")):
                shutil.rmtree(os.path.join(assembled_dir,
                    "project", "horse_modules",
                    "core.horse64.org"))
            shutil.copytree(stdlib_dir,
                    os.path.join(assembled_dir,
                    "project", "horse_modules",
                    "core.horse64.org"))

        # Now translate and run the actual program:
        translate_do_func(
            original_h64_file_path=original_target_file,
            output_h64_file=output_h64_file,
            output_py_file=output_py_file,
            output_file_linenos=output_file_linenos,
            target_file=target_file,
            target_file_args=target_file_args,
            keep_files=keep_files,
            paranoid=paranoid,
            run_as_test=run_as_test,
            overridden_package_name=overridden_package_name,
        )
    finally:
        shutil.rmtree(assembled_dir)
        pass


def translate_do_func(
        original_h64_file_path=None,
        output_h64_file=False,
        output_py_file=False,
        output_file_linenos=True,
        target_file=None,
        target_file_args=[],
        keep_files=False,
        paranoid=False,
        run_as_test=False,
        force_separate_process=False,
        overridden_package_name=None):

    if (not os.path.exists(target_file) or
            os.path.isdir(target_file) or
            not target_file.endswith(".h64") or
            "-" in os.path.basename(target_file) or
            "." in os.path.basename(target_file).
                rpartition(".")[0]):
        raise IOError("missing target file, " +
            "or target file not a .h64 file with proper " +
            "module name: " + str(target_file))

    # Detect basic project info:
    global_init_func_code_store = dict()
    project_info = TranslatedProjectInfo()
    project_info.package_name = overridden_package_name
    (project_info.repo_folder, modname) = locate_repo_folder(
        target_file
    )
    assert(project_info.repo_folder != None)
    assert(modname != None and modname != "")
    modfolder = os.path.abspath(os.path.dirname(target_file))
    if DEBUGV.ENABLE:
        print("translator.py: debug: " +
            "detected repository folder: " +
            project_info.repo_folder)
    project_info.code_relpath = ""
    if os.path.exists(os.path.join(project_info.repo_folder,
            "src")):
        project_info.code_relpath = "src/"
        assert(modname.startswith("src."))
        modname = modname[len("src."):]
    project_info.code_folder = os.path.join(
        project_info.repo_folder, project_info.code_relpath)
    if (project_info.package_name is None and
            os.path.exists(os.path.join(
            project_info.repo_folder, "horp.conf"))):
        with open(os.path.join(project_info.repo_folder,
                "horp.conf"), "r", encoding='utf-8') as f:
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
                        while fname.startswith("/"):
                            fname = fname[1:]
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
                print("translator.py: warning: " +
                    "failed to get package name from horp.conf: " +
                    str(os.path.join(project_info.repo_folder,
                    "horp.conf")))
    if DEBUGV.ENABLE:
        print("translator.py: debug: " +
            "detected package name: " +
            str(project_info.package_name))

    # Queue up first item and begin translating the program:
    translate_file_queue = []
    source_filepath = os.path.normpath(os.path.abspath(target_file))
    output_filename = (
        os.path.basename(target_file.rpartition(".h64")[0]) + ".py"
    )
    source_filepath_parts = (
        source_filepath.replace("/", os.path.sep).split(os.path.sep)
    )
    if (len(source_filepath_parts) >= 2 and
            source_filepath_parts[-1] ==
            source_filepath_parts[-2] + ".h64"):
        output_filename = "__init__.py"
    queue_file_if_not_queued(translate_file_queue,
        (source_filepath, output_filename,
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
            print("translator.py: debug: looking at "
                "queue item: " + str(
                list(original_queue_tuple)[:-1]) +
                " (queue reason" +
                (" not given" if (reason is None or reason == "") else
                ": " + reason) + ")")
        queue_module_neighbors(
            translate_file_queue, target_file,
            modname, package_name)
        contents = None
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                contents = f.read()
        except FileNotFoundError as e:
            print("translator.py: error: trying to locate module " +
                modname + " in package " + str(package_name) +
                " but file is missing: " + str(target_file) + "\n" +
                "translator.py: debug: import reason was: " + str(reason))
            import sys
            sys.exit(1)
        original_contents = contents
        pkg_dir = project_info.repo_folder
        pkg_src_dir = project_info.repo_folder
        if len(project_info.code_relpath):
            if not project_info.code_relpath.startswith("/"):
                pkg_src_dir += "/"
            pkg_src_dir += project_info.code_relpath
        if DEBUGV.ENABLE:
            print("translator.py: debug: preprocessing and sanity-"
                "checking file: " + target_file)
        contents = translator_preprocessor.\
            preprocess_file_in_translator(
                contents, pkg_dir, pkg_src_dir,
                project_info.repo_folder + "/horse_modules",
                target_file,
                modname, package_name,
                "horse64-translator-py v" + VERSION
            )
        sanity_check_h64_codestring(contents, modname=modname,
            filename=target_file)
        stmt_list_uses_banned_things(contents)
        indent_sanity_check(contents, "module '" + str(modname) +
            "'" + (" in '" + str(package_name) + "'" if
            package_name != None else ""))
        assert(type(contents) == str)
        contents = separate_out_inline_funcs(contents)
        if paranoid:
            try:
                sanity_check_h64_codestring(
                    contents, modname=modname,
                    filename=target_file)
            except ValueError as e:
                raise ValueError("INTERNAL ERROR, "
                    "separate_out_inline_funcs() "
                    "broke syntax: " + str(e) + "\n"
                    "FULL BROKEN FILE DUMP:\n" +
                    untokenize(contents) + "\nEND OF DUMP.")
        assert(type(contents) == str)
        if DEBUGV.ENABLE:
            print("translator.py: debug: tokenizing file: " +
                target_file)
        contents = tokenize(contents)
        try:
            contents = (
                transform_h64_with_to_do_rescue(contents)
            )
        except Exception as e:
            raise ValueError("in module '" + str(modname)
                + "'" + (" in package '" +
                    str(package_name) + "'" if
                    package_name != None else "") + ", "
                "encountered transform_h64_with_to_do_rescue() error: " +
                str(e))
        assert(type(contents) == list)
        try:
            # FIXME: Disabling this transformation for now, not working.
            contents = (
                make_string_literal_python_friendly(contents)
            )  # Hack, correct transformation is one line below:
            #contents = transform_later_ifs_to_closures(
            #    make_string_literal_python_friendly(tokenize(contents)),
            #    callback_delayed_func_name=[
            #        "_translator_runtime_helpers", ".",
            #        "_async_delay_call"],
            #    ignore_erroneous_code=False)
        except Exception as e:
            raise ValueError("in module '" + str(modname)
                + "'" + (" in package '" +
                    str(package_name) + "'" if
                    package_name != None else "") + ", "
                "encountered transform_later_ifs_to_closures() error: " +
                str(e))
        assert(type(contents) == list)
        if DEBUGV.ENABLE:
            print("translator.py: debug: doing advanced transforms, "
                "in horse64 shape, of file: " +
                target_file)
        try:
            contents = transform_later_to_closures(
                contents,
                callback_delayed_func_name=[
                    "_translator_runtime_helpers", ".",
                    "_async_delay_call"],
                ignore_erroneous_code=False)
        except Exception as e:
            raise ValueError("in module '" + str(modname)
                + "'" + (" in package '" +
                    str(package_name) + "'" if
                    package_name != None else "") + ", "
                "encountered transform_later_to_closures() error: " +
                str(e))
        if paranoid:
            try:
                sanity_check_h64_codestring(
                    contents, modname=modname,
                    filename=target_file)
            except ValueError as e:
                msg = ("INTERNAL ERROR, "
                    "transform_later_to_closures() "
                    "broke syntax: " + str(e) + "\n"
                    "FULL BROKEN FILE DUMP:\n" +
                    untokenize(contents) + "\nEND OF DUMP.")
                print(msg, flush=True)
                raise ValueError("INTERNAL ERROR, "
                    "transform_later_to_closures() "
                    "broke syntax: " + str(e) + "\n")
        contents = make_kwargs_in_call_tailing(contents)
        if paranoid:
            try:
                sanity_check_h64_codestring(
                    contents, modname=modname,
                    filename=target_file)
            except ValueError as e:
                raise ValueError("INTERNAL ERROR, "
                    "make_kwargs_in_call_tailing() "
                    "broke syntax: " + str(e))
        assert(type(contents) == list and
            (len(contents) == 0 or type(contents[0]) == str))
        contents = (
            translator_hacks_registry.apply_hacks_on_file(
                contents, modname, package_name,
                is_after_python_translate=False
            ))
        if output_h64_file and target_file == mainfilepath:
            output_file_result = (
                transform_for_file_output(contents,
                    with_linenos=output_file_linenos))
            print(output_file_result)
            import sys
            sys.exit(0)

        sc = TranslateInfoScope()
        assert(modname != None and modname.strip() != "")
        sc.module_name = modname
        sc.global_init_func_code = global_init_func_code_store
        sc.package_name = package_name
        sc.folder_path = modfolder
        sc.project_info = project_info
        sc.translate_file_queue = translate_file_queue
        sc.paranoid = paranoid
        if DEBUGV.ENABLE:
            print("translator.py: debug: finished pre-transforms "
                "for file: " + target_file)
        contents_result = translate(contents, sc)
        disk_target_folder = (
            project_info.get_package_subfolder(
                package_name, for_output=True) +
            modname.replace(".", "/"))
        if target_filename != "__init__.py":
            disk_target_folder = os.path.dirname(disk_target_folder)
        if DEBUGV.ENABLE and DEBUGV.ENABLE_QUEUE:
            print("translator.py: debug: will write "
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
        if DEBUGV.ENABLE and DEBUGV.ENABLE_QUEUE:
            print("translator.py: debug: Will assemble "
                "the actual code of translated files...")
        for translated_file in translated_files:
            associated_package_output_folder = os.path.join(
                output_folder,
                project_info.get_package_subfolder(
                    translated_files[translated_file]
                        ["package-name"], for_output=True))
            _modname = (translated_files
                        [translated_file]["module-name"])
            _pkgname = (translated_files
                        [translated_file]["package-name"])
            contents_result = (
                "import sys as _remapped_sys;"
                "import shutil as _remapped_shutil;"
                "import traceback as _remapped_traceback;"
                "import os as _remapped_os;"
                "import uuid as _remapped_uuid;"
                "import enum as _remapped_enum;"
                "import random as _remapped_random;"
                "import tempfile as _remapped_tempfile;"
                "_remapped_sys.path.insert(1, " +
                    as_escaped_code_string(os.path.join(
                        output_folder, "_translator_runtime")) + ");" +
                "_remapped_sys.path.append(" +
                    as_escaped_code_string(output_folder) + ");" +
                "_translator_kw_arg_default_value = object();" +
                "_translated_program_version = " +
                as_escaped_code_string(
                    project_info.package_version if
                    project_info.package_version != None else
                    "unknown") + ";" +
                "_translated_program_main_script_file = " +
                as_escaped_code_string(original_h64_file_path) + ";" +
                "import _translator_runtime_helpers; " +
                "import _translator_runtime_helpers_templating; "
                "_translator_runtime_helpers._global_module_registry[" +
                    as_escaped_code_string(
                        _modname + "@" + str(_pkgname)) +
                "] = _remapped_sys.modules[__name__];\n"
                ) + translated_files[translated_file]["output"]

            # Prepare to output the types as Python "class" defs:
            first_externaltype_extends = True
            type_ordering_unfiltered = ordered_known_types()
            type_ordering = []
            for regtype_key in type_ordering_unfiltered:
                regtype = known_types[regtype_key]
                if (regtype.module != _modname or
                        regtype.pkgname != _pkgname):
                    continue
                type_ordering.append(regtype_key)
            def cmp_two_types(a, b):
                regtype_a = known_types[a]
                regtype_b = known_types[b]
                if (regtype_a.extends_tokens != None
                        and "".join(regtype_a.extends_tokens) ==
                        regtype_b.name):
                    return 1
                elif (regtype_b.extends_tokens != None
                        and "".join(regtype_b.extends_tokens) ==
                        regtype_a.name):
                    return -1
                if (regtype_a.name > regtype_b.name):
                    return 1
                return -1
            # Order types such that they can extend each other:
            type_ordering = sorted(type_ordering,
                key=functools.cmp_to_key(cmp_two_types))
            # Figure out what classes need delayed init:
            delayed_init_classes = set()
            delayed_set_changed = True
            while delayed_set_changed:
                delayed_set_changed = False
                for regtype_key in type_ordering:
                    regtype = known_types[regtype_key]
                    if regtype.name in delayed_init_classes:
                        continue
                    if (regtype.extends_tokens != None and
                            "." in regtype.extends_tokens and
                            firstnonblank(regtype.extends_tokens) !=
                            "_translator_runtime_helpers"):
                        delayed_init_classes.add(regtype.name)
                        delayed_set_changed = True
                    elif (regtype.extends_tokens != None and
                            "".join(regtype.extends_tokens) in
                            delayed_init_classes):
                        delayed_init_classes.add(regtype.name)
                        delayed_set_changed = True
            # Now actually output the classes:
            for regtype_key in type_ordering:
                regtype = known_types[regtype_key]
                gencode_nameprefix = ""
                maybe_extends_nonlocal = False
                if regtype.name in delayed_init_classes:
                    # Likely referring to some imported class symbol
                    # (that originates in a different module).
                    maybe_extends_nonlocal = True
                    gencode_nameprefix = "_translated_delayed_"
                contents_result += "\n"
                append_t = "class " + gencode_nameprefix + regtype.name
                if regtype.extends_tokens != None:
                    append_t += ("(" +
                        untokenize(regtype.extends_tokens) + ")")
                append_t += ":\n"
                append_t += ("    def __repr__(self, *args):\n")
                append_t += ("        if hasattr(self, \"as_str\") "
                                "and len(args) == 0:\n")
                append_t += ("            return self.as_str()\n")
                append_t += ("        return super()."
                                    "__repr__(*args)\n")
                if "init" in regtype.funcs:
                    assert(regtype.funcs["init"]["arguments"][0] == "(")
                    regtype.funcs["init"]["arguments"] = (
                        regtype.funcs["init"]["arguments"][:1] +
                        ["self", ",", " "] +
                        regtype.funcs["init"]["arguments"][1:]
                    )
                    append_t += ("    def __init__" +
                        untokenize(regtype.funcs
                            ["init"]["arguments"]) + ":\n")
                    append_t += ("        _translator_runtime_helpers." +
                        "_call_builtin_init_if_needed(self, \"" +
                        gencode_nameprefix + regtype.name + "\")\n")
                    append_t += ("        def _do_super_init(*args, "
                                "**kwargs):\n"
                                 "            _translator_runtime_helpers."
                                 "_explicit_super_init_call(self, '" +
                                 gencode_nameprefix + regtype.name + "', "
                                 "args=args, kwargs=kwargs)\n")
                    if regtype.init_code != None:
                        #append_t += ("        print('Ran builtin init on " +
                        #    gencode_nameprefix + regtype.name + "/' + "
                        #    "str(self.__class__))\n")
                        append_t += ("        if (hasattr(self, "
                            "'__RAN_AUTOINIT_" +
                            gencode_nameprefix + regtype.name + "') and\n" +
                                    "                self.__RAN_AUTOINIT_" +
                            gencode_nameprefix + regtype.name + " == True):\n")
                        #append_t += ("            print('Oops already ran')\n")
                        append_t += ("            pass\n")
                        append_t += ("        else:\n")
                        append_t += ("            pass\n")
                        lines = regtype.init_code.splitlines()
                        new_code = "    " + ("\n    ").join(lines)
                        append_t += new_code + "\n"
                    append_t += regtype.funcs["init"]["code"] + "\n"
                    append_t += ("        pass\n")
                else:
                    inner_indent = (get_indent(
                        regtype.init_code))
                    if inner_indent is None:
                        inner_indent = "        "
                    append_t += ("    __NO_USERDEFINED_INIT_" +
                        gencode_nameprefix + regtype.name + " = True\n")
                    append_t += ("    def __init__(self, " +
                        "*args, **kwargs):\n")
                    #append_t += ("        print('Ran builtin init on " +
                    #    gencode_nameprefix + regtype.name + "/' + "
                    #    "str(self.__class__))\n")
                    append_t += ("        if (hasattr(self, "
                        "'__RAN_AUTOINIT_" +
                        gencode_nameprefix + regtype.name + "') and\n" +
                                 "                self.__RAN_AUTOINIT_" +
                        gencode_nameprefix + regtype.name + " == True):\n")
                    #append_t += ("            print('Oops already ran')\n")
                    append_t += ("            return\n")
                    append_t += ("        self.__RAN_AUTOINIT_" +
                        gencode_nameprefix + regtype.name + " = True\n")
                    # First, make sure to call super type constructor:
                    super_result_var = (
                        "_v" + str(uuid.uuid4()).replace("-", "")
                    )
                    append_t += ("        _translator_runtime_helpers." +
                        "_call_builtin_init_if_needed(self, \"" +
                        gencode_nameprefix + regtype.name + "\")\n")
                    if regtype.init_code != None:
                        # Now initialize all variables:
                        append_t += regtype.init_code + "\n"
                    # Then check if we're at the top of the parent chain,
                    # in which case call user constructors on sub classes if
                    # any:
                    append_t += ("        _translator_runtime_helpers." +
                        "_try_implicit_super_init_call_for_initless_cls(" +
                        "self, \"" + gencode_nameprefix + regtype.name +
                        "\", args=args, kwargs=kwargs)\n")
                    # Nothing else to do:
                    append_t + (inner_indent + "pass\n")
                for funcname in regtype.funcs:
                    if funcname == "init":
                        continue
                    assert(regtype.funcs[funcname]["arguments"][0] == "(")
                    if funcname.startswith("__extends__"):
                        continue
                    def_name = funcname
                    if regtype.funcs[funcname]["ever-extended"]:
                        def_name = "__unextended__" + funcname
                        prev_name = def_name
                        idx = 0
                        while idx < len(
                                regtype.funcs[funcname]["extend-names"]):
                            funcname2 = (
                                regtype.funcs[funcname]
                                    ["extend-names"][idx])
                            is_last = idx + 1 >= len(
                                regtype.funcs[funcname]["extend-names"])
                            use_name = funcname2
                            if is_last:
                                use_name = funcname
                            elif idx > 0:
                                prev_name = (
                                    regtype.funcs[funcname]
                                        ["extend-names"][idx - 1])
                            regtype.funcs[funcname2]["arguments"] = (
                                regtype.funcs[funcname2]["arguments"][:1] +
                                ["self", ",", " "] +
                                regtype.funcs[funcname2]["arguments"][1:]
                            )
                            append_t += ("    def " + use_name +
                                untokenize(regtype.funcs
                                    [funcname2]["arguments"]) + ":\n")
                            append_t += ("        extended = self." +
                                prev_name + "\n")
                            append_t += ("        __h64_cls_ref__ = " +
                                gencode_nameprefix + regtype.name + "\n")
                            append_t += (
                                regtype.funcs[funcname2]["code"] + "\n")
                            idx += 1
                    regtype.funcs[funcname]["arguments"] = (
                        regtype.funcs[funcname]["arguments"][:1] +
                        ["self", ",", " "] +
                        regtype.funcs[funcname]["arguments"][1:]
                    )
                    append_t += ("    def " + def_name +
                        untokenize(regtype.funcs
                            [funcname]["arguments"]) + ":\n")
                    append_t += ("        __h64_cls_ref__ = " +
                        gencode_nameprefix + regtype.name + "\n")
                    append_t += (
                        regtype.funcs[funcname]["code"] + "\n")
                if not maybe_extends_nonlocal:
                    contents_result += "\n" + append_t
                else:
                    # Since the extended module is external, we need to
                    # do this in our delayed module init since due to
                    # Python's hate of cyclic imports, we shouldn't access
                    # other modules just yet.
                    contents_result += ("\n" + regtype.name +
                        " = None\n")
                    key = (_modname, _pkgname)
                    assert(key[0] != None)
                    if not key in sc.global_init_func_code:
                        sc.global_init_func_code[key] = ""
                    prepend_t = ("\n    " +
                        "global " + regtype.name)
                    prepend_t += ("\n    " +
                        "try:")
                    prepend_t += ("\n        " + (
                        "\n        ".join(append_t.splitlines())) +
                        "\n        " + regtype.name + " = " +
                        "_translated_delayed_" +
                        regtype.name + "\n")
                    prepend_t += ("\n    " +
                        "except TypeError as e:")
                    #prepend_t += ("\n        " +
                    #    "_remapped_traceback.print_exc()")
                    prepend_t += ("\n        " +
                        "_translated_extendtype_fail = True")
                    if first_externaltype_extends:
                        prepend_t += ("\n    "
                            "if _translated_extendtype_fail:")
                        prepend_t += ("\n        return False\n")
                    sc.global_init_func_code[key] = (
                        sc.global_init_func_code[key] +
                        "\n" + prepend_t
                    )
                    first_externaltype_extends = False

            # Write out all the delayed init code to an appended func:
            key = (_modname, _pkgname)
            contents_result += "\ndef _translator_delayed_modinit():\n"
            if DEBUGV.ENABLE_MODLOAD:
                contents_result += ("    print('Delayed mod "
                    "init for ' + " +
                    as_escaped_code_string(_modname) + " + '@' + " +
                    (as_escaped_code_string(_pkgname) if
                     _pkgname != None else "'main'") + " + ' (' +"
                     "(__name__) + ')')\n")
            contents_result += ("    _translated_extendtype_fail" +
                " = False\n")
            if key in sc.global_init_func_code:
                contents_result += (
                    sc.global_init_func_code[key].rstrip() + "\n"
                )
            contents_result += "    pass\n"
            contents_result += ("_translator_runtime_helpers."
                "_delayed_modinit_funclist.append("
                "_translator_delayed_modinit)\n")

            # Compute output path:
            targetfilename = os.path.basename(
                translated_files[translated_file]["target-filename"]
            )
            contents = translated_files[translated_file]["output"]
            subfolder = (translated_files[translated_file]
                ["disk-fake-folder"])
            targetpath = os.path.normpath(os.path.join(
                output_folder, mpath(os.path.join(subfolder,
                    targetfilename))
            ))
            translated_files[translated_file]["target-filepath"] = (
                targetpath
            )

            # Now append our startup code if this is the main file:
            is_main_file = (translated_files\
                [translated_file]["path"] == mainfilepath)
            if is_main_file and run_as_test:
                # Get the name & info of all global test funcs:
                test_funcs = get_global_standalone_func_names(
                    translated_files[translated_file]
                        ["original-source"])
                test_funcs = [(tf,
                    test_funcs[tf]["is-later-func"]) for
                    tf in test_funcs if tf.startswith("test_")]
                if len(test_funcs) == 0 and not output_py_file:
                    print("translator.py: error: "
                        "no test functions found in this file")
                    import sys
                    sys.exit(1)

                # Insert a new hidden main to call the test funcs:
                testmain = ("_testsmain" +
                    str(uuid.uuid4()).replace("-", ""))
                contents_result += ("\ndef " + testmain + "():" +
                    "\n    ")
                later_bail_count = 0
                for (tfname, tfislater) in test_funcs:
                    if tfislater:
                        later_bail_count += 1
                contents_result += ("_translator_runtime_helpers."
                    "_async_final_bail_required_extra_bails(" +
                    str(max(0, later_bail_count - 1)) + ");")
                contents_result += "\n    "
                for (tfname, tfislater) in test_funcs:
                    contents_result += (tfname + "(" +
                        ("_translator_runtime_helpers."
                        "_async_final_bail_handler" if
                        tfislater else "") + "); ")

                # Insert actual main to call our test main:
                if force_separate_process:
                    contents_result += (
                        "\nif __name__ == '__main__':")
                else:
                    contents_result += (
                        "\ndef _generated_main():")
                contents_result += (
                    "\n    _translator_runtime_helpers."
                            "_ensure_all_mods_load(" +
                            as_escaped_code_string(output_folder) +
                            "," +
                            as_escaped_code_string(targetpath) +
                            ", debug=" +
                            str(DEBUGV.ENABLE_MODLOAD) + ")"
                    "\n    v = ("
                    "\n        _translator_runtime_helpers."
                                "_run_main(" + testmain + "))"
                    "\n    _remapped_sys.stdout.flush()"
                    "\n    _remapped_sys.stderr.flush()"
                    "\n    _remapped_sys.exit(v)\n")
                if not force_separate_process:
                    contents_result += (
                        "\nif __name__ == '__main__':\n" +
                        "    _generated_main()\n")
            # As final step, apply known per file hacks:
            contents_result = (
                translator_hacks_registry.apply_hacks_on_file(
                    contents_result,
                    translated_files[translated_file]
                        ["module-name"],
                    translated_files[translated_file]
                        ["package-name"],
                    is_after_python_translate=True
                ))
            if is_main_file and not run_as_test:
                # Get the name & info, find out about our 'main':
                test_funcs = get_global_standalone_func_names(
                    translated_files[translated_file]
                        ["original-source"])
                has_main = ("main" in test_funcs)
                main_is_later_func = False
                if has_main:
                    main_is_later_func = (
                        test_funcs["main"]["is-later-func"]
                    )

                # Insert a new hidden main that can pass a fake callback:
                innermain = ("_wrapmain" +
                    str(uuid.uuid4()).replace("-", ""))
                contents_result += ("\ndef " + innermain + "():" +
                    "\n    ")
                if has_main:
                    if main_is_later_func:
                        contents_result += ("main("
                            "_translator_runtime_helpers."
                            "_async_final_bail_handler); ")
                    else:
                        contents_result += ("v = main();")
                        contents_result += (
                            "\n    if v is True or v is None:")
                        contents_result += ("\n        v = 0")
                        contents_result += ("\n    elif v is False:")
                        contents_result += ("\n        v = 1")
                        contents_result += ("\n    "
                            "_remapped_sys.exit(int(v))")
                else:
                    contents_result += ("return 0;")

                # Add actual main call:
                if force_separate_process:
                    contents_result += (
                        "\nif __name__ == '__main__':")
                else:
                    contents_result += (
                        "\ndef _generated_main():")
                contents_result += (
                    "\n    _translator_runtime_helpers."
                            "_ensure_all_mods_load(" +
                            as_escaped_code_string(output_folder) +
                            "," +
                            as_escaped_code_string(targetpath) +
                            ", debug=" +
                            str(DEBUGV.ENABLE_MODLOAD) + ")"
                    "\n    v = ("
                    "\n        _translator_runtime_helpers."
                                "_run_main(" + innermain + "))"
                    "\n    _remapped_sys.stdout.flush()"
                    "\n    _remapped_sys.stderr.flush()"
                    "\n    _remapped_sys.exit(v)\n")
                if not force_separate_process:
                    contents_result += (
                        "\nif __name__ == '__main__':\n" +
                        "    _generated_main()\n")
            if is_main_file and output_py_file:
                print(mainfilepath)
                output_file_result = (
                transform_for_file_output(contents_result,
                    with_linenos=output_file_linenos))
                print(output_file_result)
                import sys
                sys.exit(0)

            if DEBUGV.ENABLE and DEBUGV.ENABLE_CONTENTS:
                print("translator.py: debug: have output of " +
                    str(len(contents_result.splitlines())) +
                    " lines for: " +
                    translated_file + " (module: " +
                    translated_files[translated_file]
                        ["module-name"] + ")")
                print(contents_result)
            translated_files[translated_file]["output"] = contents_result
            #print(tokenize(b" \n\r test".decode("utf-8")))
        returncode = 0
        if keep_files:
            print("translator.py: info: writing " +
                "translated files to (will be kept): " +
                output_folder)
        elif DEBUGV.ENABLE and DEBUGV.ENABLE_FILE_PATHS:
            print("translator.py: debug: writing temporary " +
                "result to (will be deleted): " +
                output_folder)
        for helper_file in os.listdir(os.path.join(
                translator_py_script_dir, "translator_modules")):
            if (not helper_file.startswith("translator_runtime") or
                    not helper_file.endswith(".py")):
                continue
            if not os.path.exists(os.path.join(output_folder,
                    "_translator_runtime")):
                os.mkdir(os.path.join(output_folder,
                    "_translator_runtime"))
            t = None
            with open(os.path.join(translator_py_script_dir,
                    "translator_modules",
                    helper_file), "r", encoding="utf-8") as f:
                t = f.read()
                t = (translator_debugvars.
                    get_debug_var_strings() + "\n" + t)
                t = t.replace("__translated_output_root_path__",
                    as_escaped_code_string(output_folder))
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
                print("translator.py: debug: wrote file: " +
                    os.path.join(output_folder,
                    "_translator_runtime", "_" + helper_file))
        run_py_path = None
        for translated_file in translated_files:
            name = os.path.basename(
                translated_files[translated_file]["path"]
            ).rpartition(".h64")[0].strip()
            contents = translated_files[translated_file]["output"]
            target_filepath = (translated_files[translated_file]
                ["target-filepath"])
            subfolder_abs = os.path.dirname(
                target_filepath
            )
            if not os.path.exists(subfolder_abs):
                os.makedirs(subfolder_abs)
            with open(target_filepath, "w", encoding="utf-8") as f:
                f.write(contents)
            if DEBUGV.ENABLE and DEBUGV.ENABLE_FILE_PATHS:
                print("translator.py: debug: wrote file: " +
                    target_filepath + " (module: " +
                    translated_files[translated_file]["module-name"] + ")")
            if translated_files[translated_file]["path"] == mainfilepath:
                run_py_path = target_filepath

        # Now, execute the actual module:
        relpath = os.path.normpath(os.path.abspath(run_py_path))[
            len(os.path.normpath(os.path.abspath(output_folder))):]
        while relpath.startswith("/") or relpath.startswith(os.path.sep):
            relpath = relpath[1:]
        modname = relpath.rpartition(".py")[0]
        if modname.endswith("__init__"):
            modname = modname[:-len("__init__")]
        while modname.endswith("/") or modname.endswith(os.path.sep):
            modname = relpath[:-1]
        modname = modname.replace(os.path.sep, ".").replace("/", ".")
        returncode = 0
        if not force_separate_process:
            import importlib.util
            import sys
            sys.path = [output_folder] + sys.path
            sys.argv = [run_py_path] + target_file_args
            spec = importlib.util.spec_from_file_location(
                modname, run_py_path)
            m = importlib.util.module_from_spec(spec)
            sys.modules[modname] = m
            spec.loader.exec_module(m)
            returncode = m._generated_main()
            if type(returncode) == bool:
                if returncode:
                    returncode = 0
                else:
                    returncode = -1
            elif type(returncode) == float:
                returncode = int(round(returncode))
            elif type(returncode) != int:
                returncode = 0
        else:
            import sys
            launch_cmd = [
                sys.executable, run_py_path
            ] + target_file_args
            if DEBUGV.ENABLE:
                print("translator.py: debug: launching program: " +
                    str(launch_cmd))
            sys.stdout.flush()
            sys.stderr.flush()
            returncode = None
            result = subprocess.run(launch_cmd)
            returncode = result.returncode
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        if not keep_files:
            shutil.rmtree(output_folder)
        else:
            print("Translated files left available in: " + output_folder)
    sys.exit(returncode)


if __name__ == "__main__":
    run_translator_main()


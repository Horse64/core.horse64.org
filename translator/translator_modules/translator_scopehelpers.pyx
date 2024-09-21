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

#cython: language_level=3, boundscheck=False, infer_types=True, cdivision=True, overflowcheck=False

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

from translator_syntaxhelpers import is_identifier
from translator_syntaxhelpers import (
    firstnonblank, firstnonblankidx,
    nextnonblank, nextnonblankidx,
    prevnonblank, prevnonblankidx,
    tokenize, split_toplevel_statements,
    is_whitespace_token,
    get_statement_block_ranges,
)

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)

def statement_declared_identifiers(
        st, recurse=True, recurse_into_funcs=False,
        exclude_direct_func_name=False
        ):
    if type(st) == str:
        st = tokenize(st)
    assert(type(st) in {tuple, list})

    # Collects names from inner block ranges:
    def do_recurse():
        nonlocal recurse
        if not recurse:
            return []
        inner_result = []

        # Split all block contents to scan them all:
        ranges = get_statement_block_ranges(st)
        stmts = []
        for brange in ranges:
            subtokens = st[brange[0]:brange[1]]
            stmts += split_toplevel_statements(subtokens)

        # Scan resulting statements:
        for inner_st in stmts:
            inner_do_recurse = True
            if (firstnonblank(inner_st) == "func" and
                    not recurse_into_funcs):
                # Don't pick up those func's inner blocks:
                inner_do_recurse = False
            # Add stuff to our overall result:
            inner_result += (
                statement_declared_identifiers(
                    inner_st,
                    recurse=inner_do_recurse,
                    recurse_into_funcs=
                        recurse_into_funcs))
        return inner_result
    result = []
    if firstnonblank(st) == "func":
        result = get_names_defined_in_func(
            st, is_anonymous_inline=False,
            exclude_inner=(not recurse),
            exclude_direct_func_name=
                exclude_direct_func_name)
        return result + do_recurse()
    elif firstnonblank(st) in {"for", "const", "var"}:
        idx = firstnonblankidx(st)
        while True:
            idx = nextnonblankidx(st, idx)
            if idx < 0 or not is_identifier(st[idx]):
                break
            result.append(st[idx])
            if nextnonblank(st, idx) != ",":
                break
            idx = nextnonblankidx(st, idx)
        return result + do_recurse()
    elif firstnonblank(st) in {"with", "do"}:
        bracket_depth = 0
        i = 0
        while i < len(st) and (
                st[i] != "as" or
                bracket_depth > 0):
            if st[i] in {"(", "[", "{"}:
                bracket_depth += 1
            elif st[i] in {")", "]", "}"}:
                bracket_depth -= 1
            i += 1
        if i < len(st) and st[i] == "as":
            idf = nextnonblank(st, i)
            if is_identifier(idf):
                result.append(idf)
        return result + do_recurse()
    return result + do_recurse()

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
        import_rename = None
        if nextnonblank(statement, i) == "as":
            nexti = nextnonblankidx(statement, i, no=2)
            assert(i < len(statement) and is_identifier(statement[i]))
            import_rename = statement[nexti]
            i = nexti
        if nextnonblank(statement, i) != "from":
            if import_rename != None:
                result.append([
                    import_rename, None, ".".join(import_module)
                ])
            else:
                result.append([
                    ".".join(import_module), None,
                    ".".join(import_module)])
            continue
        i = nextnonblankidx(statement, i, no=2)
        import_package = statement[i]
        while (i < len(statement) and
                nextnonblank(statement, i) == "." and
                is_identifier(nextnonblank(
                    statement, i, no=2))):
            i = nextnonblankidx(statement, i, no=2)
            import_package += ("." + statement[i])
        if import_rename != None:
            result.append([import_rename, import_package,
                ".".join(import_module)])
        else:
            result.append([".".join(import_module),
                import_package, ".".join(import_module)])
        continue
    return result

def get_global_standalone_func_names(s,
        error_duplicates=False
        ):
    result = dict()
    scope = get_global_names(s)
    for entry in scope:
        if scope[entry]["type"] == "func":
            result[entry] = scope[entry]
    return result

def get_undefined_uses_in_func(
        st, ignore_builtins=True,
        ignore_later_generated=False,
        is_anonymous_inline=False,
        ignore_these_labels=None
        ):
    """ Get all identifiers that are present in all
        inner scopes of a function statement."""

    if type(st) == str:
        st = tokenize(st)
    else:
        st = list(st)
    if ignore_these_labels is None:
        ignore_these_labels = []
    func_kw_idx = firstnonblankidx(st)
    if (func_kw_idx < 0 or
            st[func_kw_idx] != "func"):
        return set()
    names = get_all_inner_names_in_func(st)
    outer_names_with_args = get_names_defined_in_func(
        st, is_anonymous_inline=is_anonymous_inline,
        exclude_inner=False,
        exclude_direct_func_name=False
    )
    for oname in outer_names_with_args:
        names.add(oname)

    # Now find all the uses that seem undefined:
    undefined_names = set()
    ranges = get_statement_block_ranges(st)
    for brange in ranges:
        subtokens = st[brange[0]:brange[1]]
        subtokenslen = len(subtokens)
        i = 0
        while i < subtokenslen:
            if subtokens[i] == "func":
                i = get_idx_past_func(subtokens, i)
                continue
            if not is_identifier(subtokens[i]):
                i += 1
                continue
            if subtokens[i] in names:
                i += 1
                continue
            if (prevnonblank(subtokens, i) in {
                    "var", "const", "for",
                    "as", "."
                    }):
                i += 1
                continue
            if (nextnonblank(subtokens, i) == "=" and
                    prevnonblank(subtokens, i) in
                    {"(", ","}):
                i += 1
                continue
            undefined_names.add(subtokens[i])
            i += 1
    remove_set = {"self", "extended", "base"}
    if ignore_builtins:
        builtins = {"print", "assert",
            "RuntimeError", "ValueError",
            "NotImplementedError", "has_attr"}
        remove_set = remove_set.union(builtins)
    for remove_label in remove_set:
        undefined_names.discard(remove_label)
    if ignore_later_generated:
        cleaned_set = set()
        for entry in undefined_names:
            if (not entry.startswith("_later_cb") and
                    not entry.startswith("_finallyfun") and
                    not entry.startswith("_latersection_") and
                    not entry.startswith("_rescuefun") and
                    not entry.startswith("_rescuedisable") and
                    not entry.startswith("_finallydisable")
                    ):
                cleaned_set.add(entry)
        undefined_names = cleaned_set
    for entry in ignore_these_labels:
        undefined_names.discard(entry)
    return undefined_names

def get_idx_past_func(st, idx):
    """ Skip past a given func definition.
        Also works if started after the 'func'
        keyword but before the code block opens. """
    bdepth = 0
    stlen = len(st)
    i = idx
    while (i < stlen and
            (st[i] != "{" or
            prevnonblank(st, i) in {
                "(", "{", "[", "=", ","
            } or bdepth > 0)):
        if st[i] in {"{", "[", "("}:
            bdepth += 1
        elif st[i] in {"}", "]", ")"}:
            bdepth = max(0, bdepth - 1)
        i += 1
    if (i < stlen and st[i] == "{"):
        bdepth = 1
        while (i < stlen and
                bdepth > 0):
            if st[i] in {"{", "[", "("}:
                bdepth += 1
            elif st[i] in {"}", "]", ")"}:
                bdepth = max(0, bdepth - 1)
                if bdepth <= 0:
                    break
            i += 1
    return i

def get_all_inner_names_in_func(st):
    """ Get all identifiers that are present in all
        inner scopes of a function statement."""

    if type(st) == str:
        st = tokenize(st)
    else:
        st = list(st)
    if firstnonblank(st) != "func":
        return set()

    names = set()
    ranges = get_statement_block_ranges(st)
    for brange in ranges:
        subtokens = st[brange[0]:brange[1]]
        subtokenslen = len(subtokens)
        i = 0
        while i < subtokenslen:
            if (is_identifier(subtokens[i]) and
                    prevnonblank(subtokens, i) in {
                        "var", "const", "for",
                        "as"
                    }):
                names.add(subtokens[i])
            elif subtokens[i] == "func":
                i += 1
                while (i < subtokenslen and
                        subtokens[i].strip() == ""):
                    i += 1
                if (is_identifier(subtokens[i]) and
                        not nextnonblank(subtokens, i) in
                        {",", "="}):
                    names.add(subtokens[i])
                i = get_idx_past_func(subtokens, i)
                continue
            elif (is_identifier(subtokens[i]) and
                    prevnonblank(subtokens, i) == ","):
                is_vardef = False
                i2 = i - 1
                while True:
                    while (i2 >= 0 and
                            subtokens[i2].strip() == ""):
                        i2 -= 1
                    if i2 >= 0 and subtokens[i2] in {
                            "var", "const"
                            }:
                        is_vardef = True
                        break
                    if i2 < 0 or subtokens[i2] != ",":
                        break
                    i2 -= 1
                    while (i2 >= 0 and
                            subtokens[i2].strip() == ""):
                        i2 -= 1
                    if (i2 < 0 or
                            not is_identifier(subtokens[i2])):
                        break
                    i2 -= 1
                if is_vardef:
                    names.add(subtokens[i])
            i += 1
    return names

def get_names_defined_in_func(
        st, is_anonymous_inline=False,
        exclude_inner=False,
        exclude_direct_func_name=False
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
        # Skip over the lead-up type name:
        while (is_identifier(st[k]) and
                nextnonblank(st, k) == "." and
                is_identifier(nextnonblank(st, k, no=2))):
            k = nextnonblankidx(st, k, no=2)
        if (not st[k] in names and
                not exclude_direct_func_name):
            names.append(st[k])
        k = nextnonblankidx(st, k)
    else:
        if (not is_identifier(st[k]) and
                # ^ func myparam { ... }
                not st[k] in {"(", "{"}):
            return []
        # We must insert a fake function name because
        # get_statement_block_ranges() only knows named
        # func statements, not anonymous inline funcs.
        st = st[:k] + [
            "_fanon" + str(uuid.uuid4()).replace("-", ""),
            " "] + st[k:]
        k = nextnonblankidx(st, k)  # Skip past our insert.
    if exclude_inner:
        # No need for argument names or contents, just stop.
        return names
    if st[k] == "(" or is_identifier(st[k]):
        # Argument list start!
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

def get_global_names(
        s, error_on_duplicates=False
        ):
    from translator_latertransform \
        import is_func_a_later_func
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

        # See if this function uses 'later':
        is_later_func = False
        if kw == "func":
            is_later_func = is_func_a_later_func(st)

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
                "type": is_type,
            }
            if is_type == "func":
                result[is_named]["is-later-func"] = (
                    is_later_func
                )
    return result

def make_kwargs_in_call_tailing(s):
    from translator_syntaxhelpers import is_h64op_with_righthand,\
        is_keyword
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
        from translator_syntaxhelpers import untokenize
        return untokenize(s)
    return s


# Copyright (c) 2024-2025, ellie/@ell1e & Horse64's contributors
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

def is_ident_char(c):
    num = None
    if c == "_":
        return True
    num = ord(c)
    if num > 127:
        return True
    return ((num >= ord('a') and num <= ord('z')) or
        (num >= ord('A') and num <= ord('Z')) or
        (num >= ord('0') and num <= ord('9')))

def is_identifier(s):
    i = 0
    slen = len(s)
    if slen <= 0:
        return False
    while i < slen:
        if not is_ident_char(s[i]):
            return False
        if (i == 0 and ord(s[i]) >= ord('0') and
                ord(s[i]) <= ord('9')):
            return False
        i += 1
    if s in {"and", "or", "if", "elseif", "else", "set",
            "endif", "var", "const", "later"}:
        return False
    return True

def evaluate_expr(expr, templ_vars, debug=False):
    expr = str(expr)
    if expr.strip() == "yes":
        return True
    if expr.strip() == "no":
        return False
    if expr.strip() == "none":
        return None
    if (len(expr) > 1 and ((expr[0] == "'" and
            expr[-1] == "'") or
            (expr[0] == '"' and
            expr[-1] == '"'))):
        # FIXME: We ignore string escaping here.
        # However, since this is the crappy python bootstrap
        # implementation, maybe that's fine.
        return expr[1:-1]
    if (expr != "" and ((
            ord(expr[0]) >= ord('0') and
            ord(expr[0]) <= ord('9')) or
            expr[0] == '-')):
        try:
            v = float(expr.strip())
            return v
        except (TypeError, ValueError):
            pass
    bdepth = 0
    op_precedences = [
        ["*", "/"],
        ["+", "-"],
        [">=", "<=", ">", "<"],
        ["==", "!="],
        ["not"],
        ["and"],
        ["or"],
    ]
    def get_precedence(op):
        precedence = 0
        for entry in op_precedences:
            precedence += 1
            if op in entry:
                return precedence
    ops = []
    for entry in op_precedences:
        for op in entry:
            ops.append(str(op))
    op_idx = -1
    op_str = None
    op_precedence = -1
    i = 0
    while i < len(expr):
        if i > 0 and ((ord(expr[i - 1]) >= ord("a") and
                ord(expr[i - 1]) >= ord("z")) or
                expr[i - 1] == "_" or
                (ord(expr[i - 1]) >= ord("0") and
                ord(expr[i - 1]) >= ord("9")) or
                (ord(expr[i - 1]) >= ord("A") and
                ord(expr[i - 1]) >= ord("Z"))) and (
                (ord(expr[i]) >= ord("a") and
                ord(expr[i]) >= ord("z")) or
                (ord(expr[i]) >= ord("A") and
                ord(expr[i]) >= ord("Z"))):
            i += 1
        for op in ops:
            if (expr[i:].startswith(op) and
                    (op_idx < 0 or
                    get_precedence(op) > op_precedence)):
                op_str = op
                op_precedence = get_precedence(op)
        i += 1
    if op_idx < 0:
        if expr.strip().startswith(
                "package.is_dep_in_pkg_mod_dir("
                ):
            expr = expr.strip()
            assert(expr.endswith(")"))
            pkg_name = expr[len("package.is_dep_in_pkg_mod_dir("):]
            pkg_name = pkg_name[:-1].strip()
            assert(pkg_name.startswith("HORP_INFO_PROJECT_DIR"))
            pkg_name = pkg_name[len("HORP_INFO_PROJECT_DIR"):].strip()
            assert(pkg_name.startswith(","))
            pkg_name = pkg_name[1:].strip()
            assert(pkg_name.startswith("\"") or
                pkg_name.endswith("'"))
            assert(pkg_name[0] == pkg_name[-1])
            pkg_name = pkg_name[1:-1]
            result = (
                pkg_name in templ_vars["___known_available_packages"]
            )
            return result
        for tvar in templ_vars:
            if expr.strip().startswith(tvar + ".has(") and \
                    expr.strip().endswith(")"):
                has_arg = expr.strip().partition(tvar + ".has(")[2]
                has_arg = has_arg.rpartition(")")[0]
                value = evaluate_expr(
                    has_arg, templ_vars, debug=debug
                )
                if (type(value) != str and
                        type(templ_vars[tvar]) == str):
                    return False
                result = value in templ_vars[tvar]
                return result
        raise RuntimeError("Cannot parse expression: " +
            str(expr))
    if op_str == "and":
        op_left = expr[0:op_idx]
        op_right = expr[op_idx+len("and"):]
        if evaluate_expr(op_left, templ_vars, debug=debug) != True:
            return False
        if evaluate_expr(op_right, templ_vars, debug=debug) != True:
            return False
        return True
    if op_str == "or":
        op_left = expr[0:op_idx]
        op_right = expr[op_idx+len("and"):]
        if evaluate_expr(op_left, templ_vars, debug=debug) == True:
            return True
        if evaluate_expr(op_right, templ_vars, debug=debug) == True:
            return True
        return False
    if op_str == "not":
        op_right = expr[op_idx+len("not"):]
        if evaluate_expr(op_right, templ_vars, debug=debug) == True:
            return False
        return True
    if op_str == "==":
        op_left = expr[0:op_idx]
        op_right = expr[op_idx+len("=="):]
        v1 = evaluate_expr(op_left, templ_vars, debug=debug)
        v2 = evaluate_expr(op_right, templ_vars, debug=debug)
        return (v1 == v2)
    if op_str == "!=":
        op_left = expr[0:op_idx]
        op_right = expr[op_idx+len("!="):]
        v1 = evaluate_expr(op_left, templ_vars, debug=debug)
        v2 = evaluate_expr(op_right, templ_vars, debug=debug)
        return (v1 != v2)
    if is_identifier(op_str):
        if op_str in templ_vars:
            return templ_vars[op_str]
        return None
    raise RuntimeError("Operator not implemented: " + op_str)

def preprocess(file_contents, templ_vars, debug=False):
    file_contents_len = None
    i = 0
    in_quote = None
    prep_list = []
    file_contents_len = len(file_contents)
    in_quote = ""
    
    # First, collect all preprocessor statements:
    i = 0
    while i < file_contents_len:
        if in_quote == "" and (
                file_contents[i] == "'" or
                file_contents[i] == "\""):
            in_quote = file_contents[i]
        elif in_quote == "" and file_contents[i] == '#':
            i += 1
            while (i < file_contents_len and
                    file_contents[i] not in {"\n", "\r"}):
                i += 1
        elif (in_quote == "" and file_contents[i] == "p" and
                (i <= 0 or
                 not is_ident_char(file_contents[i - 1])) and
                file_contents[i:i + 5] == "prep{"):
            prep_start = i
            prep_inner_start = i + 5
            bracket_depth = 1
            prep_end = i + 5
            i += 5
            while i < file_contents_len:
                if file_contents[i] in {"{", "(", "["}:
                    bracket_depth += 1
                elif file_contents[i] in ("}", ")", "]"):
                    bracket_depth = max(0, bracket_depth - 1)
                    if (bracket_depth == 0 and
                            file_contents[i] == "}"):
                        prep_end = i
                        i += 1
                        break
                i += 1
            prep_end = i
            prep_list.append({
                "type": None, "prep-children": [], "block": False,
                "prep-str": file_contents[
                    prep_inner_start:prep_end - 1
                ].strip(),
                "prep-header-start": prep_start,
                "prep-header-end": prep_end,
                "processed": False,
                "replace-contents": None,
                "prep-parent": None,
            })
        elif in_quote != "":
            if file_contents[i] == "\\":
                i += 2
                continue
            elif file_contents[i] == in_quote:
                in_quote = ""
                i += 1
                continue
        i += 1
    if debug:
        print("translator.py: debug: preprocess(): "
            "prep_list(early)=" + str(prep_list))

    # If we got nothing, bail early:
    if len(prep_list) == 0:
        return file_contents

    # Categorize all the preprocessor statements we found:
    i = 0
    while i < len(prep_list):
        if (prep_list[i]["type"] == None and
                prep_list[i]["prep-str"].startswith("if ")):
            prep_list[i]["expr"] =\
                prep_list[i]["prep-str"][len("if"):].strip()
            prep_list[i]["type"] = "if"
            prep_list[i]["evaluated"] = False
            prep_list[i]["clauses-indexes"] = [i]
            prep_list[i]["endif-index"] = -1
            prep_list[i]["block"] = True
            prep_list[i]["block-unreplaced"] = True
            prep_list[i]["block-start"] = (
                prep_list[i]["prep-header-start"]
            )
            prep_list[i]["block-end"] = prep_list[i]["prep-header-end"]
        elif (prep_list[i]["type"] == None and
                (prep_list[i]["prep-str"].startswith("elseif ") or
                prep_list[i]["prep-str"] == "elseif")):
            prep_list[i]["expr"] =\
                prep_list[i]["prep-str"][len("elseif"):].strip()
            prep_list[i]["type"] = "elseif"
            prep_list[i]["clauses-indexes"] = []
            prep_list[i]["endif-index"] = -1
            prep_list[i]["block"] = True
            prep_list[i]["block-unreplaced"] = True
            prep_list[i]["block-start"] = (
                prep_list[i]["prep-header-start"]
            )
            prep_list[i]["block-end"] = prep_list[i]["prep-header-end"]
        elif (prep_list[i]["type"] == None and
                (prep_list[i]["prep-str"].startswith("else ") or
                prep_list[i]["prep-str"] == "else")):
            prep_list[i]["type"] = "else"
            prep_list[i]["clauses-indexes"] = []
            prep_list[i]["endif-index"] = -1
            prep_list[i]["block"] = True
            prep_list[i]["block-unreplaced"] = True
            prep_list[i]["block-start"] = (
                prep_list[i]["prep-header-start"]
            )
            prep_list[i]["block-end"] = prep_list[i]["prep-header-end"]
        elif (prep_list[i]["type"] == None and
                (prep_list[i]["prep-str"].startswith("endif ") or
                prep_list[i]["prep-str"] == "endif")):
            prep_list[i]["type"] = "endif"
        elif (prep_list[i]["type"] == None and
                (prep_list[i]["prep-str"].startswith("set ") or
                prep_list[i]["prep-str"] == "set")):
            prep_list[i]["type"] = "set"
            prep_list[i]["expr"] =\
                prep_list[i]["prep-str"][len("set"):].strip()
        elif is_identifier(prep_list[i]["prep-str"].strip()):
            prep_list[i]["type"] = "identifier"
            prep_list[i]["expr"] = prep_list[i]["prep-str"].strip()
        prep_list[i]["skipped"] = False
        i += 1

    # Figure out which if/elseif/else clauses belong together:
    i = 0
    while i < len(prep_list):
        if prep_list[i]["type"] != "if":
            i += 1
            continue
        nesting_depth = 0
        i2 = i + 1
        while i2 < len(prep_list):
            if prep_list[i2]["type"] == "if":
                nesting_depth += 1
            elif prep_list[i2]["type"] == "else":
                if nesting_depth == 0:
                    prep_list[i]["clauses-indexes"].append(i2)
            elif prep_list[i2]["type"] == "elseif":
                if nesting_depth == 0:
                    prep_list[i]["clauses-indexes"].append(i2)
            elif prep_list[i2]["type"] == "endif":
                if nesting_depth == 0:
                    prep_list[i]["endif-index"] = i2
                    break
                nesting_depth -= 1
            i2 += 1
        i += 1

    # Copy over if/elseif/else clause indexes to all clauses:
    i = 0
    while i < len(prep_list):
        if prep_list[i]["type"] != "if":
            i += 1
            continue
        clause_idxs = prep_list[i]["clauses-indexes"]
        k = 0
        while k < len(clause_idxs):
            idx = clause_idxs[k]
            prep_list[idx]["clauses-indexes"] = (
                list(clause_idxs)
            )
            prep_list[idx]["endif-index"] =\
                prep_list[i]["endif-index"]
            k += 1
        i += 1

    # Fix block boundaries for if/elseif/else clauses:
    i = 0
    while i < len(prep_list):
        if prep_list[i]["type"] != "if":
            i += 1
            continue
        clause_idxs = prep_list[i]["clauses-indexes"]
        k = 0
        while k < len(clause_idxs):
            idx = clause_idxs[k]
            assert(prep_list[idx]["block"] == True)
            if k > 0:
                prev_idx = clause_idxs[k - 1]
                prep_list[prev_idx]["block-end"] = (
                    prep_list[idx]["block-start"]
                )
            if k + 1 < len(clause_idxs):
                next_idx = clause_idxs[k + 1]
                prep_list[idx]["block-end"] = (
                    prep_list[next_idx]["block-start"]
                )
            else:
                endif_idx = prep_list[i]["endif-index"]
                prep_list[idx]["block-end"] = (
                    prep_list[endif_idx]["prep-header-start"]
                )
            k += 1
        i += 1

    # Assign child items to parents:
    i = 0
    while i < len(prep_list):
        item_start = prep_list[i]["prep-header-start"]
        item_end = prep_list[i]["prep-header-end"]
        if prep_list[i]["block"]:
            item_start = prep_list[i]["block-start"]
            item_end = prep_list[i]["block-end"]
        closest_parent_idx = -1
        closest_parent_start = None
        closest_parent_end = None
        i2 = 0
        while i2 < len(prep_list):
            if (i2 == i or not prep_list[i2]["block"] or
                    item_start < prep_list[i2]["block-start"] or
                    item_end > prep_list[i2]["block-end"]):
                i2 += 1
                continue
            if (closest_parent_idx < 0 or
                    closest_parent_start <
                        prep_list[i2]["block-start"] or
                    closest_parent_end >
                        prep_list[i2]["block-end"]):
                prep_list[i]["prep-parent"] = i2
                prep_list[i2]["prep-children"].append(i)
            i2 += 1
        i += 1
    if debug:
        print("translator.py: debug: preprocess(): "
            "prep_list=" + str(prep_list))

    # Now resolve and process all items:
    made_resolve_progress = True
    while made_resolve_progress:
        made_resolve_progress = False
        i = 0
        while i < len(prep_list):
            if (prep_list[i]["skipped"] or
                    prep_list[i]["processed"] or
                    (prep_list[i]["prep-parent"] != None and
                     not prep_list[prep_list[i]["prep-parent"]]
                        ["processed"])):
                i += 1
                continue
            prep_list[i]["processed"] = True
            made_resolve_progress = True
            if prep_list[i]["type"] == "set":
                assign_left = (prep_list[i]["expr"].
                    partition("=")[0].strip())
                assign_right = (prep_list[i]["expr"].
                    partition("=")[2].strip())
                assign_right = evaluate_expr(
                    assign_right, templ_vars, debug=debug
                )
                templ_vars[assign_left] = assign_right
                i += 1
                continue
            if prep_list[i]["type"] == "identifier":
                idf = prep_list[i]["expr"].strip()
                if not idf in templ_vars:
                    prep_list[i]["replace-contents"] = "none"
                else:
                    prep_list[i]["replace-contents"] = templ_vars[idf]
                while (len(prep_list[i]["replace-contents"]) <
                        len(prep_list[i]["prep-str"])):
                    prep_list[i]["replace-contents"] += " "
                i += 1
                continue
            if prep_list[i]["type"] == "if":
                # First, evaluate all the clauses:
                clause_idxs = prep_list[i]["clauses-indexes"]
                k = 0
                while k < len(clause_idxs):
                    idx = clause_idxs[k]
                    result = False
                    if not "expr" in prep_list[idx]:
                        result = True  # else clause
                    else:
                        result = evaluate_expr(
                            prep_list[idx]["expr"], templ_vars,
                            debug=debug
                        )
                        assert(result in {True, False})
                    prep_list[idx]["expr-result"] = result
                    if result:
                        k2 = k + 1
                        while k2 < len(clause_idxs):
                            idx = clause_idxs[k2]
                            prep_list[idx]["expr-result"] = False
                            k2 += 1
                        break
                    k += 1
                # Now disable everything nested inside false clauses:
                k = 0
                while k < len(clause_idxs):
                    idx = clause_idxs[k]
                    if not prep_list[idx]["expr-result"]:
                        prep_list[idx]["block-unreplaced"] = False
                        k2 = 0
                        while k2 < len(prep_list[idx]["prep-children"]):
                            child_idx = (
                                prep_list[idx]["prep-children"][k2]
                            )
                            prep_list[child_idx]["skipped"] = True
                            k2 += 1
                        inner_str = ""
                        strpos = prep_list[idx]["block-start"]
                        while strpos < prep_list[idx]["block-end"]:
                            if (file_contents[strpos] in
                                    {"\r", "\n", "\t"}):
                                inner_str += file_contents[strpos]
                            else:
                                inner_str += " "
                            strpos += 1
                        prep_list[idx]["replace-contents"] = inner_str
                    k += 1
                i += 1
                continue
            i += 1

    # Insert the resulting strings:
    i = len(prep_list) - 1
    while i >= 0:
        if prep_list[i]["skipped"]:
            i -= 1
            continue
        if not prep_list[i]["block"] or (
                prep_list[i]["block"] and
                prep_list[i]["block-unreplaced"]):
            replace_value = ""
            while len(replace_value) < len(prep_list[i]["prep-str"]):
                replace_value += " "
            if prep_list[i]["replace-contents"] != None:
                replace_value = prep_list[i]["replace-contents"]
            file_contents = (
                file_contents[:prep_list[i]["prep-header-start"]] +
                replace_value +
                file_contents[prep_list[i]["prep-header-end"]:]
            )
            file_contents_len = len(file_contents)
            i -= 1
            continue
        elif prep_list[i]["block"]:
            replace_value = prep_list[i]["replace-contents"]
            assert(replace_value != None)
            file_contents = (
                file_contents[:prep_list[i]["block-start"]] +
                replace_value +
                file_contents[prep_list[i]["block-end"]:]
            )
        i -= 1
        continue

    return file_contents

def preprocess_file_in_translator(
        file_contents, project_base_dir, project_code_dir,
        horse_modules_dir,
        file_path, module_name, package_name, translator_version
        ):
    import os
    have_deps = ["core.horse64.org"]
    if (horse_modules_dir != None and
            os.path.sep + "horse_modules" in
                horse_modules_dir.replace("/", os.path.sep)):
        if os.path.exists(horse_modules_dir):
            have_deps = []
            for f in os.listdir(horse_modules_dir):
                fpath = os.path.join(horse_modules_dir, f)
                if not os.path.isdir(fpath):
                    continue
                if (not "." in f or f.startswith(".") or
                        f.endswith(".") or " " in f):
                    continue
                have_deps.append(f)
    result = preprocess(file_contents, {
        "system.program_compiler_name": translator_version,
        "___known_available_packages": have_deps,
        "HORP_INFO_PROJECT_DIR": project_base_dir,
        "HORP_INFO_MODNAME": module_name,
        "HORP_INFO_PKGNAME": package_name,
    }, debug=False)
    return result


#!/usr/bin/python3

VERSION="2022-09-16"

import os
import platform
import shutil
import subprocess
import sys
import tempfile


translated_files = {}

DEBUG_ENABLE = False
DEBUG_ENABLE_CONTENTS = False
DEBUG_ENABLE_TYPES = False


class RegisteredType:
    def __init__(self, type_name, module_path, library_name):
        self.module = module_path
        self.libname = library_name
        self.name = type_name
        self.init_code = ""
        self.funcs = {}


known_types = {}


def register_type(type_name, module_path, library_name):
    global known_types
    library_name_part = ""
    if library_name is not None:
        library_name_part = "@" + library_name
    if module_path + "." + type_name + library_name_part in known_types:
        raise ValueError("found duplicate type " +
            module_path + "." + type_name)
    known_types[module_path + "." + type_name + library_name_part] = (
        RegisteredType(type_name, module_path, library_name)
    )
    if DEBUG_ENABLE and DEBUG_ENABLE_TYPES:
        print("tools/translator.py: debug: registered type " +
            module_path + "." + type_name + library_name_part)


def get_type(type_name, module_path, library_name):
    if library_name is None:
        return known_types[module_path + "." + type_name]
    return known_types[module_path + "." + type_name + "@" +
        library_name]


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

    if s[0] == "'" or s[0] == '"':
        end_marker = s[0]
        next_escaped = False
        i = 1
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
                i += 1
                break
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
    token_count = 0
    bracket_nesting = 0
    for t in s:
        token_count += 1
        if t in ["(", "[", "{"]:
            bracket_nesting += 1
        if t in [")", "]", "}"]:
            bracket_nesting -= 1
        if bracket_nesting == 0 and \
                (t.endswith("\n") or t.endswith("\r")):
           return s[:token_count]
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
                    "}", "]", ")"} and \
                not is_whitespace_token(token) and \
                not is_whitespace_token(prevtoken):
            result += " "
        result += token
        prevtoken = token
    return result


def translate_expression_tokens(s, module_name, library_name,
        parent_statement=None, known_imports=None):
    # Remove "new" since Python just omits that:
    i = 0
    while i < len(s):
        if s[i] == "new":
            s = s[:i] + s[i + 1:]
            continue
        i += 1
    # Translate XYZ.as_str() to str(XYZ)
    replaced_one = True
    while replaced_one:
        replaced_one = False
        i = 0
        while i + 2 < len(s):
            if (i > 0 and s[i - 1] == "." and
                    s[i] == "as_str" and s[i + 1] == "(" and
                    s[i + 2] == ")"):
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
                s = s[:i - 1] + s[i + 2:]
                inserted_left_end = False
                bdepth = 0
                i -= 2
                while i > 0:
                    if s[i] in {")", "]", "}"}:
                        bdepth += 1
                    elif s[i] in {"(", "[", "{"}:
                        bdepth -= 1
                    if (s[i] != "." and
                            not is_keyword_or_idf(s[i]) and
                            bdepth <= 0):
                        s = s[:i + 1] + ["str", "("] + s[i + 1:]
                        inserted_left_end = True
                        break
                    i -= 1
                assert(inserted_left_end)
                break
            i += 1
    return s


def translate(s, module_name, library_name, parent_statement=None,
        extra_indent="", folder_path="", repo_folder="",
        known_imports=None, translate_file_queue=None):
    if parent_statement is None and DEBUG_ENABLE:
        print("tools/translator.py: debug: translating " +
            "module \"" + modname + "\" in folder: " + folder_path)
    if known_imports is None:
        known_imports = {}
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    result = ""
    tokens = tokenize(s)
    statements = split_toplevel_statements(tokens)
    for statement in statements:
        while is_whitespace_token(statement[-1]):
            statement = statement[:-1]
        indent = extra_indent
        if is_whitespace_token(statement[0]):
            indent += statement[0]
            statement = statement[1:]
            while is_whitespace_token(statement[0]):
                statement = statement[1:]
        if statement[0] == "var":
            statement_cpy = list(statement)
            statement = statement[1:]
            while is_whitespace_token(statement[0]):
                statement = statement[1:]
            i = 1
            while i < len(statement) and statement[i] != "=":
                i += 1
            if i < len(statement) and statement[i] == "=":
                statement = statement[:i + 1] + translate_expression_tokens(
                    statement[i + 1:], module_name, library_name,
                    parent_statement=statement_cpy,
                    known_imports=known_imports)
            if parent_statement != None and \
                    parent_statement[0] == "type":
                type_name = parent_statement[2]
                get_type(type_name, module_name, library_name).\
                    init_code += indent +\
                    ("\n" + indent).join((
                        "self." +
                        untokenize(statement) + "\n"
                    ).splitlines())
                continue
        elif statement[0] == "import":
            assert(len(statement) >= 2 and statement[1].strip() == "")
            i = 2
            while i + 2 < len(statement) and statement[i + 1] == ".":
                i += 2
            import_module = "".join([
                part.strip() for part in statement[1:i + 1]
                if part.strip() != ""
            ])
            import_library = None
            i += 1
            while i < len(statement) and statement[i].strip() == "":
                i += 1
            if i < len(statement) and statement[i] == "from":
                i += 1
                while i < len(statement) and statement[i].strip() == "":
                    i += 1
                import_library = statement[i]
                while i + 2 < len(statement) and statement[i + 1] == ".":
                    import_library += "." + statement[i + 2]
                    i += 2
            target_path = import_module.replace(".", "/") + ".h64"
            python_module = import_module
            if import_library != None:
                python_module = "horse_modules." + (
                    import_library.replace(".", "_")
                ) + "." + python_module
                target_path = ("horse_modules/" +
                    import_library
                ) + "/" + target_path
            target_path = os.path.normpath(
                os.path.join(os.path.abspath(
                repo_folder), target_path))
            known_imports[import_module] = {
                "library": import_library,
                "module": import_module,
                "python-module": python_module,
                "path": target_path,
            }
            result += "import " + python_module + "\n"
            translate_file_queue.append(
                (target_path,
                import_module, os.path.dirname(target_path),
                import_library)
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
                    import_library)
                )
            continue
        elif statement[0] == "func":
            statement_cpy = list(statement)
            statement[0] = "def"
            i = 1
            while statement[i] != "{":
                i += 1
            i += 1
            assert(statement[-1] == "}")
            contents = (
                statement[i:-1]
            )
            assert(statement[1].strip() == "")
            type_module = None
            type_name = None
            type_library = None
            type_python_module = None
            i = 2
            name = statement[2]
            if statement[3] == ".":
                type_name = ""
                name = ""
                i = 2
                while i + 2 < len(statement) and statement[i + 1] == ".":
                    if len(type_name) > 0:
                        type_name += "."
                    type_name += statement[i]
                    name = statement[i + 2]
                    i += 2
                for import_mod_name in known_imports:
                    if type_name.startswith(import_mod_name + "."):
                        type_module = import_mod_name
                        type_name = type_name[len(type_module) + 1:]
                        type_library = known_imports[type_module]["library"]
                        type_python_module = known_imports[
                            type_module]["python-module"]
            if type_module is None:
                type_module = module_name
                type_library = library_name
            argument_tokens = ["(", ")"]
            if statement[i] == "(":
                istart = i
                bdepth = 1
                i += 1
                while statement[i] != ")" or bdepth > 1:
                    if statement[i] == "(":
                        bdepth += 1
                    elif statement[i] == ")":
                        bdepth -= 1
                assert(statement[i] == ")")
                argument_tokens = statement[istart:i + 1]
            translated_contents = translate(
                untokenize(contents), module_name, library_name,
                parent_statement=statement_cpy,
                extra_indent=(indent + ("    "
                    if type_name is not None else "")),
                folder_path=folder_path,
                repo_folder=repo_folder,
                known_imports=known_imports,
                translate_file_queue=translate_file_queue
            )
            if type_name is None:
                result += (indent + "def " + name +
                    untokenize(argument_tokens) + ":\n")
                result += translated_contents + "\n"
            else:
                regtype = get_type(type_name, type_module, type_library)
                regtype.funcs[name] = {
                    "arguments": argument_tokens,
                    "name": name,
                    "code":
                    "    \n".join(translated_contents.splitlines()) + "\n"
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
            register_type(statement[2], module_name, library_name)
            translated_contents = translate(
                untokenize(contents), module_name, library_name,
                parent_statement=statement_cpy,
                extra_indent=(indent + "    "),
                folder_path=folder_path,
                repo_folder=repo_folder,
                known_imports=known_imports,
                translate_file_queue=translate_file_queue
            )
            continue
        result += indent + untokenize(translate_expression_tokens(
            statement, module_name, library_name,
            parent_statement=parent_statement,
            known_imports=known_imports)) + "\n"
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    target_file = None
    i = 0
    while i < len(args):
        if args[i].startswith("-"):
            if args[i] == "--help":
                print("Usage: translator.py ...path-to-h64-file...")
            elif (args[i] == "--version" or args[i] == "-v" or
                    args[i] == "-V"):
                print("tools/translator.py version " + VERSION)
            elif args[i] == "--debug":
                DEBUG_ENABLE = True
                DEBUG_ENABLE_TYPES = True
                DEBUG_ENABLE_CONTENTS = True
        elif target_file is None:
            target_file = args[i]
        i += 1
    if target_file is None:
        raise RuntimeError("please provide target file argument")
    modname = (os.path.basename(target_file).
        rpartition(".h64")[0].strip())
    modfolder = os.path.abspath(os.path.dirname(target_file))
    if (not os.path.exists(target_file) or
            os.path.isdir(target_file) or
            not target_file.endswith(".h64") or
            len(modname) == 0 or "-" in modname or
            "." in modname):
        raise IOError("missing target file, " +
            "or target file not a .h64 file with proper " +
            "module name")
    repo_folder = modfolder
    while True:
        repo_folder_files = os.listdir(repo_folder)
        if ("horse_modules" in repo_folder_files or
                ".git" in repo_folder_files):
            break
        repo_folder = os.path.normpath(os.path.abspath(repo_folder))
        if "windows" in platform.system().lower():
            repo_folder = repo_folder.replace("\\", "/")
        while "//" in repo_folder:
            repo_folder = repo_folder.replace("//", "/")
        if repo_folder.endswith("/") and (
                "windows" not in platform.system().lower() or
                len(repo_folder) > 3) and repo_folder != "/":
            repo_folder = repo_folder[:-1]
        if (("windows" in platform.system().lower() and
                len(repo_folder) == 3) or
                "windows" not in platform.system().lower() and
                repo_folder == "/"):
            raise RuntimeError("failed to detect repository folder")
        repo_folder = os.path.normpath(os.path.abspath(
            os.path.join(repo_folder, "..")))
    if DEBUG_ENABLE:
        print("tools/translator.py: debug: " +
            "detected repository folder: " +
            repo_folder)
    translate_file_queue = [
        (os.path.normpath(os.path.abspath(target_file)),
        modname, modfolder, None)]
    mainfilepath = translate_file_queue[0][0]
    while len(translate_file_queue) > 0:
        (target_file, modname, modfolder,
         library_name) = translate_file_queue[0]
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
                new_modname, modfolder, library_name))
        contents = None
        with open(target_file, "r", encoding="utf-8") as f:
            contents = f.read()
        contents_result = (
            translate(contents, modname, library_name,
                folder_path=modfolder, repo_folder=repo_folder,
                translate_file_queue=translate_file_queue))
        translated_files[target_file] = {
            "module-name": modname,
            "library-name": library_name,
            "module-folder": modfolder,
            "path": target_file,
            "disk-fake-folder": os.path.dirname(
                ("" if library_name is None else
                "horse_modules/" +
                library_name.replace(".", "_") + "/") +
                modname.replace(".", "/")),
            "output": contents_result
        }
    for translated_file in translated_files:
        contents_result = translated_files[translated_file]["output"]
        for regtype in known_types.values():
            if (regtype.module != translated_files
                    [translated_file]["module-name"] or
                    regtype.libname != translated_files
                    [translated_file]["library-name"]):
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
        if DEBUG_ENABLE:
            print("tools/translator.py: debug: writing result to: " +
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
            with open(os.path.join(output_folder, subfolder,
                    name + ".py"), "w", encoding="utf-8") as f:
                f.write(contents)
            if translated_files[translated_file]["path"] == mainfilepath:
                run_py_path = os.path.join(output_folder, subfolder,
                    name + ".py")
        result = subprocess.run([
            sys.executable, run_py_path
        ])
        returncode = result.returncode
    finally:
        shutil.rmtree(output_folder)
    sys.exit(returncode)


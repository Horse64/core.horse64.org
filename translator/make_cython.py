#!/usr/bin/env python3
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

from Cython.Build import cythonize
import hashlib
import os
import platform
import subprocess
import sys

MY_DIR = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(1, os.path.join(MY_DIR,
    "translator_modules"))

def filehash(path):
    contents = None
    with open(path, "rb") as f:
        contents = f.read()
    return str(hashlib.md5(contents).hexdigest())

if __name__ == "__main__":
    print("Building Cython modules for translator...")
    force_rebuild = False
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--force-rebuild":
            force_rebuild = True
        elif sys.argv[i] == "--":
            break
        elif sys.argv[i] in ["--help", "-?", "-h"]:
            print("make_cython tool to build Cython parts of translator")
            print("Options:")
            print("")
            print("    --help")
            print("    --force-rebuild")
            print("    --version")
            sys.exit(0)
        elif sys.argv[i] in ["--version", "-v", "-V"]:
            print("make_cython version: 2024-08-09")
            sys.exit(0)
        i += 1
    items = [os.path.join(MY_DIR, "..",
        "translator", "translator_main.pyx")]
    for p in os.listdir(os.path.join(MY_DIR, "..",
            "translator", "translator_modules")):
        if not p.endswith(".pyx"):
            continue
        fullp = os.path.join(MY_DIR, "..", "translator",
            "translator_modules", p)
        items.append(fullp)
    shared_flags = ["-shared"]
    symlink_from = None
    lib_ext = ".so"
    if platform.system().lower() == "darwin":
        lib_ext = ".dylib"
        symlink_from = ".so"  # Work around Python module loader bug. Sigh.
        shared_flags = ["-dynamiclib",
            "-undefined", "dynamic_lookup"]
    elif platform.system().lower() == "windows":
        lib_ext = ".dll"
    for fullp in items:
        fullp_hash = fullp.rpartition(".pyx")[0] + ".md5.txt"
        fullp_c = fullp.rpartition(".pyx")[0] + ".c"
        fullp_lib = fullp.rpartition(".pyx")[0] + lib_ext
        fullp_lib_link = None
        if symlink_from != None:
            fullp_lib_link = fullp.rpartition(".pyx")[0] + symlink_from

        source_hash = filehash(fullp)
        if (os.path.exists(fullp_hash) and
                os.path.exists(fullp_lib)):
            old_hash = None
            with open(fullp_hash, "r", encoding="utf-8") as f:
                old_hash = f.read().strip()
            if old_hash == source_hash:
                print("Hash match for " + fullp + "!")
                if force_rebuild:
                    print("Rebuilding anyway due to --force-rebuild "
                        "option.")
                else:
                    if fullp_lib_link != None:
                        if os.path.exists(fullp_lib_link):
                            os.remove(fullp_lib_link)
                        os.symlink(fullp_lib, fullp_lib_link)
                    continue
        subprocess.check_output([
            "cython", "-o", fullp_c,
            "-I", os.path.join(MY_DIR, "translator_modules"),
            fullp
        ])
        py_include = None
        if (platform.system().lower() == "darwin" or
                not os.path.exists("/usr/include")):
            # Headers are in a non-Linux location, therefore
            # use python3-config to find out where:

            include_flags = subprocess.check_output([
                "python3-config", "--include"
            ])
            if type(include_flags) in [bytes, bytearray]:
                include_flags = include_flags.decode("utf-8", "replace")
            switch_idx = include_flags.find("-I")
            if switch_idx < 0:
                raise RuntimeError("-I switch not found in "
                    "python3-config output")
            path = include_flags[switch_idx + len("-I"):]
            if " -" in path:
                path = path.partition(" -")[0]
            # FIXME: handle spaces properly here.

            if (not path.startswith("/") or
                    not os.path.exists(path)):
                raise RuntimeError("Obtained Python dev include "
                    "path appears to be invalid: " + path)

            py_include = path
        else:
            # Find the newest headers inside /usr/include that we can.
            py_include = "/usr/include/" + list(reversed(sorted(
                [l for l in os.listdir("/usr/include")
                if l.startswith("python")])))[0]
        print("Compiling changed file " + fullp + "...")
        print("*** WARNING, THIS MAY TAKE VERY LONG. ON SLOW MACHINES, "
            "IT MAY TAKE HALF AN HOUR OR LONGER. ***", flush=True)
        subprocess.check_output([
            "gcc"] + shared_flags + ["-pthread", "-fPIC", "-fwrapv",
            "-Ofast", "-Wall", "-fno-strict-aliasing",
            "-I" + py_include, "-o", fullp_lib,
            fullp_c
        ], stderr=subprocess.STDOUT)
        if fullp_lib_link != None:
            if os.path.exists(fullp_lib_link):
                os.remove(fullp_lib_link)
            os.symlink(fullp_lib, fullp_lib_link)
        with open(fullp_hash, "w", encoding="utf-8") as f:
            f.write(source_hash)


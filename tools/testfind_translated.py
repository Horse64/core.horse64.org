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

import os
import platform
import subprocess
import sys
import textwrap

from translator_runtime_helpers import _process_run

my_dir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))


if __name__ == "__main__":
    debug_cmd = False
    args = sys.argv[1:]
    if "--help" in args:
        print("\n".join(textwrap.wrap("Note: "
            "this is a script to discover tests when nothing "
            "is bootstrapped yet, which allows running them "
            "without needing something horse64-based just "
            "for the discovery.", width=75,
            subsequent_indent='  ')))
        print("")
        print("Usage: tools/testfind_translated.py [..options..] folder")
        print("")
        print("Available options:")
        print("   --debug-cmd  Print the exact command run")
        print("   --help       Show this help text")
        sys.exit(0)
    if "--version" in args:
        print("tools/testfind_translated.py V1")
        sys.exit(0)
    translator_options = []
    discovery_path = None
    i = -1
    while i + 1 < len(args):
        i += 1
        arg = args[i]
        if arg.startswith("-"):
            if arg == "--debug-cmd":
                debug_cmd = True
            elif arg == "--tl-opt":
                if (i + 1 > len(args) or
                        args[i + 1].startswith("-")):
                    print("tools/testfind_translated.py: "
                        "error: missing argument " +
                        "for --tl-opt")
                    sys.exit(1)
                switch = args[i + 1]
                switch_option = None
                if "," in switch:
                    switch_option = switch.partition(",")[2]
                    switch = switch.partition(",")[0]
                translator_options.append("--" + switch)
                if switch_option != None:
                    translator_options.append(switch_option)
                i += 1
                continue
            else:
                print("tools/testfind_translated.py: error: " +
                    "unknown option: " + str(arg))
                sys.exit(1)
            continue
        dpath = os.path.normpath(os.path.abspath(arg))
        if not os.path.exists(dpath) or not os.path.isdir(dpath):
            print("tools/testfind_translated.py: error: " +
                "no such path or not a dir: " + arg)
            sys.exit(1)
        discovery_path = dpath
        break
    if discovery_path is None:
        print("tools/testfind_translated.py: error: " +
            "missing discovery folder argument")
        sys.exit(1)

    test_paths = []
    for (base, dirs, files) in os.walk(discovery_path):
        base = os.path.normpath(os.path.abspath(base))
        if not base.startswith(discovery_path):
            print("tools/testfind_translated.py: warning: " +
                "unexpectedly ended up in outside folder, skipping: " +
                str(base))
        base_relpath = base[len(discovery_path):]
        while (base_relpath.startswith("/") or
                (platform.system().lower() == "windows" and
                base_relpath.startswith("\\"))):
            base_relpath = base_relpath[1:]
        if len(set(base_relpath.replace("\\", "/").split("/")).\
                intersection({".git", "horse_modules",
                "__pycache__", ".hg"})) > 0:
            continue
        for f in files:
            if f.startswith("test_") and f.endswith(".h64"):
                test_paths.append(os.path.join(base, f))
    test_paths = sorted(test_paths)

    had_error = False
    for test_path in test_paths:
        print("\x1B[1m==> RUNNING TEST ==> \x1B[0m" + str(test_path))
        cmd = os.path.join(my_dir, "translator.py")
        cmd_args = (["--as-test", "--paranoid"] +
            translator_options + ["--", test_path])
        if debug_cmd:
            print("tools/testfind_translated.py: debug: exact cmd: " +
                str((cmd, cmd_args)))
        failed = False
        try:
            result = _process_run(
                cmd, args=cmd_args,
                print_output=True)
        except Exception as e:
            failed = True
        sys.stdout.flush()
        sys.stderr.flush()
        if failed:
            print("\x1B[1m!!!! TEST FAILED !!!!\x1B[0m")
            had_error = True
        else:
            print("==> TEST SUCCESSFUL.")
    if had_error:
        print("\x1B[31;40;1mFAILURE trying to run tests.\x1B[0m")
        sys.exit(1)
    else:
        print("\x1B[32;40;1mSuccess and all tests done.\x1B[0m")
        sys.exit(0)

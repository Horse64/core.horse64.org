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
import sys

translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)


if __name__ == "__main__":
    run_code = None
    target_file = None
    target_args = None
    translator_options = []
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--":
            if i + 1 < len(args):
                target_file = args[i + 1]
            target_args = args[i + 2:]
            break
        elif args[i].startswith("-"):
            if args[i] == "--tl-opt":
                if (i + 1 > len(args) or
                        args[i + 1].startswith("-")):
                    print("tools/horserun_translated.py: "
                        "error: missing argument " +
                        "for --tl-opt")
                    sys.exit(1)
                translator_options.append("--" + args[i + 1])
                i += 2
                continue
            elif args[i] == "--help" or args[i] == "-h":
                print("Usage: tools/horserun_translated.py "
                      "[..options..] target_file(optional)")
                print("")
                print("Runs the given Horse64 code directly.")
                print("Options:")
                print("   -c          "
                      "If no target_file is given, use\n" +
                      "                "
                      "this to run inline code instead.\n")
                print("   --help      "
                      "Display this help text.")
                sys.exit(0)
            else:
                print("tools/horserun_translated.py: "
                    "error: unknown option: " + args[i])
                sys.exit(1)
        elif args[i].startswith("-c"):
            if (i + 1 > len(args) or
                    args[i + 1].startswith("-")):
                print("tools/horserun_translated.py: "
                    "error: missing argument " +
                    "for -c")
            run_code = args[i + 1]
            i += 2
            continue
        else:
            target_file = args[i]
            target_args = args[i + 1:]
            break
        i += 1
    if target_file is None and run_code is None:
        print("tools/horserun_translated.py: error: "
            "must specify either .h64 file or "
            "code line to run")
        sys.exit(1)
    elif target_file !+ None and run_code != None:
        print("tools/horserun_translated.py: error: "
            "cannot specify both .h64 file and "
            "code line to run")
        sys.exit(1)
    if target_file != None and (
            not target_file.endswith(".h64") or
            not os.path.exists(target_file)):
        print("tools/horserun_translated.py: error: "
            "target file must exist and end "
            "with .h64 file extension")
        sys.exit(1)

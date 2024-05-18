#!/usr/bin/env python3
# Copyright (c) 2020-2024, ellie/@ell1e & Horse64 authors (see AUTHORS.md).
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

import os
import subprocess
import sys

my_dir = os.path.abspath(os.path.dirname(
    os.path.realpath(__file__)
))

def run_horsec(is_moosec=False):
    args = sys.argv[1:]
    use_paranoid_translator = False
    use_debug = False
    use_debug_python_output = False
    use_debug_keep_files = False
    while True:
        if (not use_debug and len(args) > 0 and
                args[0] == "--debug-translator"):
            use_debug = True
            args = args[1:]
        elif (not use_debug_python_output and len(args) > 0 and
                args[0] == "--debug-translator-python-output"):
            use_debug_python_output = True
            args = args[1:]
        elif (not use_debug_keep_files and len(args) > 0 and
                args[0] == "--debug-translator-keep-files"):
            use_debug_keep_files = True
            args = args[1:]
        elif (not use_paranoid_translator and len(args) > 0 and
                args[0] == "--paranoid-translator"):
            use_paranoid_translator = True
            args = args[1:]
        else:
            break
    compiler_path = os.path.join(my_dir, "..",
        "src", "compiler", "main.h64")
    if is_moosec:
        compiler_path = os.path.join(my_dir, "..",
            "src", "compiler", "moose64", "main.h64")
    process = subprocess.Popen([
        sys.executable,
        os.path.join(my_dir, "translator.py")] +
        (["--paranoid"] if use_paranoid_translator else []) +
        (["--debug"] if use_debug else []) +
        (["--debug-python-output"] if use_debug_python_output else []) +
        (["--keep-files"] if use_debug_keep_files else []) +
        [compiler_path] + args)
    exit_code = process.wait()
    sys.exit(exit_code)

if __name__ == "__main__":
    run_horsec()


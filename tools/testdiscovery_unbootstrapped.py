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
import subprocess
import sys
import textwrap

from translator_runtime_helpers import _process_run

my_dir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--help" in args:
        print("\n".join(textwrap.wrap(
            "This is a script to discover tests when nothing "
            "is bootstrapped yet, which allows running them "
            "without needing something horse64-based just "
            "for the discovery.")
        print("Usage: just specify the folder as argument.")
        sys.exit(0)
    if "--version" in args:
        print("tools/testdiscovery_unbootstrapped.py V1")
        sys.exit(0)
    discovery_path = None
    for arg in args:
        if arg.startswith("-"):
            print("tools/testdiscovery_unbootstrapped.py: error: " +
                "unknown option: " + str(arg))
        dpath = os.path.normpath(os.path.abspath(arg))
        if not os.path.exists(dpath) or not os.path.isdir(dpath):
            print("tools/testdiscovery_unbootstrapped.py: error: " +
                "no such path or not a dir: " + arg)
        discovery_path = dpath
        break

    test_paths = []
    for (base, dirs, files) in os.walk(discovery_path):
        for f in files:
            if f.startswith("test_") and f.endswith(".h64"):
                test_paths.append(os.path.join(base, f))
    test_paths = sorted(test_paths)

    for test_path in test_paths:
        print("==> RUNNING TEST ==> " + str(test_path))
        result = _process_run([
            os.path.join(my_dir,
            "translator.py"), args=["--as-test",
            "--", test_path], run_in_dir=os.path.dirname(test_path),
            print_output=True])
        print("==> TEST SUCCESSFUL.")
    print("All tests done.")

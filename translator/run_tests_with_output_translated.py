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

import os
import shutil
import subprocess
import sys
import tempfile
import time

MY_DIR = os.path.abspath(os.path.dirname(__file__))

def prepare_test_dir(d, only_delete=False):
    if not os.path.isdir(d):
        return
    if not os.path.isdir(os.path.join(d,
            "horse_modules")):
        return
    modules_target = os.path.join(d, "horse_modules")

    print("*** run_tests_with_output_translated.py PREP DIR: " + d)
    # Clean out old contents:
    for entry in os.listdir(modules_target):
        entryp = os.path.join(modules_target, entry)
        if not os.path.isdir(entryp):
            continue
        print("Removing: " + entryp)
        shutil.rmtree(entryp)
    if only_delete:
        return
    main_modules_dir = os.path.join(MY_DIR, "..",
        "horse_modules")
    for entry in os.listdir(main_modules_dir):
        entrysource = os.path.join(
            main_modules_dir, entry)
        entrytarget = os.path.join(modules_target, entry)
        if not os.path.isdir(entrysource):
            continue
        if not "." in entry or entry.startswith("."):
            continue
        print("Copying " + entrysource + " -> " + entrytarget)
        shutil.copytree(entrysource, entrytarget)
    entrysource = os.path.join(MY_DIR, "..")
    entrytarget = os.path.join(modules_target, "core.horse64.org")
    temptarget = tempfile.mkdtemp()
    temptarget = os.path.join(temptarget, "module")
    print("Copying " + entrysource + " -> " + entrytarget +
        " (via " + str(temptarget) + ")")
    try:
        shutil.copytree(entrysource, temptarget)
        shutil.copytree(temptarget, entrytarget)
    finally:
        shutil.rmtree(temptarget)

def prepare_test_dirs(only_delete=False):
    fail_dirs = [os.path.join(MY_DIR, "..", "tests",
        "compile-fail", l) for l in
        os.listdir(os.path.join(MY_DIR,
            "..", "tests", "compile-fail"))]
    fail_dirs = [l for l in fail_dirs
        if os.path.isdir(l)]
    success_dirs = []
    for d in fail_dirs + success_dirs:
        prepare_test_dir(d, only_delete=only_delete)
    return [success_dirs, fail_dirs]

def prepare_test_files():
    def expand_folder_to_tests(ds):
        result = []
        for d in ds:
            dlist = os.listdir(d)
            for entry in dlist:
                entryp = os.path.join(d, entry)
                outputfname = ("expected_output_" +
                    entry.rpartition(".h64")[0] + ".txt"
                )
                if os.path.isdir(entryp) or\
                        not entry.startswith("test_") or\
                        not entry.endswith(".h64") or \
                        not outputfname in dlist:
                    continue
                result.append([entryp,
                    os.path.join(d, outputfname)])
        return result
    dirs = prepare_test_dirs()
    return [expand_folder_to_tests(dirs[0]),
        expand_folder_to_tests(dirs[1])]

def run_tests_without_cleanup():
    files = prepare_test_files()
    error_count = 0
    print("*** run_tests_with_output_translated.py TESTS to work:")

    print("*** run_tests_with_output_translated.py TESTS to not work:")
    for fail_file in files[1]:
        expected_output = None
        with open(fail_file[1], "r", encoding="utf-8") as f:
            expected_output = f.read().strip()
        cmd = [sys.executable, os.path.join(
            "translator", "horsec.py"), "compile",
            "--stage", "transformed-code", "--",
            fail_file[0]]
        print("Running test: " + str(cmd))
        result = None
        try:
            result = subprocess.check_output(cmd,
                cwd=os.path.join(MY_DIR, ".."),
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            result = e.output
        if type(result) != str:
            result = result.decode("utf-8", "replace")
        if result.lower().find(expected_output.lower()) < 0:
            print("!! TEST FAILED. DIDN'T FIND EXPECTED OUTPUT. !!")
            print("Failed output:\n" + result)
            error_count += 1
        else:
            print("OK, test succeeded.")
    if error_count > 0:
        print("*** run_tests_with_output_translated.py TESTS FAIL, " +
            str(error_count) + " broke.")
        sys.exit(1)
    else:
        print("*** run_tests_with_output_translated.py TESTS ALL OK.")
        sys.exit(0)

def run_tests():
    try:
        run_tests_without_cleanup()
    finally:
        time.sleep(1)
        prepare_test_dirs(only_delete=True)

if __name__ == "__main__":
    run_tests()


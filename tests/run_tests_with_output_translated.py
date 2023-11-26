#!/usr/bin/python3

import os
import shutil
import subprocess
import sys
import tempfile

MY_DIR = os.path.abspath(os.path.dirname(__file__))

def prepare_test_dir(d):
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
    shutil.copytree(entrysource, temptarget)
    shutil.copytree(temptarget, entrytarget)

def prepare_test_dirs():
    fail_dirs = [os.path.join(MY_DIR, "..", "tests",
        "compile-fail", l) for l in
        os.listdir(os.path.join(MY_DIR,
            "..", "tests", "compile-fail"))]
    fail_dirs = [l for l in fail_dirs
        if os.path.isdir(l)]
    success_dirs = []
    for d in fail_dirs + success_dirs:
        prepare_test_dir(d)
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

def run_tests():
    files = prepare_test_files()
    error_count = 0
    print("*** run_tests_with_output_translated.py TESTS to work:")

    print("*** run_tests_with_output_translated.py TESTS to not work:")
    for fail_file in files[1]:
        expected_output = None
        with open(fail_file[1], "r", encoding="utf-8") as f:
            expected_output = f.read()
        cmd = [sys.executable, os.path.join(
            "tools", "horsec.py"), "compile",
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
        if not expected_output.lower() in result.lower():
            print("!! TEST FAILED. DIDN'T FIND EXPECTED OUTPUT. !!")
            print("Failed output:\n" + result)
        else:
            print("OK, test succeeded.")
        error_count += 1
    if error_count > 0:
        print("*** run_tests_with_output_translated.py TESTS FAIL, " +
            str(error_count) + " broke.")
        sys.exit(1)
    else:
        print("*** run_tests_with_output_translated.py TESTS ALL OK.")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()


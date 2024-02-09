#!/usr/bin/python3

from Cython.Build import cythonize
import hashlib
import os
import subprocess

MY_DIR = os.path.abspath(os.path.dirname(__file__))

def filehash(path):
    contents = None
    with open(path, "rb") as f:
        contents = f.read()
    return str(hashlib.md5(contents).hexdigest())

if __name__ == "__main__":
    print("Building Cython modules for translator...")
    items = [os.path.join(MY_DIR, "..",
        "translator", "translator_main.pyx")]
    for p in os.listdir(os.path.join(MY_DIR, "..",
            "translator", "translator_modules")):
        if not p.endswith(".pyx"):
            continue
        fullp = os.path.join(MY_DIR, "..", "translator",
            "translator_modules", p)
        items.append(fullp)
    for fullp in items:
        fullp_hash = fullp.rpartition(".pyx")[0] + ".md5.txt"
        fullp_c = fullp.rpartition(".pyx")[0] + ".c"
        fullp_so = fullp.rpartition(".pyx")[0] + ".so"

        source_hash = filehash(fullp)
        if (os.path.exists(fullp_hash) and
                os.path.exists(fullp_so)):
            old_hash = None
            with open(fullp_hash, "r", encoding="utf-8") as f:
                old_hash = f.read().strip()
            if old_hash == source_hash:
                print("Hash match for " + fullp + "!")
                continue
        subprocess.check_output([
            "cython", "-o", fullp_c, fullp
        ])
        py_include = "/usr/include/" + list(reversed(sorted(
            [l for l in os.listdir("/usr/include")
            if l.startswith("python")])))[0]
        print("Compiling changed file " + fullp + "...")
        subprocess.check_output([
            "gcc", "-shared", "-pthread", "-fPIC", "-fwrapv",
            "-Ofast", "-Wall", "-fno-strict-aliasing",
            "-I" + py_include, "-o", fullp_so,
            fullp_c
        ], stderr=subprocess.STDOUT)
        with open(fullp_hash, "w", encoding="utf-8") as f:
            f.write(source_hash)


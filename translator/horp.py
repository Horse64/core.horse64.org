#!/usr/bin/env python3
# Copyright (c) 2024, ellie/@ell1e & Horse64 authors (see AUTHORS.md).
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
import shlex
import shutil
import sys

my_dir = os.path.abspath(os.path.dirname(
    os.path.realpath(__file__)
))

def check_if_pkg_local_linked(pkg_name):
    if (not os.path.exists(os.path.join(my_dir, "..",
            "horse_modules", pkg_name)) or
            not os.path.islink(os.path.join(my_dir, "..",
            "horse_modules", pkg_name))) and \
            os.path.exists(os.path.join(my_dir,
            "..", "..", pkg_name)):
        return False
    return True

def link_local_pkg(pkg_name):
    if os.path.exists(os.path.join(my_dir, "..", "..",
            pkg_name)):
        if os.path.exists(os.path.join(my_dir, "..",
                "horse_modules", pkg_name)):
            if os.path.islink(os.path.join(my_dir, "..",
                    "horse_modules", pkg_name)):
                os.unlink(os.path.join(my_dir, "..",
                    "horse_modules", pkg_name))
            else:
                shutil.rmtree(os.path.join(my_dir, "..",
                    "horse_modules", pkg_name))
        if not os.path.exists(os.path.join(my_dir, "..",
                "horse_modules")):
            os.mkdir(os.path.join(my_dir, "..",
                "horse_modules"))
        os.system("ln -s " + shlex.quote(
                os.path.join("..", "..", pkg_name)) + " " +
            shlex.quote(os.path.join(my_dir, "..",
            "horse_modules", pkg_name),
            ))

def run_horp(args):
    keep_files = False
    symlink_existing = False
    while True:
        if len(args) > 0 and args[0] == "--force-link":
            symlink_existing = True
            args = args[1:]
            continue
        elif len(args) > 0 and args[0] == "--keep-files":
            keep_files = True
            args = args[1:]
            continue
        break
    offer_link_pkgs = [
        "horp.horse64.org",
        "hvm.horse64.org",
        "m64.horse64.org",
        "spew3d.horse64.org",
    ]
    for link_pkg in offer_link_pkgs:
        if not check_if_pkg_local_linked(link_pkg):
            if not symlink_existing:
                print("horp.py: warning: Found neighboring install "
                    "of '" + link_pkg + "' at " +
                    os.path.abspath(os.path.join(my_dir, "..",
                        "..", "..", link_pkg)) + " but it's "
                    "not linked into "
                    "the horse_modules folder. Use --force-link "
                    "to change " + os.path.abspath(os.path.join(
                        my_dir, "horse_modules", link_pkg)) + " to "
                    "link to this local install.",
                    file=sys.stderr, flush=True)
            else:
                if os.path.exists(os.path.join(my_dir, "..", "..",
                        link_pkg)):
                    link_local_pkg(link_pkg)
    translator_opt_str = ""
    if keep_files:
        translator_opt_str += " --keep-files"
    horp_cmd = (shlex.quote(sys.executable) + " " +
        shlex.quote(os.path.join(my_dir,
        "translator.py")) + (" " +
        translator_opt_str.strip()).rstrip() + " " +
        os.path.join(my_dir, "..", "horse_modules",
            "horp.horse64.org", "src", "main.h64"))
    for arg in args:
        horp_cmd += " " + shlex.quote(arg)
    val = os.system(horp_cmd)
    return val

if __name__ == "__main__":
    sys.exit(run_horp(sys.argv[1:]))


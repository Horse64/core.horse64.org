#!/usr/bin/python3
# Copyright (c) 2024, ellie/@ell1e & Horse64 authors (see AUTHORS.md).
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

import datetime
import os
import shutil
import subprocess
import sys

mydir = os.path.abspath(os.path.dirname(__file__))

def are_files_different(p1, p2):
    if not os.path.exists(p1) and os.path.exists(p2):
        return True
    if os.path.exists(p1) and not os.path.exists(p2):
        return True
    content1 = None
    content2 = None
    with open(p1, "r", encoding="utf-8") as f:
        content1 = f.read()
    with open(p2, "r", encoding="utf-8") as f:
        content2 = f.read()
    return (content1 != content2)

if __name__ == "__main__":
    # First, parse command line options:
    dry_run = False
    dco_signature = ""
    args = sys.argv[1:]
    index = -1
    while (index + 1 < len(args)):
        index += 1
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
            continue
        if arg == "--help":
            print("Helper tool to update all Horse64 repositories,\n"
                "assuming sibling repositories are cloned into the\n"
                "parent folder with unchanged folder names.\n"
                "(If you don't know what any of this means, just\n"
                "don't use it, it's meant for maintainer work.)")
            sys.exit(0)
        if arg in ["-v", "--version", "-V"]:
            print("Version 2023.9")
            sys.exit(0)
        if arg == "--dco-signature" and index + 1 < len(args):
            dco_signature = args[index + 1]
            index += 1
            continue
        raise RuntimeError("Error: unknown argument: " + str(arg))
    if (not "@" in dco_signature or
            not dco_signature.endswith(">") or
            not dco_signature.startswith("DCO-1.1-Signed-off-by") or
            "@work.email" in dco_signature):
        print("Error: Read LICENSE.md to understand and agree\n"
            "to the DCO, then use --dco-signature to specify\n"
            "your name and e-mail to sign the maintenance changes.\n"
            " Example: --dco-signature "
            "'DCO-1.1-Signed-off-by: Jane <jane@work.email>'")
        raise RuntimeError("missing DCO info")

    # Preparations and helper functions:
    if dry_run:
        print("(NOT changing anything, just a test run)")
    def update_misc_years(rpath, to_year="today"):
        if to_year == "today":
            to_year = int(datetime.date.today().year)
        contents = None
        def do_update_on_relpath(relpath):
            if not os.path.exists(os.path.join(rpath,
                    relpath)):
                return
            with open(os.path.join(rpath, relpath), "r",
                      encoding="utf-8") as f:
                contents = f.read()
                lines = contents.splitlines()
                had_change = False
                new_lines = []
                for line in lines:
                    if (not line.startswith("Copyright (c) ") or
                            not "ell1e" in line.lower()):
                        new_lines.append(line)
                        continue
                    remainder = line.partition("Copyright (c) ")[2].strip()
                    while len(remainder) > 0 and (
                            (ord(remainder[0]) >= ord("0") and
                            ord(remainder[0]) <= ord("9")) or
                            remainder[0] == "-"):
                        remainder = remainder[1:]
                    first_year = line.partition("Copyright (c) ")[2].strip()
                    first_year = first_year.partition(" ")[0].strip()
                    if "-" in first_year:
                        first_year = first_year.partition("-")[0].strip()
                    if "," in first_year:
                        first_year = first_year.partition(",")[0]
                    first_year = int(first_year)
                    insert_year_str = str(first_year)
                    if first_year < to_year:
                        insert_year_str += "-" + str(to_year)
                    insert_line = ("Copyright (c) " + str(insert_year_str) +
                        remainder)
                    if line.strip().lower() == insert_line.strip().lower():
                        new_lines.append(line)
                        continue
                    new_lines.append(insert_line)
                    had_change = True
            if had_change:
                if not dry_run:
                    with open(os.path.join(rpath, relpath), "w",
                            encoding="utf-8") as f:
                        f.write("\n".join(new_lines))
                    o = subprocess.check_output(["git", "add",
                        relpath],
                        cwd=rpath)
                print("Updated " + os.path.basename(os.path.normpath(
                    rpath)) + ": " + relpath + " year bumped")
                return True
        if do_update_on_relpath("LICENSE.md"):
            return True
        return False

    # Collect all repositories:
    mainrepopath = os.path.join(mydir, "..")
    repo_paths = [mainrepopath]
    for reponame in os.listdir(os.path.join(mainrepopath, "..")):
        if not reponame in ["hvm.horse64.org",
                "hodoc.horse64.org",
                "horp.horse64.org",
                "horsels.horse64.org",
                "sdk.horse64.org",
                "Spew3D",
                "Spew3D-Web",
                "Spew3D-Net"]:
            continue
        print("Found repository: " + str(reponame))
        repopath = os.path.join(mainrepopath, "..", reponame)
        if not os.path.isdir(repopath):
            continue
        repo_paths.append(os.path.normpath(repopath))

    # Make sure nothing is scheduled yet before we touch it:
    for repopath in repo_paths:
        print("Verifying repo is clean: " + str(repopath))
        o = subprocess.check_output(["git", "status", "--porcelain=1"],
            cwd=repopath).decode("utf-8")
        lines = [l for l in o.splitlines()
            if l.startswith("A")]
        if len(lines) > 0:
            print("Aborting, repository has changes scheduled: " +
                repopath)
            raise RuntimeError("found repository with changes to be "
                "committed, deal with that first")

    # Check all repositories if they need to be updated:
    for repopath in repo_paths:
        repopath = os.path.normpath(os.path.abspath(repopath))
        reponame = os.path.basename(os.path.normpath(repopath))
        print("Checking repository: " + str(reponame))
        def update_rel_path_file(rel_path):
            if (os.path.normpath(repopath) ==
                    os.path.normpath(mainrepopath)):
                return False
            if type(rel_path) == list:
                rel_path = os.path.join(*rel_path)
            if are_files_different(
                    os.path.join(repopath, rel_path),
                    os.path.join(mainrepopath, rel_path)):
                base_dir = (os.path.normpath(rel_path).
                    rpartition(os.path.sep)[0])
                if not dry_run:
                    if not os.path.exists(os.path.join(
                            repopath, base_dir)):
                        os.makedirs(os.path.join(repopath, base_dir))
                    shutil.copyfile(os.path.join(mainrepopath, rel_path),
                        os.path.join(repopath, rel_path))
                    o = subprocess.check_output(["git", "add",
                        rel_path],
                        cwd=repopath)
                print("Updated " + reponame + " by updating: " +
                    rel_path + " (inside: " + str(base_dir) + ")")
                return True
            return False
        changed = False
        changed = (update_rel_path_file(
            [".gitea", "ISSUE_TEMPLATE", "bug.yml"]) or changed)
        changed = (update_rel_path_file(
            [".gitea", "ISSUE_TEMPLATE", "docs.yml"]) or changed)
        changed = (update_rel_path_file(
            [".gitea", "ISSUE_TEMPLATE", "proposal.yml"]) or changed)
        changed = (update_rel_path_file(
            [".git", "hooks", "commit-msg"]) or changed)
        os.chmod(os.path.join(repopath, ".git", "hooks", "commit-msg"),
            0o775)
        changed = (update_rel_path_file(
            [".github", "workflows",
                "close-all-pull-requests.yml"]) or changed)
        changed = (update_misc_years(repopath) or changed)
        if not dry_run and changed:
            o = subprocess.check_output(["git", "commit",
                "-m", "housekeeping: Updating "
                "misc repository meta files via "
                "tools/update-repos.py",
                "-m", dco_signature],
                cwd=repopath)


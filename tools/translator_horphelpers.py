#!/usr/bin/python3

# Copyright (c) 2020-2022,  ellie/@ell1e & Horse64 Team (see AUTHORS.md).
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

VERSION="unknown"

import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import textwrap


translator_py_script_dir = (
    os.path.abspath(os.path.dirname(__file__))
)
translator_py_script_path = os.path.abspath(__file__)


def horp_ini_string_get_package_key(s, key):
    lines = s.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [(line.rpartition("#")[0].rstrip() if
        "#" in line else line.rstrip()) for line in lines]
    section = None
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
        if (section == "package" and
                line.startswith(str(key) + "=") or
                line.startswith(str(key) + " ")):
            while (len(line) >= len(str(key) + "X") and
                    line[len(key)] == " "):
                line = key + line[len(key) + 1:]
            if line.startswith(key + "="):
                result = line.partition("=")[2].strip()
                if "." in result:
                    return result
                return None
    return None


def horp_ini_string_get_package_name(s):
    return horp_ini_string_get_package_key(s, "name")


def horp_ini_string_get_package_version(s):
    return horp_ini_string_get_package_key(s, "version")


def horp_ini_string_get_package_license_files(s):
    return horp_ini_string_get_package_key(s, "license files")



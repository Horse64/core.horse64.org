#!/bin/bash
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

realpath -s . 2>&1 > /dev/null
if [ "x$?" != x0 ]; then
    echo "The realpath tool isn't working right."
    exit 1
fi
FULL_PATH_TO_SCRIPT="$(realpath -s "${BASH_SOURCE[-1]}")"
echo "Full path to script: ${FULL_PATH_TO_SCRIPT}"
SCRIPT_DIRECTORY="$(dirname "$FULL_PATH_TO_SCRIPT")"
cd $SCRIPT_DIRECTORY
echo "Changed working directory to: $SCRIPT_DIRECTORY"

cd ..
gcc -o ./gen-c/src/main.o -I ./gen-c/src ./gen-c/src/main.m64.c || { echo "main.o build failed."; exit 1; }
gcc -o ./gen-c/src/std/std.o -I ./gen-c/src ./gen-c/src/std/std.m64.c || { echo "std/std.o build failed"; exit 1; }
gcc -o ./prog ./gen-c/src/main.o ./gen-c/src/std/std.o || { echo "final build failed"; exit 1; }


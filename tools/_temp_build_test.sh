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

# Go to repository root:
realpath . 2>&1 > /dev/null
if [ "x$?" != x0 ]; then
    echo "The realpath tool isn't working right."
    exit 1
fi
FULL_PATH_TO_SCRIPT="$(realpath "${BASH_SOURCE[-1]}")"
echo "Full path to script: ${FULL_PATH_TO_SCRIPT}"
SCRIPT_DIRECTORY="$(dirname "$FULL_PATH_TO_SCRIPT")"
cd $SCRIPT_DIRECTORY
echo "Changed working directory to: $SCRIPT_DIRECTORY"
cd ..
# We should now be in the repository root.

# Run build of our test program:
CFLAGS="-g -I ./gen-c/src/"
function RUN_BUILD_CMD {
    echo "RUNNING: $BUILD_CMD"
    $BUILD_CMD || { echo "Build command failed: $BUILD_CMD"; exit 1; }
}
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/debug.o -c ./gen-c/src/debug.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/io.o -c ./gen-c/src/io.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/limit.o -c ./gen-c/src/limit.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/main.o -c ./gen-c/src/main.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/memory.o -c ./gen-c/src/memory.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/path.o -c ./gen-c/src/path.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/str.o -c ./gen-c/src/str.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./gen-c/src/system.o -c ./gen-c/src/system.m64.c"
RUN_BUILD_CMD
BUILD_CMD="gcc $CFLAGS -o ./prog ./gen-c/src/debug.o ./gen-c/src/io.o ./gen-c/src/limit.o ./gen-c/src/main.o ./gen-c/src/memory.o ./gen-c/src/path.o ./gen-c/src/str.o ./gen-c/src/system.o"
RUN_BUILD_CMD
echo "Output written to: `pwd`/prog"


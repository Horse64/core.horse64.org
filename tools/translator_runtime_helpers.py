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


import subprocess
import sys
import threading
import time


def _process_run(cmd, args=[], run_in_dir=None,
        print_output=False):
    assert(type(cmd) == str)
    cmdlist = [cmd] + args
    process = subprocess.Popen(cmdlist,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=run_in_dir)
    output = [b""]
    def output_thread_func(output, process, print_output):
        while process.poll() == None:
            try:
                char = process.stdout.read(1)
            except (IOError, BrokenPipeError, ValueError):
                return
            output[0] += char
            if print_output:
                sys.stdout.buffer.write(char)
    output_thread = threading.Thread(
        target=output_thread_func,
        args=(output, process, print_output))
    output_thread.daemon = True
    output_thread.start()
    process.wait()
    try:
        process.stdout.close()
    except (IOError, BrokenPipeError):
        pass
    output_thread.join()
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)
    output = output[0].decode("utf-8", "replace")
    return output


def _compiler_run_file(cmd, args=[], run_in_dir=None,
        print_output=False):
    assert(type(cmd) == str)
    run_cmd = sys.executable
    run_args = [__translator_py_path__,
        "--", cmd] + args
    return _process_run(run_cmd, args=run_args,
        run_in_dir=run_in_dir, print_output=print_output)


def h64_type(v):
    result = type(v)
    if result == str:
        return "str"
    elif result == bytes:
        return "bytes"
    elif result in {int, float}:
        return "num"
    elif result == list:
        return "list"
    elif result == set:
        return "set"
    elif result == dict:
        return "map"
    elif result == bool:
        return "bool"
    elif v == None:
        return "none"
    return str(result)


def _container_add(container, item):
    if (not hasattr(container, "add") and
            hasattr(container, "append")):
        return container.append(item)
    return container


def _container_sort(container, *args, **kwargs):
    if (type(container) in {list, set}):
        return sorted(container)
    return container.sort(*args, **kwargs)


def _container_repeat(container, *args, **kwargs):
    if type(container) in {bytes, str} and \
            len(args) == 1 and type(args[0]) in {int, float}:
        return container * int(round(args[0]))
    return container.repeat(*args, **kwargs)


def _container_join(container, *args, **kwargs):
    if (hasattr(container, "join") and
            type(container) not in {list, set, map}):
        return container.join(*args, **kwargs)
    if len(args) == 1 and (type(args[0]) == str or
            type(args[0]) == bytes):
        return args[0].join(container)
    return container.join(*args)


def _container_find(container, *args, **kwargs):
    if type(container) == str and len(args) == 1:
        result = container.find(args[0])
        if result < 0:
            return None
        return result
    if (hasattr(container, "find") and
            type(container) != list) or len(args) < 1:
        return container.find(*args, **kwargs)
    try:
        return container.index(args[0])
    except ValueError:
        return None


def _container_sub(container, *args, **kwargs):
    if len(args) >= 1 and type(container) in {bytes, str, list}:
        i1 = args[0]
        i2 = None
        if len(args) > 1:
            i2 = args[1]
        if i2 == None:
            i2 = len(container)
        if (type(i1) not in {float, int} and
                type(i2) not in {float, int}):
            raise TypeError("indexes must be type num")
        i1 = max(0, i1)
        i2 = max(i1, i2)
        if i2 <= i1:
            return ""
        return container[i1:i2]
    return container.sub(*args, **kwargs)


def _math_max(v1, v2):
    return max(v1, v2)


def _math_min(v1, v2):
    return min(v1, v2)


def _math_round(v1):
    return int(round(v1))


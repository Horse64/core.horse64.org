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


import collections.abc
import fnmatch
import functools
import ipaddress
import json
import math
import os
import platform
import requests
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib
import urllib.parse


_async_ops_lock = threading.Lock()
_async_ops = []
_async_ops_stop_threads = False
_async_delayed_calls = []

_delayed_modinit_funclist = []


def _run_delayed_modinit():
    failed_runs = []
    for f in _delayed_modinit_funclist:
        if f() == False:
            failed_runs.append(f)
    while len(failed_runs) > 0:
        new_failed_runs = []
        for f in _delayed_modinit_funclist:
            if f() == False:
                new_failed_runs.append(f)
        failed_runs = new_failed_runs


class _LicenseObj:
    def __init__(self, file_name, text=""):
        self.file_name = file_name
        self.text = text


class _RuntimeError(BaseException):
    def __init__(self, msg):
        if msg is None:
            msg = ("Runtime error.")
        super().__init__(msg)
        self.msg = msg


class _ValueError(ValueError, _RuntimeError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Invalid value.")
        super().__init__(msg)
        self.msg = msg


class _TypeError(TypeError, _RuntimeError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Invalid value.")
        super().__init__(msg)
        self.msg = msg


class _ResourceError(OSError, _RuntimeError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Hardware resource problem occured.")
        super().__init__(msg)
        self.msg = msg


class _NetworkIOError(_ResourceError):
    def __init__(self, msg):
        if msg is None:
            msg = (
                "Temporary network failure occured. "
                "Check your internet connectivity.")
        super().__init__(msg)
        self.msg = msg


class _IOError(_ResourceError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Unexpected I/O failure")
        super().__init__(msg)
        self.msg = msg


class _ResourceMisuseError(_ValueError):
    def __init__(self, msg):
        if msg is None:
            msg = ("The given resource doesn't "
                "support this operation in the "
                "requested way.")
        super().__init__(msg)
        self.msg = msg


class _PermissionError(_ResourceMisuseError):
    def __init__(self, msg):
        if msg is None:
            msg = ("PermissionDenied.")
        super().__init__(msg)
        self.msg = msg


class _PathNotFoundError(_ResourceMisuseError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Target path not found.")
        super().__init__(msg)
        self.msg = msg


class _PathAlreadyExistsError(_ResourceMisuseError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Target path already exists.")
        super().__init__(msg)
        self.msg = msg


class _PathIsWrongTypeError(_ResourceMisuseError):
    def __init__(self, msg):
        if msg is None:
            msg = ("Target path isn't the right type.")
        super().__init__(msg)
        self.msg = msg


def _return_licenses():
    return __translator_licenses_list


def _terminal_get_line(callback):
    global _async_ops_lock, _async_ops
    info = {"callback": callback}
    def run_do(op):
        global _async_ops_lock
        info = op.userdata
        err = None
        try:
            sys.stdout.flush()
            output = input()
        except Exception as e:
            err = e
        if err != None:
            output = None
        _async_ops_lock.acquire()
        op.userdata2 = [err, output]
        op.done = True
        _async_ops_lock.release()
    def done_cb(op):
        result = op.userdata2
        assert(result != None)
        f = op.userdata["callback"]
        op.userdata = None
        op.userdata2 = None
        op.do_func = None
        op.callback_func = None
        return f(result[0], result[1])
    op = _AsyncOperation(info, run_do, done_cb)
    _async_ops_lock.acquire()
    _async_ops.append(op)
    _async_ops_lock.release()


def _process_run_async(cmd, callback,
        args=[], run_in_dir=None,
        print_output=False):
    global _async_ops_lock, _async_ops
    info = {"cmd": cmd, "callback": callback,
        "args": args, "run_in_dir": run_in_dir,
        "print_output": print_output}
    def run_do(op):
        global _async_ops_lock
        info = op.userdata
        output = None
        err = None
        try:
            output = _process_run(
                info["cmd"],
                args=info["args"],
                run_in_dir=info["run_in_dir"],
                print_output=info["print_output"])
        except subprocess.CalledProcessError as e:
            err = e
        _async_ops_lock.acquire()
        op.userdata2 = [err, output]
        op.done = True
        _async_ops_lock.release()
    def done_cb(op):
        result = op.userdata2
        assert(result != None)
        f = op.userdata["callback"]
        op.userdata = None
        op.userdata2 = None
        op.do_func = None
        op.callback_func = None
        return f(result[0], result[1])
    op = _AsyncOperation(info, run_do, done_cb)
    _async_ops_lock.acquire()
    _async_ops.append(op)
    _async_ops_lock.release()


def _process_run(cmd, args=[], run_in_dir=None,
        print_output=False, with_input=False):
    assert(type(cmd) == str)

    # Launch the process:
    cmdlist = [cmd] + args
    process = subprocess.Popen(cmdlist,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=(None if with_input else
               subprocess.PIPE),
        cwd=run_in_dir)

    # An output thread to read while process is running:
    output = [b""]
    def output_thread_func(output, process, print_output):
        read_something_last = time.monotonic()
        while (process.poll() == None or
                read_something_last + 0.5 > time.monotonic()):
            try:
                if not with_input:
                    process.stdin.flush()
                process.stdout.flush()
                char = process.stdout.read(1)
            except (IOError, BrokenPipeError, ValueError) as e:
                sys.stdout.flush()
                return
            read_something_last = time.monotonic()
            output[0] += char
            if print_output:
                sys.stdout.buffer.write(char)
                sys.stdout.flush()
        sys.stdout.flush()
    # Launch our thread:
    output_thread = threading.Thread(
        target=output_thread_func,
        args=(output, process, print_output))
    output_thread.daemon = True
    output_thread.start()

    # Wait for process to finish and then shut down things:
    process.wait()
    try:
        process.stdout.flush()
    except (IOError, BrokenPipeError):
        pass
    time.sleep(0.2)  # Is this needed due to a subprocess.PIPE bug?
    try:
        process.stdout.close()
    except (IOError, BrokenPipeError):
        pass
    output_thread.join()

    # Return result:
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)
    output = output[0].decode("utf-8", "replace")
    return output


def _compiler_run_file(cmd, callback,
        args=[], run_in_dir=None,
        print_output=False):
    assert(type(cmd) == str)
    run_cmd = sys.executable
    run_args = [__translator_py_path__,
        "--", cmd] + args
    return _process_run_async(run_cmd, callback,
        args=run_args,
        run_in_dir=run_in_dir, print_output=print_output)


def h64_type(v):
    result = type(v)
    if result == str:
        return "str"
    elif result == _TranslatedVec:
        return "vec"
    elif result == _TranslatedSet:
        return "set"
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
    return container.add(item)


def _container_sort(container, *args, **kwargs):
    if (type(container) in {list}):
        if len(container) <= 1:
            return None
        sorted_container = None
        if "cmp" in kwargs:
            cmp_func = kwargs["cmp"]
            def do_cmp(a, b):
                v = cmp_func(a, b)
                if v == True:
                    return -1
                elif v == False:
                    return 1
                elif v == None:
                    return None
                raise ValueError("Given 'cmp' func returned "
                    "invalid value.")
            sorted_container = list(sorted(
                container, key=functools.cmp_to_key(do_cmp)
            ))
        else:
            sorted_container = list(sorted(container))
        i = 0
        while i < len(sorted_container):
            container[i] = sorted_container[i]
            i += 1
        return None
    elif type(container) in {tuple, set}:
        return _TypeError("cannot sort this container")
    return container.sort(*args, **kwargs)


def _container_reverse(container, *args, **kwargs):
    if (type(container) in {list}):
        sorted_container = list(reversed(container))
        i = 0
        while i < len(sorted_container):
            container[i] = sorted_container[i]
            i += 1
        return
    elif type(container) in {tuple, set}:
        return _TypeError("cannot reverse this container")
    return container.sort(*args, **kwargs)


def _value_to_str(value):
    if type(value) == bytes:
        return value.decode("utf-8",
            errors="surrogateescape")
    if type(value) == str:
        return value
    if type(value) == bool:
        return ("yes" if value else "no")
    if value is None:
        return "none"
    if (hasattr(value, "as_str") and
            callable(value.as_str)):
        return str(value.as_str())
    if type(value) == type(set()):
        v = repr(value)
        if v.strip().lower() == "set()":
            return "{}"
        return v
    return str(value)


def _value_as_bytes(value):
    if type(value) == str:
        return value.encode("utf-8",
            errors="surrogateescape")
    else:
        return NotImplementedError("conversion not handled "
            "by this runtime")


def _container_repeat(container, *args, **kwargs):
    if type(container) in {bytes, str} and \
            len(args) == 1 and type(args[0]) in {int, float}:
        if int(round(args[0])) <= 0:
            if type(container) == bytes:
                return b""
            return ""
        return container * int(round(args[0]))
    return container.repeat(*args, **kwargs)


def _container_ltrim(container, *args, **kwargs):
    if type(container) in {bytes, str} and \
            len(args) <= 1:
        if len(args) == 0:
            if type(container) == bytes:
                return container.lstrip(b" \t\r\n")
            return container.lstrip(" \t\r\n")
        return container.lstrip(args[0])
    return container.ltrim(*args, **kwargs)


def _container_rtrim(container, *args, **kwargs):
    if type(container) in {bytes, str} and \
            len(args) <= 1:
        if len(args) == 0:
            if type(container) == bytes:
                return container.rstrip(b" \t\r\n")
            return container.rstrip(" \t\r\n")
        return container.rstrip(args[0])
    return container.rtrim(*args, **kwargs)


def _container_trim(container, *args, **kwargs):
    if type(container) in {bytes, str} and \
            len(args) <= 1:
        if len(args) == 0:
            if type(container) == bytes:
                return container.strip(b" \t\r\n")
            return container.strip(" \t\r\n")
        return container.strip(args[0])
    return container.trim(*args, **kwargs)


def _container_join(container, *args, **kwargs):
    if (hasattr(container, "join") and
            type(container) not in {list, set, map}):
        return container.join(*args, **kwargs)
    if len(args) == 1 and (type(args[0]) == str or
            type(args[0]) == bytes):
        return args[0].join(container)
    return container.join(*args)


def _container_find(container, *args, **kwargs):
    if (type(container) in {str, bytes} and
            len(args) == 1):
        result = container.find(args[0])
        if result < 0:
            return None
        return result + 1
    if (type(container) in {tuple, list} and
            len(args) == 1):
        try:
            result = container.index(args[0])
            if result < 0:
                return None
            return result + 1
        except ValueError:
            return None
    return container.find(*args, **kwargs)


def _container_rfind(container, *args, **kwargs):
    if (type(container) in {str, bytes} and
            len(args) == 1):
        result = container.rfind(args[0])
        if result < 0:
            return None
        return result + 1
    if (type(container) in {tuple, list} and
            len(args) == 1):
        try:
            result = container.index(reversed(args[0]))
            if result < 0:
                return None
            return result + 1
        except ValueError:
            return None
    return container.rfind(*args, **kwargs)


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
            raise _TypeError("indexes must be type num")
        i1 = max(1, i1)
        if i2 < i1:
            if type(container) == bytes:
                return b""
            if type(container) == list:
                return []
            return ""
        return container[i1 - 1:i2]
    return container.sub(*args, **kwargs)


def _container_subfirst(container, *args, **kwargs):
    if (len(args) == 0 and
            type(container) in {bytes, str, list}):
        return container[:1]
    return container.subfirst(*args, **kwargs)


def _container_sublast(container, *args, **kwargs):
    if (len(args) == 0 and
            type(container) in {bytes, str, list}):
        return container[-1:]
    return container.sublast(*args, **kwargs)


def _container_first(container, *args, **kwargs):
    if (len(args) == 0 and
            type(container) in {bytes, str, list}):
        return container[0]
    return container.first(*args, **kwargs)


def _container_last(container, *args, **kwargs):
    if (len(args) == 0 and
            type(container) in {bytes, str, list}):
        return container[-1]
    return container.last(*args, **kwargs)


def _math_floor(v1):
    return math.floor(v1)


def _math_ceil(v1):
    return math.ceil(v1)


def _math_max(v1, v2):
    return max(v1, v2)


def _math_min(v1, v2):
    return min(v1, v2)


def _math_round(v1):
    return int(round(v1))


def _is_digits(v):
    if len(v) == 0:
        return False
    for c in v:
        if ord(c) < ord("0") or ord(c) > ord("9"):
            return False
    return True


def _looks_like_uri(v):
    if (v.find("://") >= 2 and
            len(v.partition("://")[0].strip()) > 1
            ):
        return True
    if len(v) >= 1 and v[0] == "/":
        return False
    if (len(v) >= 3 and v[1] == ":" and
            (v[2] == "/" or c[2] == "\\")):
        return False
    if ("." in v and ":" in v and
            v.find(":") > v.find(".") and
            v.find("/") > v.find(":") + 1):
        possible_host = v.partition(":")[0]
        possible_port = v.partition(":")[2]
        possible_resource = possible_port.partition("/")[2]
        possible_port = possible_port.partition("/")[0]
        if not _is_digits(possible_port) or ":" in possible_resource:
            return False
        if "." not in possible_host or possible_host.startswith("."):
            return False
        if (" " in possible_host or
                possible_host.endswith(".")):
            return False
        return True
    common_tlds = [".org", ".com", ".co.uk", ".io",
        ".eu", ".dev", ".cn", ".in", ".net"]
    for common_tld in common_tlds:
        tld_pos = v.find(common_tld + "/")
        if tld_pos >= 2:
            return True
    if v.find("://") >= 1:
        return True
    return False


def _file_uri_from_vfs_path(v):
    v = _file_uri_from_path(v)
    return "vfs://" + v.partition("://")[2]


def _uri_get_protocol(v):
    if not "://" in v:
        return None
    return v.partition("://")[0].lower()


def _file_uri_from_path(v):
    if v == "" or v == ".":
        v = "./"
    if platform.system().lower() == "windows":
        v = (os.path.normpath(v.replace("\\", "/")).
            replace("\\", "/"))
    else:
        v = os.path.normpath(v)
    v = "file://" + urllib.parse.quote(v)
    return v


def _uri_escape_path(v):
    return urllib.parse.quote(v)


def _uri_normalize(v, guess_nonfiles=True):
    v = str(v + "")
    if (guess_nonfiles and
            _looks_like_uri(v) and
            "://" not in v):
        target_part = v
        resource_part = "/"
        if "/" in v:
            resource_part = "/" + v.partition("/")[2]
            target_part = v.partition("/")[0]
        v = ("https://" + target_part +
            urllib.parse.quote(resource_part))
    elif "://" not in v or not _looks_like_uri(v):
        if platform.system().lower() == "windows":
            v = (os.path.normpath(v.replace("\\", "/")).
                replace("\\", "/"))
        else:
            v = os.path.normpath(v)
        v = "file://" + urllib.parse.quote(v)
    if (v.lower().startswith("file://") or
            v.lower().startswith("vfs://")):
        resource = urllib.parse.unquote(v.partition("://")[2])
        resource = os.path.normpath(resource)
        if resource == ".":
            resource = "./"
        return (v.partition("://")[0].lower() + "://" +
            urllib.parse.quote(resource))
    urlobj = urllib.parse.urlparse(v)
    result = (urlobj.scheme.lower() + "://" +
        urlobj.hostname.lower())
    if urlobj.port != None:
        result += ":" + str(urlobj.port)
    resource = urlobj.path
    if not resource.startswith("/"):
        resource = "/" + resource
    result += resource
    return result


def _json_dump(obj):
    return json.dumps(obj)


def _json_parse(s):
    return json.loads(s)


def _uri_to_file_or_vfs_path(v):
    if (not v.lower().startswith("file://") and
            not v.lower().startswith("vfs://")):
        raise ValueError("Not a file:// or vfs:// path.")
    resource = urllib.parse.unquote(v.partition("://")[2])
    resource = os.path.normpath(resource)
    return resource


def _io_exists(v, allow_vfs=True, allow_disk=True):
    if v == "":
        v = "."
    if not allow_disk:
        return (v == ".")
    return _wrap_io(os.path.exists)(v)


def _io_ls_dir(v, allow_vfs=True, allow_disk=True):
    if not allow_disk:
        if os.path.normpath(v) in {"", "."}:
            return []
        raise _PathNotFoundError(
            "path not found"
        )
    result = None
    try:
        result = v.listdir(v)
    except (FileNotFoundError, OSError, IOError) as e:
        if isinstance(e, FileNotFoundError):
            raise _PathNotFoundError()
        if isinstance(e, NotADirectoryError):
            raise _PathIsWrongTypeError(
                "Target isn't a directory."
            )
        if isinstance(e, PermissionError):
            raise _PermissionError()
        raise _IOError(str(e))
    return result


def _wrap_io(f):
    def wrapped_func(*args, **kwargs):
        result = None
        try:
            result = f(*args, **kwargs)
        except (FileNotFoundError, OSError, IOError) as e:
            if isinstance(e, FileNotFoundError):
                raise _PathNotFoundError()
            if isinstance(e, IsADirectoryError):
                raise _PathIsWrongTypeError("Target is a directory.")
            if isinstance(e, NotADirectoryError):
                raise _PathIsWrongTypeError(
                    "Target isn't a directory."
                )
            if isinstance(e, FileExistsError):
                raise _PathAlreadyExistsError()
            if isinstance(e, shutil.Error):
                raise _ResourceMisuseError()
            if isinstance(e, PermissionError):
                raise _PermissionError()
            if isinstance(e, OSError):
                raise _ResourceMisuseError()
            raise _IOError(str(e))
        return result
    return wrapped_func


def _async_delay_call(f, args):
    global _async_delayed_calls, async_ops_lock
    _async_ops_lock.acquire()
    _async_delayed_calls.append((f, args))
    _async_ops_lock.release()


class _FileObjFromDisk:
    def __init__(self, path, mode,
            allow_vfs=True,
            allow_disk=True):
        if not allow_disk:
            raise _ResourceMisuseError(
                "no VFS support available in this runtime"
            )
        self.binary = "b" in mode
        try:
            if not self.binary:
                self.fobj = open(path, mode, encoding="utf-8",
                    errors='replace')
            else:
                self.fobj = open(path, mode)
        except (FileNotFoundError, IsADirectoryError,
                IOError, OSError) as e:
            if isinstance(e, FileNotFoundError):
                raise _PathNotFoundError("Path not found.")
            if isinstance(e, IsADirectoryError):
                raise _ResourceMisuseError("Target is a directory.")
            if isinstance(e, PermissionError):
                raise _PermissionError("Permission denied.")
            if isinstance(e, OSError):
                raise _ResourceMisuseError("Resource can't be "
                    "used that way.")
            raise _IOError("Temporary IO failure.")

    def read(self, callback, amount=None):
        if amount != None:
            amount = int(amount)
            if amount <= 0:
                _async_delay_call(
                    callback, [None, b"" if self.binary else ""]
                )
                return
        err = None
        data = None
        try:
            if amount == None:
                data = self.fobj.read()
            else:
                data = self.fobj.read(amount)
        except (IOError, OSError) as e:
            if isinstance(e, PermissionError):
                err = _PermissionError()
            else:
                err = _IOError()
            assert(data == None)
        _async_delay_call(callback, [err, data])

    def write(self, callback, value):
        if not self.binary and type(value) != str:
            _async_delay_call(callback, [
                _TypeError("Value must be widechar string.")
            ])
            return
        elif self.binary and type(value) != bytes:
            _async_delay_call(callback, [
                _TypeError("Value must be bytes value.")
            ])
            return
        self.fobj.write(value)
        _async_delay_call(callback, [None])

    def close(self):
        try:
            self.fobj.close()
        except (IOError, OSError) as e:
            raise _IOError()


class _AsyncOperation:
    def __init__(self, userdata, do_func, callback_func):
        self.started = False
        self.done = False
        self.userdata = userdata
        self.userdata2 = None
        self.do_func = do_func
        self.callback_func = callback_func


class _RequestsFetchObj:
    def __init__(self, uri,
            extra_headers={},
            retries=0, retry_delay=0.5):
        self.iterobj = None
        self.request = None
        self.buffer = b""
        self.uri = uri
        self.extra_headers = extra_headers
        self.request = None
        self.retries = retries
        self.retry_delay = retry_delay

    def read(self, cb, amount=None):
        if amount != None:
            amount = int(amount)
        global _async_ops_lock, _async_ops
        def recv_sync(op):
            global _async_ops_lock
            self = op.userdata[0]
            def read_chunk():
                try:
                    chunk = next(self.iterobj)
                    if len(chunk) == 0:
                        return False
                    self.buffer += chunk
                    return True
                except StopIteration:
                    return False
            if self.request is None:
                try:
                    self.request = (
                        requests.get(self.uri,
                        headers=self.extra_headers,
                        stream=True))
                    self.iterobj = self.request.iter_content(
                        chunk_size=1024
                    )
                except (OSError, requests.RequestException,
                        requests.HTTPError):
                    _async_ops_lock.acquire()
                    op.userdata2 = [
                        _NetworkIOError("Connection setup or "
                            "request failed."), None]
                    op.done = True
                    _async_ops_lock.release()
                    return
            result = b""
            if amount is None or amount > 0:
                try:
                    while amount is None or len(self.buffer) < amount:
                        if not read_chunk():
                            break
                    if amount is None:
                        result = self.buffer
                        self.buffer = b""
                    else:
                        result = self.buffer[:amount]
                        self.buffer = self.buffer[amount:]
                except (OSError, IOError):
                    _async_ops_lock.acquire()
                    op.userdata2 = [
                        _NetworkIOError("Connection read "
                            "failed."), None]
                    op.done = True
                    _async_ops_lock.release()
                    return
            _async_ops_lock.acquire()
            op.userdata2 = [None, result]
            op.done = True
            _async_ops_lock.release()
        def done_cb(op):
            result = op.userdata2
            f = op.userdata[1]
            op.userdata = None
            op.userdata2 = None
            op.do_func = None
            op.callback_func = None
            return f(result[0], result[1])
        op = _AsyncOperation([self, cb], recv_sync, done_cb)
        _async_ops_lock.acquire()
        _async_ops.append(op)
        _async_ops_lock.release()

    def close(self):
        if self.request is None:
            return
        try:
            self.request.close()
        except (IOError, OSError):
            pass
        self.rawobj = None


def _net_lookup_name(name, cb, retries=0, retry_delay=0.5):
    returnasdict = True
    names = None
    if type(name) == str:
        returnasdict = False
        names = [name]
    elif type(name) in {tuple, list}:
        names = list(name)
    else:
        raise _TypeError("name must be str or list")
    def async_lookup_do(job):
        returnasdict = job.userdata["returnasdict"]
        perma_tempfail = False
        finalresult = {}
        for name in job.userdata["names"]:
            was_tempfail = False
            try:
                ip = str(ipaddress.ip_address(name))
                # Oh, so it was an ip already!
                finalresult[name] = ip
                continue
            except ValueError:
                pass
            finalresult[name] = None
            retries = job.userdata["retries"]
            retry_delay = job.userdata["retry_delay"]
            tries = retries + 1
            retry_delay = max(0, retry_delay)
            while tries > 0:
                tries -= 1
                want_retry = False
                was_tempfail = False
                ipv6_results = []
                try:
                    result = socket.getaddrinfo(
                        name, None, socket.AF_INET6)
                    if len(result) > 0:
                        ipv6_results += [
                            str(entry[4][0]) for entry in result
                        ]
                except socket.gaierror as e:
                    if e.errno != -2:  # -2 means NXDOMAIN
                        want_retry = True
                        was_tempfail = True
                ipv4_results = []
                try:
                    result = socket.getaddrinfo(
                        name, None, socket.AF_INET)
                    if len(result) > 0:
                        ipv4_results += [
                            str(entry[4][0]) for entry in result
                        ]
                except socket.gaierror as e:
                    if e.errno != -2:  # -2 means NXDOMAIN
                        want_retry = True
                        was_tempfail = True
                if want_retry and tries > 0:
                    if retry_delay > 0:
                        time.sleep(retry_delay)
                    continue
                finalresult[name] = ipv6_results + ipv4_results
                break
            if finalresult[name] is None and was_tempfail:
                perma_tempfail = True
                break
            continue
        if perma_tempfail:
            job.userdata2 = [_NetworkIOError("Look-up "
                 "temporarily failed, check connectivity."), {}]
        else:
            if not job.userdata["returnasdict"]:
                job.userdata2 = [None,
                    finalresult[job.userdata["names"][0]]]
            else:
                job.userdata2 = [None, finalresult]
        job.done = True
    def done_cb(op):
        f = op.userdata["usercb"]
        result = op.userdata2
        op.userdata = None
        op.userdata2 = None
        op.do_func = None
        op.callback_func = None
        return f(result[0], result[1])
    op = _AsyncOperation({
        "returnasdict": returnasdict,
        "names": names, "retries": retries,
        "retry_delay": retry_delay,
        "usercb": cb},
        async_lookup_do, done_cb)
    _async_ops_lock.acquire()
    _async_ops.append(op)
    _async_ops_lock.release()


def _net_fetch_open(uri, extra_headers=None,
        user_agent="core.horse64.org net.fetch/0.1 (translator)",
        allow_disk=False, allow_vfs=False):
    if extra_headers is None:
        extra_headers = {}
    if not "://" in uri:
        raise ValueError("Need web URI to fetch from.")
    if uri.lower().startswith("file://"):
        if not allow_disk:
            raise _PermissionError("Disk access disabled.")
        fpath = _uri_to_file_or_vfs_path(uri)
        return _FileObjFromDisk(fpath, "rb")
    if (not uri.lower().startswith("https://") and
            not uri.lower().startswith("http://")):
        raise ValueError("Unsupported protocol, "
            "supported protocols are: http, https, file.")
    if extra_headers != None:
        extra_headers = dict(extra_headers)
    clean_keys = []
    for key in extra_headers:
        if key.lower() == "user-agent":
            clean_keys.append(key)
    for key in clean_keys:
        del(extra_headers[key])
    extra_headers["User-Agent"] = str(user_agent + "")
    return _RequestsFetchObj(
        uri=uri, extra_headers=extra_headers
    )


def _run_main(main_func):
    global DEBUGV, _async_ops_stop_threads,\
        _async_ops_lock, _async_ops, \
        _async_delayed_calls
    _run_delayed_modinit()
    def async_jobs_worker():
        global _async_ops_stop_threads,\
            _async_ops_lock, _async_ops
        while True:
            _async_ops_lock.acquire()
            if _async_ops_stop_threads:
                _async_ops_lock.release()
                return
            if len(_async_ops) == 0:
                _async_ops_lock.release()
                time.sleep(0.1)
                continue
            work_job = None
            for job in _async_ops:
                if not job.done and not job.started:
                    job.started = True
                    work_job = job
                    break
            _async_ops_lock.release()
            if work_job:
                try:
                    job.do_func(job)
                except Exception as e:
                    print("translator_runtime_helper.py: " +
                        "error: " +
                        "uncaught error in async job: " +
                        str((e,
                        type(job.userdata))))
                    pass
                _async_ops_lock.acquire()
                job.done = True
                if _async_ops_stop_threads:
                    _async_ops_lock.release()
                    return
                _async_ops_lock.release()
            else:
                time.sleep(0.1)
    if DEBUGV.ENABLE and DEBUGV.ENABLE_ASYNC_OPS:
        print("tools/translator.py: debug: starting worker "
            "threads for async jobs...")
    workers = []
    i = 0
    while i < 16:
        worker_thread = threading.Thread(
            target=async_jobs_worker,
            args=tuple())
        worker_thread.daemon = True
        worker_thread.start()
        workers.append(worker_thread)
        i += 1
    return_value = main_func()
    while True:
        _async_ops_lock.acquire()
        if (len(_async_ops) == 0 and
                len(_async_delayed_calls) == 0):
            _async_ops_lock.release()
            break

        # If we got any operations done, process result:
        have_calls_waiting = len(_async_delayed_calls)
        done_op = None
        i = 0
        while i < len(_async_ops):
            if _async_ops[i].done:
                done_op = _async_ops[i]
                _async_ops = (_async_ops[:i] +
                    _async_ops[i + 1:])
                break
            i += 1
        _async_ops_lock.release()
        if done_op != None:
            try:
                done_op.callback_func(done_op)
            except Exception as e:
                _async_ops_lock.acquire()
                _async_ops_stop_threads = True
                _async_ops_lock.release()
                raise e
            continue
        elif have_calls_waiting:
            _async_ops_lock.acquire()

            # No operator needing our time but delayed calls!
            if len(_async_delayed_calls) == 0:
                # Oops, was cleared out in race condition.
                _async_ops_lock.release()
                continue
            first_call = _async_delayed_calls[0]
            assert(type(first_call) == tuple)
            _async_delayed_calls = (
                _async_delayed_calls[1:]
            )
            _async_ops_lock.release()
            try:
                first_call[0](*(first_call[1]))
            except Exception as e:
                _async_ops_lock.acquire()
                _async_ops_stop_threads = True
                _async_ops_lock.release()
                raise e
            continue
        # Since we didn't do work, sleep to not burn the CPU:
        time.sleep(0.01)
        continue
    if DEBUGV.ENABLE and DEBUGV.ENABLE_ASYNC_OPS:
        print("tools/translator.py: debug: program "
            "shutting down for good, stopping jobs...")
    _async_ops_lock.acquire()
    _async_ops_stop_threads = True
    _async_ops_lock.release()
    sys.exit(return_value)


def _container_squarebracketaccess(container, index):
    if type(container) == dict:
        return container[index]
    elif type(container) in {str, bytes, list, _TranslatedVec}:
        if type(index) not in {float, int}:
            raise _TypeError("Index isn't a num.")
        index = round(index)
        if index < 1 or index > len(container):
            raise IndexError("Out of range.")
        if type(container) == bytes:
            return container[index - 1:index]
        return container[index - 1]
    raise NotImplementedError("container type "
        "not implemented for '[' indexing: " +
        str(type(container)))


def _container_squarebracketassign(container, index,
        assign_type, value):
    recognized_type = False
    index_to_use = None
    if type(container) in {str, bytes, list}:
        if type(index) not in {float, int}:
            raise _TypeError("Index isn't a num.")
        index_to_use = round(index)
        if (index_to_use <= 0 or
                index_to_use > len(container)):
            raise IndexError("Out of range.")
        index_to_use -= 1
        recognized_type = True
    elif type(container) == dict:
        index_to_use = index
        recognized_type = True
    if recognized_type:
        if assign_type == "=":
            container[index_to_use] = value
        elif assign_type == "+=":
            container[index_to_use] = (
                container[index_to_use] + value)
        elif assign_type == "-=":
            container[index_to_use] = (
                container[index_to_use] - value)
        elif assign_type == "*=":
            container[index_to_use] = (
                container[index_to_use] * value)
        elif assign_type == "/=":
            container[index_to_use] = (
                container[index_to_use] / value)
        elif assign_type == "|=":
            container[index_to_use] = (
                container[index_to_use] | value)
        elif assign_type == "&=":
            container[index_to_use] = (
                container[index_to_use] & value)
        else:
            raise NotImplementedError("assign type " +
                "not implemented: " + assign_type)
        return
    raise NotImplementedError("container type "
        "not imlemented for '[' assign: " +
        str(type(container)))


def _system_osname():
    import sys
    if "linux" in sys.platform.lower():
        return "linux"
    if ("darwin" in sys.platform.lower() or
            "mac" in sys.platform.lower()):
        return "macos"
    if "freebsd" in sys.platform.lower():
        return "freebsd"
    if "win" in sys.platform.lower():
        return "windows"
    if "openbsd" in sys.platform.lower():
        return "openbsd"
    if "netbsd" in sys.platform.lower():
        return "netbsd"
    raise NotImplementedError("Not implemented on "
        "this platform, please file an issue to "
        "get it fixed.")


def _textformat_outdent(s):
    if not type(s) in {str, bytes}:
        raise _TypeError("Text must be str or bytes")
    was_bytes = False
    if type(s) == bytes:
        s = s.decode("utf-8", "surrogateescape")
    linebreak = "\n"
    if "\r\n" in s:
        linebreak = "\r\n"

    # Figure out what amount of indent all lines share:
    s = s.splitlines()
    shared_indent = None
    for sline in s:
        # Ignore fully empty lines:
        if sline.strip(" \t") == "":
            continue

        # Get the indent of this line:
        indent = sline[
            :(len(sline) - len(sline.strip(" \t")))
        ]
        if shared_indent is None:
            shared_indent = indent
            continue
        # Figure out the shortest, shared indent:
        i = 0
        while (i < len(shared_indent) and
                i < len(indent) and
                shared_indent[i] == indent[i]):
            i += 1
        shared_indent = shared_indent[:i]

    # Rewrite lines with all the shared indent removed:
    new_s = []
    for sline in s:
        if sline.strip(" \t") == "":
            new_s.append(shared_indent)
            continue
        new_s.append(sline[len(shared_indent):])

    # Return result:
    new_s = linebreak.join(new_s)
    if was_bytes:
        new_s = new_s.encode("utf-8", "surrogateescape")
    return new_s


class _ModuleObject:
    def __init__(self, base_module, base_library,
            renamed=None):
        assert(base_module != None)
        self._base_module = base_module
        if base_library is None:
            base_library = "main"
        self._base_library = base_library
        self._rename_pair = renamed

    def _get_base_module(self):
        folder = __translated_output_root_path__
        if folder not in sys.path:
            sys.path.insert(1, folder)
        import horse_modules
        result = getattr(horse_modules,
            self._base_library.replace(".", "_"))
        if hasattr(result, "_h64mod_" + self._base_module):
            result = getattr(result,
                ("_h64mod_" + self._base_module))
        else:
            result = getattr(result, self._base_module)
        if self._rename_pair != None:
            rename_parts = self._rename_pair[0].split(".")[1:]
            for part in rename_parts:
                result = getattr(result, "_h64mod_" + part)
        return result

    def __getattr__(self, name):
        if (name == "" or "." in name or
                name.startswith("__")):
            raise AttributeError("nope: " + str(name))
        basemod = self._get_base_module()
        if (not hasattr(basemod, name) and
                not name.startswith("_h64mod_")):
            name = "_h64mod_" + name
        return getattr(basemod, name)


def _wildcard_match(pattern, value,
        doublestar_for_paths=False,
        backslash_paths=False):
    if "^" in pattern:
        raise NotImplementedError(
            "Escaping via '^' is not implemented by "
            "the Python translator."
        )
    if is_winpath:
        pattern = pattern.replace("\\", "/")
        value = value.replace("\\", "/")
    if doubleglob_for_paths and (
            "/" in value):
        return (len(pywildcard.filter([value], pattern)) == 1)
    return fnmatch.fnmatch(value, pattern)


def _is_num(v):
    if type(v) in {float, int}:
        return True
    if type(v) == bytes:
        v = v.decode("utf-8", "surrogateescape")
    if type(v) != str:
        return False
    dotseen = False
    digitseen = False
    i = 0
    while i < len(v):
        if (digitseen and i + 1 < len(v) and
                v[i] == "." and
                not dotseen):
            dotseen = True
            i += 1
            continue
        elif (ord(v[i]) >= ord("0") and
                ord(v[i]) <= ord("9")):
            digitseen = True
            i += 1
            continue
        elif v[i] == "-" and i == 0:
            i += 1
            continue
        return False
    return digitseen


def _container_copy(v, *args, **kwargs):
    if type(v) in {dict, list, set} and len(args) == 0:
        if type(v) == dict:
            return dict(v)
        if type(v) == set:
            return set(v)
        return list(v)
    if hasattr(v, "_translator_renamed_copy"):
        return v._translator_renamed_copy(*args, **kwargs)
    return v.copy(*args, **kwargs)


def _container_insert(v, *args, **kwargs):
    if type(v) == list:
        idx = int(args[0])
        idx = max(0, idx)
        return v.insert(idx, args[1])
    return v.insert(*args, **kwargs)


def _container_del(v, *args, **kwargs):
    if type(v) == list or type(v) == set:
        v.remove(args[0])
        return
    elif type(v) == dict:
        del(v[args[0]])
        return
    if hasattr(v, "_translator_renamed_del"):
        return v._translator_renamed_del(*args, **kwargs)


def _text_pos_from_line_col(s, line, col, start_line=1, start_col=1):
    # XXX: The translator implementation of this intentionally
    # ignores glyphs for simplicity. Only HVM will do this properly.
    if type(s) == bytes:
        s = s.decode("utf-8", "surrogateescape")
    if type(s) != str:
        raise _TypeError("must be used on str or bytes")
    slen = len(s)
    atline = start_line
    atcol = start_col
    i = 0
    while i < slen:
        if line == atline and col == atcol:
            return i + 1  # 1-based indexing.
        elif s[i] == "\r" or s[i] == "\n":
            atline += 1
            atcol = 1
            if (s[i] == "\r" and
                    i + 1 < slen and s[i + 1] == "\n"):
                i += 1
            i += 1
            continue
        atcol += 1
        i += 1
    return None


def _as_hex(v, *args, **kwargs):
    if type(v) != int and type(v) != float:
        return v.as_hex(*args, **kwargs)
    if type(v) == float:
        v = int(round(v))
    vstr = '{:x}'.format(v)
    return vstr


def _to_num(v):
    if type(v) in {int, float}:
        return v
    if not _is_num(v):
        raise _ValueError("Given value can't "
            "be converted to number")
    if type(v) == bytes:
        v = v.decode("utf-8", "surrogateescape")
    assert(type(v) == str)
    while (v.endswith("0") and len(v) > 1 and
            v[-2] != "-"):
        v = v[:-1]
    if v.endswith("."):
        v = v[:-1]
    if "." in v:
        return float(v)
    return int(v)


def _bignum_compare_nums(v1, v2):
    def conv(v):
        if type(v) == str:
            return v
        elif type(v) == bytes:
            return v.decode("utf-8", "surrogateescape")
        if type(v) not in {float, int}:
            raise _TypeError("parameters must be num or str")
        return str(v)
    v1 = conv(v1)
    v2 = conv(v2)
    if not _is_num(v1) or not _is_num(v2):
        raise _TypeError("parameters must contain "
            "properly formatted numbers")
    if "." in v1 or "." in v2:
        if float(v1) > float(v2):
            return 1
        elif float(v1) < float(v2):
            return -1
        return 0
    if int(v1) > int(v2):
        return 1
    elif int(v1) < int(v2):
        return -1
    return 0


def _make_or_get_appcache(v):
    forbidden_chars = {"/", "\\", "*", ":",
        "\"", "~", "?", "|", "<", ">", "\0"}
    if v.strip() != v:
        raise _ValueError("Invalid folder name.")
    for c in v:
        if c in forbidden_chars:
            raise _ValueError("Invalid folder name.")
    if platform.system().lower() == "windows":
        appdata = os.path.expandvars(r'%APPDATA%')
        if not os.path.exists(appdata):
            raise _ResourceError("AppData dir doesn't exist.")
        os.makedirs(os.path.join(appdata, v))
        return os.path.join(appdata, v)
    else:
        home_dir = os.path.abspath(os.path.expanduser("~"))
        if not os.path.exists(home_dir):
            raise _ResourceError("Home dir doesn't exist.")
        os.makedirs(os.path.join(home_dir, ".cache", v))
        return os.path.join(home_dir, ".cache", v)


class _TranslatedVec(collections.abc.Sequence):
    def __init__(self, v):
        self.contents = list()
        assert(len(v) in {2, 3, 4})
        if type(v) == dict:
            idx = 1
            while idx <= len(v):
                self.contents.append(v[idx])
                idx += 1
        else:
            for i in v:
                self.contents.append(i)

    @property
    def x(self):
        return self.contents[0]

    @property
    def y(self):
        return self.contents[1]

    @property
    def z(self):
        return self.contents[2]

    @property
    def w(self):
        return self.contents[3]

    def __iadd__(self, v):
        raise _TypeError("Vecs are immutable.")

    def __isub(self, v):
        raise _TypeError("Vecs are immutable.")

    def __imul(self, v):
        raise _TypeError("Vecs are immutable.")

    def __add__(self, otherv):
        if len(otherv) != len(self.contents):
            raise _TypeError("Can only add to vec with same dimensions.")
        values = []
        idx = -1
        for v in self.contents:
            idx += 1
            values.append(v + otherv[idx])
        return _TranslatedVec(values)

    def __sub__(self, otherv):
        if len(otherv) != len(self.contents):
            raise _TypeError("Can only add to vec with same dimensions.")
        values = []
        idx = -1
        for v in self.contents:
            idx += 1
            values.append(v - otherv[idx])
        return _TranslatedVec(values)

    def __mul__(self, otherv):
        otherv = float(otherv)
        values = []
        for v in self.contents:
            values.append(v * otherv)
        return _TranslatedVec(values)

    def __setitem__(self, no, v):
        raise _TypeError("Vecs are immutable.")

    def __len__(self):
        return len(self.contents)

    def __getitem__(self, i):
        return self.contents[i]

    def __iter__(self):
        for v in self.contents:
            yield v

    def __contains__(self, v):
        return (v in self.contents)

    def __reversed__(self):
        for v in reversed(self.contents):
            yield v

    def count(self):
        return len(self.contents)

    def index(self, v):
        idx = -1
        for i in self.contents:
            idx += 1
            if i == v:
                return idx
        raise ValueError("value not found in vec")


class _TranslatedSet(collections.abc.MutableSet):
    def __init__(self, v=None):
        self.contents = set()
        if v != None:
            for i in v:
                self.contents.add(i)

    def __len__(self):
        return len(self.contents)

    def discard(self, v):
        self.contents.remove(v)

    def __contains__(self, v):
        return (v in self.contents)

    def __iter__(self):
        for v in self.contents:
            yield v

    def add(self, v):
        self.contents.add(v)

    def __add__(self, otherv):
        new_set = _TranslatedSet()
        for value in self.contents:
            new_set.add(value)
        for value in otherv:
            new_set.add(value)
        return new_set

    def __iadd__(self, otherv):
        for value in otherv:
            self.contents.add(value)
        return self


def _make_vec(v):
    return _TranslatedVec(v)


def _make_set(v):
    t = _TranslatedSet()
    oldid = id(t)
    assert(t != None)
    t += v
    assert(t != None)
    assert(oldid == id(t))
    return t


def _has_attr(v, name):
    if name == "str":
        name = "_translator_renamed_str"
    return hasattr(v, name)


def _ensure_all_mods_load(output_dir, mainfilepath, debug=False):
    output_dir = os.path.normpath(os.path.abspath(output_dir))
    for abs_root, dirs, filenames in os.walk(
            output_dir, topdown=False
            ):
        assert(abs_root.startswith(output_dir))
        root = abs_root[len(output_dir):]
        while root.startswith(os.path.sep):
            root = root[1:]

        if "__pycache__" in os.path.normpath(root).split(os.path.sep):
            continue

        modbase = root.replace(os.path.sep, ".")
        for name in filenames:
            if not name.endswith(".py"):
                continue
            modfpath = os.path.normpath(os.path.abspath(
                os.path.join(output_dir, root, name)
            ))
            if (os.path.normpath(os.path.abspath(modfpath)) ==
                    mainfilepath):
                continue
            modname = (modbase + ("." +
                name.rpartition(".py")[0]) if
                name != "__init__.py" else "")
            if (modname == "_translator_runtime."
                    "_translator_runtime_helpers"):
                continue
            if debug:
                print("translator_runtime_helpers.py: debug: "
                    "pre-loading module: " + str((
                    modname, modfpath)))
            import importlib.util
            import sys
            spec = importlib.util.spec_from_file_location(
                modname, modfpath)
            m = importlib.util.module_from_spec(spec)
            sys.modules[modname] = m
            spec.loader.exec_module(m)


def _math_parse_hex(v):
    if type(v) not in {bytes, str}:
        raise _TypeError("Not an str or bytes.")
    if type(v) == bytes:
        v = v.decode("utf-8", "surrogateescape")
    if v.startswith("0x"):
        v = v[2:]
    elif v.startswith("x"):
        v = v[1:]
    if len(v) == 0:
        raise _ValueError("Not a valid hex number.")
    i = 0
    while i < len(v):
        if ((ord(v[i]) < ord('0') or
                ord(v[i]) > ord('9')) and
                (ord(v[i]) < ord('a') or
                ord(v[i]) > ord('f')) and
                (ord(v[i]) < ord('A') or
                ord(v[i]) > ord('F'))):
            raise _ValueError("Not a valid hex number.")
        i += 1
    return int("0x" + v, 0)


def _async_final_bail_handler(err, result, funcname="main"):
    if err != None and not isinstance(err, SystemExit):
        print("Unhandled error in 'later' function: " + str(err))
        print(''.join(traceback.format_exception(
            type(err), err, err.__traceback__)))
        sys.exit(1)


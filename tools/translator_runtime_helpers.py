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


import ipaddress
import math
import os
import socket
import subprocess
import sys
import threading
import time


class _LicenseObj:
    def __init__(self, file_name, text=""):
        self.file_name = file_name
        self.text = text


def _return_licenses():
    return __translator_licenses_list


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
        if int(round(args[0])) <= 0:
            if type(container) == bytes:
                return b""
            return ""
        return container * int(round(args[0]))
    return container.repeat(*args, **kwargs)


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
            if type(container) == bytes:
                return b""
            if type(container) == list:
                return []
            return ""
        return container[i1:i2]
    return container.sub(*args, **kwargs)


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
        tld_pos = v.find(common_told + "/")
        if tld_pos >= 2:
            return True
    if v.find("://") >= 1:
        return True
    return False


def _file_uri_from_path(v):
    if platform.system().lower() == "windows":
        v = (os.path.normpath(v.replace("\\", "/")).
            replace("\\", "/"))
    else:
        v = os.path.normpath(v)
    v = "file://" + urllib.parse.quote(v)
    return v


def _uri_normalize(v):
    import urllib.parse
    v = str(v + "")
    if _looks_like_uri(v):
        if "://" not in v:
            target_part = v
            resource_part = "/"
            if "/" in v:
                resource_part = "/" + v.partition("/")[2]
                target_part = v.partition("/")[0]
            v = ("https://" + target_part +
                urllib.parse.quote(resource_part))
    else:
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
            urllib.parse.quote(v))
    urlobj = urllib.parse.urlparse(v)
    result = (urlobj.scheme.lower() + "://" +
        urlobj.hostname.lower())
    if urlobj.port != None:
        result += ":" + str(urlobj.port)
    resource = urlobj.path
    if not resource.startswith("/"):
        resource = "/" + resource
    result += resource
    return resource


def _uri_to_file_or_vfs_path(v):
    if (not v.lower().startswith("file://") and
            not v.lower().startswith("vfs://")):
        raise ValueError("not a file:// or vfs:// path")
    resource = urllib.parse.unquote(v.partition("://")[2])
    resource = os.path.normpath(resource)
    return resource


class _FileObjFromDisk:
    def __init__(self, path, mode):
        self.binary = "b" in mode
        if not self.binary:
            self.fobj = open(path, mode, encoding="utf-8",
                errors='replace')
        else:
            self.fobj = open(path, mode)

    def read(self, amount=None):
        if amount == None:
            return self.fobj.read()
        amount = int(amount)
        if amount <= 0:
            return (b"" if self.binary else "")

    def write(self, value):
        if not self.binary and type(value) != str:
            raise TypeError("value must be unicode string")
        elif self.binary and type(value) != bytes:
            raise TypeError("value must be bytes value")
        return self.fobj.write(value)

    def close(self):
        self.fobj.close()


class _AsyncOperation:
    def __init__(self, userdata, do_func, callback_func):
        self.started = False
        self.done = False
        self.userdata = userdata
        self.userdata2 = None
        self.do_func = do_func
        self.callback_func = callback_func


_async_ops_lock = threading.Lock()
_async_ops = []
_async_ops_stop_threads = False


class _RequestsFetchObj:
    def __init__(self, request):
        self.request = request
        self.rawobj = self.request.raw

    def recv(self, amount, cb):
        if amount != None:
            amount = int(amount)
        global _async_ops_lock, _async_ops
        def recv_sync(op):
            result = b""
            if amount is None or amount > 0:
                try:
                    result = self.rawobj.read(amount)
                except (OSError, IOError):
                    result = None
            if len(result) == 0 and (
                    amount is None or amount > 0):
                result = None
            _async_ops.acquire()
            op.userdata2 = result
            op.done = True
            _async_ops.release()
        def done_cb(op):
            result = op.userdata2
            op.userdata = None
            op.userdata2 = None
            op.do_func = None
            f = op.callback_func
            op.callback_func = None
            return f(result)
        op = AsyncOperation(self, recv_sync, done_cb)
        _async_ops_lock.acquire()
        _async_ops.append(op)
        _async_ops_lock.release()

    def close(self):
        if self.rawobj is None:
            return
        try:
            self.rawobj.close()
        except (IOError, OSError):
            pass
        self.rawobj = None


def _net_fetch_lookup_name(name, cb):
    try:
        ip = ipaddress.ip_address(name)
        return [str(ip)]
    except ValueError:
        pass
    def async_lookup_do(op):
        ipv6_results = []
        try:
            result = socket.getaddrinfo(
                name, None, socket.AF_INET6)
            if len(result) > 0:
                ipv6_results += [
                    str(entry[4][0]) for entry in result
                ]
        except socket.gaierror as e:
            pass
        ipv4_results = []
        try:
            result = socket.getaddrinfo(
                name, None, socket.AF_INET)
            if len(result) > 0:
                ipv4_results += [
                    str(entry[4][0]) for entry in result
                ]
        except socket.gaierror as e:
            pass
        job.done = True
        job.userdata2 = ipv6_results + ipv4_results
    def done_cb(op):
        result = op.userdata2
        op.userdata = None
        op.userdata2 = None
        op.do_func = None
        f = op.callback_func
        op.callback_func = None
        return f(result)
    op = AsyncOperation(self, async_lookup_do, done_cb)
    _async_ops_lock.acquire()
    _async_ops.append(op)
    _async_ops_lock.release()


def _net_fetch_get(uri, extra_headers=None,
        user_agent="core.horse64.org net.fetch/0.1 (translator)"):
    if not "://" in uri:
        raise ValueError("need web url to fetch from")
    if uri.lower().startswith("file://"):
        fpath = _uri_to_file_or_vfs_path(uri)
        return _FileObjFromDisk(fpath, "rb")
    if (not uri.lower().startswith("https://") and
            not uri.lower().startswith("http://")):
        raise ValueError("unsupported protocol, "
            "supported protocols are http, https, file")
    if extra_headers != None:
        extra_headers = dict(extra_headers)
    clean_keys = []
    for key in extra_headers:
        if key.lower() == "user-agent":
            clean_keys.append(key)
    for key in clean_keys:
        del(extra_headers[key])
    extra_headers["User-Agent"] = str(user_agent + "")
    import requests
    return _RequestsFetchObj(
        requests.get(uri, headers=extra_headers)
    )


def _run_main(main_func):
    def async_jobs_worker():
        while True:
            _async_ops_lock.acquire()
            if _async_ops_stop_threads:
                _async_ops_lock.release()
                return
            if len(_async_ops) == 0:
                _async_ops_lock.release()
                time.sleep(0.1)
            work_job = None
            for job in _async_ops:
                if not job.done and not job.started:
                    job.started = True
                    work_job = job
                    break
            _async_ops_lock.release()
            if work_job:
                try:
                    job.do_func(job):
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
    workers = []
    i = 0
    while i < 16:
        worker_thread = threading.Thread(
            target=async_jobs_worker,
            args=(,))
        worker_thread.daemon = True
        worker_thread.start()
        workers.append(worker_thread)
        i += 1
    return_value = main_func()
    while True:
        _async_ops_lock.acquire()
        if len(_async_ops) == 0:
            _async_ops_lock.release()
            break
        done_op = None
        i = 0
        while i < len(_async_ops):
            if _async_ops[i].done:
                done_op = _async_ops[i]
                _async_ops = (async_ops[:i] +
                    async_ops[i + 1:])
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
        time.sleep(0.01)
    _async_ops_lock.acquire()
    _async_ops_stop_threads = True
    _async_ops_lock.release()
    sys.exit(return_value)

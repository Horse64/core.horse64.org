# Copyright (c) 2020-2024, ellie/@ell1e & Horse64 Team (see AUTHORS.md).
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

#cython: language_level=3, boundscheck=True, infer_types=True, cdivision=True, overflowcheck=False

class HackInfo:
    def __init__(self,
            module=None, package=None,
            start_t=None, end_t=None, insert_t=None,
            insert_replacers=None,
            apply_after_python_translate=None,
            ):
        if apply_after_python_translate not in {True, False}:
            raise ValueError("please specify "
                "apply_after_python_translate")
        self.module = module
        self.package = package
        self.start_t = [
            t for t in start_t if t.strip(" \r\n\t") != ""]
        self.end_t = None
        if end_t != None:
            self.end_t = [
                t for t in end_t if t.strip(" \r\n\t") != ""]
        self.insert_t = None
        if type(insert_t) is list:
            self.insert_t = [
                t for t in insert_t if t.strip(" \r\n\t") != ""
            ]
        self.insert_replacers = None
        if type(insert_replacers) is dict:
            self.insert_replacers = insert_replacers
        self.apply_after_python_translate = (
            apply_after_python_translate
        )
        assert(self.insert_t != None or self.insert_replacers != None)

registered_hacks = []

def register_hack(
        module=None, package=None,
        start_t=None, end_t=None, insert_t=None,
        insert_replacers=None,
        apply_after_python_translate=None,
        ):
    registered_hacks.append(HackInfo(
        module=module, package=package,
        start_t=start_t, end_t=end_t, insert_t=insert_t,
        insert_replacers=insert_replacers,
        apply_after_python_translate=
            apply_after_python_translate,
    ))

def apply_hacks_on_file(
        toks, module, package, is_after_python_translate=None,
        output_hacks_notice=False
        ):
    import translator_hacks
    from translator_syntaxhelpers import (
        split_toplevel_statements, flatten,
        tokenize, untokenize,
    )
    was_tokenized = False
    was_flattened = False
    if (type(toks) == str):
        was_tokenized = True
        toks = tokenize(toks)
    elif (type(toks) == list and
            len(toks) > 0 and type(toks[0]) == list):
        was_flattened = True
        toks = flatten(toks)
    hacks_for_this_file = []
    for hack in registered_hacks:
        if (hack.module == module and (
                hack.package == package or
                (package == "main" and hack.package is None)) and
                len(hack.start_t) > 0 and
                hack.apply_after_python_translate ==
                    is_after_python_translate):
            hacks_for_this_file.append(hack)
    for hack in hacks_for_this_file:
        i = -1
        while i + 1 < len(toks):
            i += 1
            t = toks[i]
            if hack.start_t[0] != t:
                continue

            # See if the full start sequence of our hack matches:
            match = True
            i3 = 1
            endofstart = i + 1
            while i3 < len(hack.start_t):
                while (endofstart < len(toks) and
                        toks[endofstart].strip(" \r\n\t") == ""):
                    endofstart += 1
                if (endofstart >= len(toks) or
                        toks[endofstart] != hack.start_t[i3]):
                    match = False
                    break
                endofstart += 1
                i3 += 1
            if not match:
                continue

            # Try to find the ending for our hack:
            endbegin = endofstart - 1
            endmatch = False
            while endbegin < len(toks):
                if hack.end_t == None:
                    endmatch = True
                    actualend = endbegin
                    break
                endbegin += 1
                actualend = endbegin
                endmatch = True
                i3 = 0
                while i3 < len(hack.end_t):
                    while (actualend < len(toks) and
                            toks[actualend].strip(" \t\r\n") == ""):
                        actualend += 1
                    if (actualend >= len(toks) or
                            toks[actualend] != hack.end_t[i3]):
                        endmatch = False
                        break
                    actualend += 1
                    i3 += 1
                if endmatch:
                    break
            if not endmatch:
                raise ValueError("found start of hack, failed to find end!")

            # Okay, apply actual new contents:
            if output_hacks_notice:
                print("tools/translator.py: warning: " +
                    "in module '" + str(module) + "'" +
                    (" in package '" + str(package) +
                    "'") + ", applying per-file hack " +
                    str(hack))
            in_between = toks[i:actualend]
            if hack.insert_t != None:
                in_between = hack.insert_t
            elif hack.insert_replacers != None:
                i2 = 0
                while i2 < len(in_between):
                    if in_between[i2] in hack.insert_replacers:
                        inner_insert = (
                            hack.insert_replacers[in_between[i2]]
                        )
                        in_between = in_between[:i2] + (
                            inner_insert
                        ) + in_between[i2 + 1:]
                        i2 += len(inner_insert)
                        continue
                    i2 += 1
            toks = toks[:i] + in_between + toks[actualend:]
            i = (i + len(in_between)) - 1
    if was_flattened:
        return split_toplevel_statements(toks)
    elif was_tokenized:
        return untokenize(toks)
    return toks


# Copyright (c) 2024, ellie/@ell1e & Horse64 Team (see AUTHORS.md).
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

def load_honse_tmpl_ex(t, is_str=False, escape_for_html=True):
    if is_str:
        return _HonseTmplObj(t, escape_for_html=escape_for_html)
    with open(tpath, "r", encoding="utf-8") as f:
        contents = f.read()
    return _HonseTmplObj(contents, escape_for_html=escape_for_html)

def load_honse_html_tmpl_from_file(tpath):
    return load_honse_tmpl_ex(tpath, is_str=False, escape_for_html=True)

def load_honse_html_tmpl_from_str(t):
    return load_honse_tmpl_ex(t, is_str=True, escape_for_html=True)

def load_honse_generic_tmpl_from_file(tpath):
    return load_honse_tmpl_ex(tpath, is_str=False, escape_for_html=False)

def load_honse_generic_tmpl_from_str(t):
    return load_honse_tmpl_ex(t, is_str=True, escape_for_html=False)

def honse_tmpl_to_jinja2(t):
    newt = ""
    len_t = len(t)
    i = 0
    while i < len_t:
        if t[i] == "$":
            if i + 1 < len_t and t[i + 1] == "$":
                newt += "$"
                i += 2
                continue
            if i + 1 >= len_t or t[i + 1] != "{":
                new_t += "$"
                i += 1
                continue
            assert(t[i + 1] == "{")
            bdepth = 0
            inner_expr = ""
            i2 = i + 2  # Past the ${.
            while i2 < len_t:
                if t[i2] == "{":
                    bdepth += 1
                    i2 += 1
                    inner_expr += "{"
                    continue
                elif t[i2] == "}":
                    bdepth -= 1
                    i2 += 1
                    if bdepth < 0:
                        break
                    inner_expr += "}"
                    continue
                ilen = get_token_len(t, i2)
                assert(ilen >= 1)
                inner_expr += t[i2:i2 + ilen]
                i2 += ilen
            inner_expr = honse_tmpl_expr_to_jinja2(inner_expr)
            newt += inner_expr
            assert(i2 > i)
            i = i2
            continue
        newt += t[i]
        i += 1
    return newt

class _HonseTmplObj:
    def __init__(self, tmpl_text, escape_for_html=True):
        self.jinja_tmpl = honse_tmpl_to_jinja2(tmpl_text)
        self.escape_for_html = escape_for_html
        self.search_dir = None

    def add_dir(self, search_dir):
        self.search_dir = search_dir

    def apply(self, vars):
        if type(vars) != dict:
            raise TypeError("vars must be a dict")
        result = None
        try:
            import jinja2
            import shutil
            import tempfile
            _some_dir = tempfile.mkdtemp()
            try:
                env = jinja2.Environment(
                    loader=(_some_dir
                        if self.search_dir is None else
                        self.search_dir),
                    autoescape=self.escape_for_html
                )
                tmpl = env.from_string(self.jinja_tmpl)
            finally:
                shutil.rmtree(_some_dir)
            result = tmpl.render(vars)
        except Exception as e:
            print("translator.py: warning: "
                "Templating error: " + str(e))
            raise e
        return result

def get_identifier_len(s, pos):
    len_s = len(s)
    i = pos
    while i < len_s:
        c = s[i]
        if ((i == pos or ((ord(c) < ord('0') or ord(c) > ord('9')))) and
               (ord(c) < ord('A') or ord(c) > ord('Z')) and
               (ord(c) < ord('a') or ord(c) > ord('z')) and
               c != "_" and
               ord(c) <= 127):
            break
        i += 1
    return i - pos

def get_token_len(s, pos):
    if (s[pos] in ["<", ">", "|", "^", "*", "/", "+", "=", "!", "-"] and
            pos + 1 < len(s) and
            s[pos + 1] == "="):
        return 2
    if s[pos:pos + 3] in ["^^="]:
        return 3
    if s[pos] in {" ", "\t", "\n", "\r"}:
        i = pos + 1
        while i < len(s) and s[i] in {" ", "\t", "\n", "\r"}:
            i += 1
        return (i - pos)
    ilen = get_identifier_len(s, pos)
    if ilen <= 0:
        return 1
    return ilen

def get_next_token(s, pos):
    ilen = get_token_len(s, pos)
    assert(ilen >= 1)
    return s[pos:pos + ilen]

def s_to_tokens(s):
    result = []
    i = 0
    assert(type(s) == str)
    slen = len(s)
    while i < slen:
        t = get_next_token(s, i)
        assert(len(t) > 0)
        result.append(t)
        i += len(t)
    return result

def _next_t(ts, i=None):
    if i == None:
        i = 0
    tslen = len(ts)
    while i < tslen:
        if ts[i].strip(" \n\r\t") != "":
            return ts[i]
        i += 1
    return None

def honse_tmpl_expr_to_jinja2(inner_expr):
    is_control_flow = False
    result = ""
    tokens = s_to_tokens(inner_expr)
    if _next_t(tokens) in ["if", "for", "endif", "endfor"]:
        is_control_flow = True
    for t in tokens:
        if t == "none":
            t = "None"
        elif t == "yes":
            t = "True"
        elif t == "no":
            t = False
        result += t
    if is_control_flow:
        return "{" + "% " + ("".join(tokens)).strip("") + " %" + "}"
    else:
        return "{" + "{ " + ("".join(tokens)).strip("") + " }" + "}"


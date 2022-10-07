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


import textwrap
import unittest

from translator_syntaxhelpers import (
    tokenize, untokenize, expr_nonblank_equals
)

from translator_transformhelpers import (
    transform_h64_misc_inline_to_python
)


class TestTranslatorTransformHelpers(unittest.TestCase):
    def test_transform_h64_misc_inline_to_python(self):
        t = ("var test = " +
            "(\"complex string concat test: \" + f(l, 1).as_str())")
        texpected = ("var test = " +
            "(\"complex string concat test: \" + " +
            "str(f(l, 1)))")
        tresult = transform_h64_misc_inline_to_python(t)
        self.assertTrue(expr_nonblank_equals(tresult, texpected),
            msg=("got " + tresult + ", expected: " + texpected))

        t = ("args = args.sub(0, double_dash_idx) +" +
            "    args.sub(double_dash_idx + 1)")
        texpected = ("args = _translator_runtime_helpers." +
            "_container_sub(args, 0, double_dash_idx) +" +
            "    _translator_runtime_helpers._container_sub(" +
            "args, double_dash_idx + 1)")
        tresult = transform_h64_misc_inline_to_python(t)
        self.assertTrue(expr_nonblank_equals(tresult, texpected),
            msg=("got " + tresult + ", expected: " + texpected))

if __name__ == '__main__':
    unittest.main()

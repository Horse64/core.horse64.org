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

#cython: language_level=3, boundscheck=True, infer_types=True, cdivision=True, overflowcheck=False

cdef is_keyword(x)

cdef identifier_or_keyword(str x)

cdef is_identifier(str v)

cdef nextnonblank(list t, int idx, int no=*)

cdef nextnonblankidx(list t, int idx, int no=*)

cdef prevnonblank(list t, int idx, int no=*)

cdef prevnonblankidx(list t, int idx, int no=*)

cdef firstnonblank(t)

cdef firstnonblankidx(t)

cdef str get_next_token(str s)

cdef int is_h64op_with_righthand(str v)

cdef int is_h64op_with_lefthand(str v)

cdef is_whitespace_token(str s)

cpdef tokenize(str s)

cpdef get_next_statement(list s, int pos)

cpdef sanity_check_h64_codestring(s, filename=*, modname=*)

cpdef untokenize(tokens)

cpdef split_toplevel_statements(s, skip_whitespace=*)

cpdef tokens_need_spacing(str v1, str v2)

cpdef transform_h64_with_to_do_rescue(_s)

cpdef is_bracket(str v)

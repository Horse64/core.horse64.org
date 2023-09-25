
Runtime Concerns
================

Get the Horse64 runtime as part of the [SDK](
/docs/Resources.md#SDK). This document talks about
technical detail concerns you might have regarding the
runtime.


Garbage Collection
------------------

To make Horse64 powerful to use while still efficient for the
programmer, it helps you out with automatic memory management
using an approach *Garbage Collection*. This is implemented
in [HVM](/docs/Resources.md#HVM).

Generally, [data types](/docs/Language Specs/Data%20Types.md) that
allow referencing to other values that may reference back in cycles
need more complex cleanup. Therefore, they cause so-called
*GC load* when created. Items that can't produce complex cyclic
references are cheaper to handle (in terms of computation time)
and therefore may make your code faster if used instead.


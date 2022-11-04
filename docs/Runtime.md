
Runtime
=======

The runtime of the Horse64 programming language is **HVM**,
which is short for "Horse Virtual Machine". You can find its
[source code here](docs/Resources.md#HVM).


Garbage Collection
------------------

To make Horse64 powerful to use while still efficient for the
programmer, it helps you out with automatic memory management
using an approach *Garbage Collection*. This is implemented
in [HVM](docs/Resources.md#HVM), and it means that unused
objects and items will be automatically freed from memory after
they're no longer referenced anywhere. This lowers the risk
of your code causing [memory leaks](
https://cwe.mitre.org/data/definitions/401.html) and
even more effectively removes the pitfall of [use-after-free
programming errors](
https://cwe.mitre.org/data/definitions/416.html) in your code.
However, it also takes up some computation time for taking
care of memory book-keeping.

Generally, [data types](docs/Language Specs/Data Types.md) that
allow referencing to other values that may reference back in cycles
need more complex cleanup. Therefore, they cause so-called
*GC load* when created. Items that can't produce complex cyclic
references are cheaper to handle (in terms of computation time)
and therefore may make your code faster if used instead.


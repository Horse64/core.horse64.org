
# Grammar

This section describes the grammar of the Horse64 programming
language.


## Overview

Horse64's grammar is inspired by the [Go](https://golang.org),
[Lua](https://lua.org), and [Python programming
language](https://python.org)s. It's meant to be verbose enough to be
beginner-friendly while still minimal:

```Horse64
func main {
    print("Hello World!")
}
```

Here's an overview of the basic differences and properties
of Horse64's grammar compared to other programming languages:


### No Line Terminators

In some other languages like the [C programming language](
https://en.wikipedia.org/wiki/C_%28programming_language%29),
statements always end with some statement terminating character
like a `;` at the end, others like the [Python programming
language](https://python.org) have a statement terminating character
for at least optional use. This is not the case in Horse64,
statements just end where they naturally end.


### No Significant Whitespace

In some other languages like the [Python programming
language](https://python.org), indent via space or
tabulator characters or line breaks
play a role in where statements start or end. This is usually
called "significant whitespace".

Horse64 doesn't have such significant whitespace, all code
can technically be written with whatever
indent or even in one long line. The only exception are comments
that begin with `#` and always end at the next line break.


### Statement Start Restrictions

A statement can't ever begin with:

* `(` or `[` opening brackets (`{` opening bracket is allowed)

* a `new` operator

This is forbidden to avoid ambiguity with the previous statement's
ending given Horse64's [lack of significant whitespace](
#no-significant-whitespace).


### (Pitfall) `return` Statements That Aren't At Block Ends

A `return` statement may have an expression following to be
returned but it's optional.
This can lead to seeming ambiguity, which can be easily avoided
with this advice:

> **(Advice)** You shouldn't put a `return` statement anywhere
  but right before the closing `}` bracket of a code block.

An example follows where ignoring this advice is confusing:

```Horse64
func main {
    return

    # ...not heeding above advice, this is an example of not ending
    # the block after a `return`, but instead adding another call:
    call_my_func()

    # This is misleading, since here's what the compiler sees:
    #   return call_my_func()
}
```



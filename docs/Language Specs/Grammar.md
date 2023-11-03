
<!-- For license of this file, see LICENSE.md in the base folder. -->

Grammar
=======

This section describes the grammar of the Horse64 programming
language.


Overview
--------

Horse64's grammar is inspired by the [Go](https://golang.org),
[Lua](https://lua.org), and [Python](https://python.org)
programming languages. It's meant to be verbose enough to be
beginner-friendly while still minimal:

```Horse64
func main {
    print("Hello World!")
}
```

Here's an overview of the basic differences and properties
of Horse64's grammar compared to other programming languages:


### No line terminators

In some other languages like the [C programming language](
https://en.wikipedia.org/wiki/C_%28programming_language%29),
statements always end with some statement terminating character
like a `;` at the end, others like the [Python programming
language](https://python.org) have a statement terminating character
for at least optional use. This is not the case in Horse64,
statements just end where they naturally end, and there
is no optional character to end them more explicitly.


### No significant whitespace

In some other languages like the [Python programming
language](https://python.org), indent via space or
tabulator characters or line breaks
play a role in where statements start or end. This is usually
called "significant whitespace".

Horse64 doesn't have such significant whitespace, all code
can technically be written with whatever
indent or even in one long line. The only exception are comments
that begin with `#` and always end at the next line break.


### Statement start restriction

A statement can't ever begin with some specific items:

* `(` or `[` opening enclosing marks are forbidden,
  while a `{` opening brace is allowed,

* a `new` operator is forbidden,

* an inline `if` is forbidden,
  while a standalone `if` statement start is allowed.

All these are forbidden to avoid ambiguity
given the grammar's [lack of significant whitespace](
#no-significant-whitespace). If you use them anyway,
expect to get yelled at by [horsec](/docs/Resources.md#horsec).


### Pitfall of `return` statements that aren't at block end

A `return` statement may have an expression following to be
returned but it's optional.
This can lead to seeming ambiguity, which can be easily avoided
with this advice:

> **Advice:** You shouldn't put a `return` statement anywhere
  but right before the closing `}` brace of a code block.

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


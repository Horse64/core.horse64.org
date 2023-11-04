
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

Formal listing
--------------

For the formal rules of the grammar, [go here for a listing](
/docs/Language%20Specs/Grammar%20Rules.md).


Operators
---------

Horse64 supports the following operators, all of which
will raise a `TypeError` if not applied to the supported
types specified:

### Math operators (`T_MATH`)

Regular: `+`, `-`, `*`, `/`, `%`, `**',
and bitwise: `<<`, `>>`, `~`, `&`, `|`, `^`.

*(All operators except for `-` always take a left-hand
and right-hand side, so they're all binary operators)*

- They can be applied to any pair of numbers, the
  bitwise ones will round the number to an integer
  first if it has a fractional part.

- The `+` operator can also be applied to two strings or
  two lists or two sets or two vectors,
  and the `-` operator can also be used as a unary operator.

### Comparison operators (`T_COMPARE`)

`==`, `!=`, `>`, `<`, `>=`, `<=`.

*(These all take a left-hand and right-hand side,
so they're all binary operators)*

- The first two, `==` and `!=`, can be applied to any types,
  the others to either a pair of numbers, or a pair of strings
  which compares them based on unicode code point values.
  All comparisons evaluate to either boolean `yes` or boolean `no`.

### Boolean operators (`T_BOOLCOMP`)

`not`, `and`, `or`.

*(The `not` operator only takes a right-hand side
and is therefore unary, the others are binary operators.)*

- All of these can be applied to any pair of booleans,
  and will return a boolean (`yes`/`no`).

- The `and` operator will only evaluate the right-hand side
  if the left-hand turns out to be boolean `yes`.

- The `or` operator will only evaluate the right-hand side
  if the left-hand turns out to be boolean `no`.

### `new` operator (`T_NEWOP`)

`new`.

*(It just takes a right-hand side, it's an unary operator.)*

Example: `new type_name(arg1, arg2)`

- This operator can be applied to an identifier that
  refers to a type, an expression referring to a variable
  previously assigned to a type, combined with arguments
  for the constructor.

- The operator evaluates to an object instance, or it may
  raise any error caused by the `init` function
  attribute when run.

### Index by expression operator

`[` with closing `]`.

*(It takes both a right-hand and left-hand side,
so it's a binary operator)*

Example: `somecontainer[<indexexpr>]`.

- This operator can be applied to any container of type
  list or vector, and takes a number type for indexing. It
  evaluates to the respective nth list or vector item.

- If the number passed in is lower than `1` or higher than
  the amount of items, an `IndexError` will be raised.

### Attribute by identifier operator

`.` (dot).

*(It has both right- and left-hand side,
it's a binary operator)*

Example: `someitem.identifier`.

- The item can be any arbitrary expression.
  The operator can be applied on any item, even numbers or
  booleans or even none, but will raise an `AttributeError`
  if the given data type doesn't have this attribute.

- For object instances created from your [custom types](
  /docs/OOP#custom-types-in-horse64) via `new`, the attributes
  are as specified by your type. Beyond that, many values
  have special attributes, see the [data types listing](
  /docs/Language%20Specs/Data%20Types.md) for these.
  E.g., all values have the `.as_str()` attribute
  that when called returns a string value representing them.

### Call operator

`(` with closing `)`.

*(Also a binary operator with left- and right-hand side.)*

Example: `left_hand_called_side(right_hand_argument_side)`

- This calls the left-hand side with the given arguments
  inside the parenthesis.

### Operator precedences

If operators aren't clearly nested via parenthesis to indicate
evaluation order, then it is determined by operator precedence.
For simplicity, precedence is presented here by pasting the
according implementation code of [horsec](../horsec/horsec.md)
found in `src/compiler/operator.h64`:

```
var precedence_table = [  # From closest-binding to loosest:
    ["new"],
    [["-", token.T_UNARYMATH]],
    ["~", "&"],
    ["|"],
    ["^"],
    ["/", "*", "%", "**"],
    ["+", ["-", token.T_MATH]],
    ["<<", ">>"],
    ["==", "!="],
    [">=", "<="],
    [">", "<"],
    ["not"],
    ["and"],
    ["or"],
]
```


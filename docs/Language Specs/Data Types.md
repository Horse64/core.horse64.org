
<!-- For license of this file, see LICENSE.md in the base folder. -->

Data Types
==========

This section describes the data types available in the Horse64
programming language.


Overview
--------

| Data type name   | How to instantiate        | Mutable | GC load |
|------------------|---------------------------|---------|---------|
| none             | `none`                    | no      | no      |
| num              | `1`, `1.0`, `-2.332`      | no      | no      |
| str              | `"bla"`, `'bla'`, `""`    | no      | no      |
| bytes            | `b"test"`, `b''`          | no      | no      |
| bool             | `yes`, `no`               | no      | no      |
| vec              | `[x:1, y:5, z:3, w:1.1]`  | no      | no      |
| list             | `[]`, `[1, 2]`            | yes     | yes     |
| map              | `{"price"-> 5.0}`, `{->}` | yes     | yes     |
| set              | `{}`, `{1, 2}`            | yes     | yes     |
| type             | `new MyCustomType()`      | yes     | yes     |
| func             | `var f = func test {}`    | no      | no      |

Mutable types are passed by reference, immutable ones by value.

*(Read more [here about GC load](
/docs/Runtime%20Concerns.md#garbage-collection).)*


Custom data types with `type`
-----------------------------

So-called *custom types*, or in short just types, are declared via
the [type keyword](
/docs/Language%20Specs/Overview.md#oop-in-horse64-by-using-type).
Internally, they're basically just a struct like in [C/C++](
https://en.wikipedia.org/wiki/C_%28programming_language%29) which
contains a reference to the `type` definition they belong to,
as well as all the values of the var attributes they have.

Since custom types can have var attributes pointing to other types
and back in circles, they're allocated on the [
GC heap](/docs/Runtime%20Concerns.md#garbage-collection)
causing GC load.


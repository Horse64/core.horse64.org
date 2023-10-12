
<!-- For license of this file, see LICENSE.md in the base folder. -->

Concurrency model of Horse64
============================

Horse64's concurrency model has the following properties:

- It has two types of functions, the concurrent *"later functions"*
  and the regular ones, that both need to be called differently.

- The execution is concurrent as in interleaved, but not threaded
  as in not parallel. Interleaving happens only at the `later`
  call points or when one execution chain fully ends.

- The concurrency is handled fully at compile time and
  reshaped by the compiler into closures under the hood.

- The concurrency has no promise objects or greenlet objects
  of any kind to pass around, it's a very lightweight and minimal
  model.

- All standard library functionality that might be blocked on
  external resources aims to be concurrent, and so should you
  in that case.


Formal rules for calling later `func`s
--------------------------------------

The rules for calling later functions are as follows:

1. Calls to later functions must be followed by either `later:`
   or `later ignore`, or `later repeat`.

2. The call cannot be a nested inline call inside a
   bigger expression. It needs to be a standalone call statement,
   or right-hand to a variable definition or simple assignment.
   A `later ignore` call's return value needs to be ignored.

3. If the call's return value is assigned to a variable,
   it needs to be `await`ed after a `later:`.

4. Calling any later function with `later:` or `later repeat`
   makes the surrounding calling function also a later function.

5. Otherwise, using `return later ...` in a function will also
   make it a later function.

6. Returning anything from a later function may cause other
   functions and program parts to run in between, rather than
   a guaranteed direct return to the caller. The same applies
   for calling any later function.


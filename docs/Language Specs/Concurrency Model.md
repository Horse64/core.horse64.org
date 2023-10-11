
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


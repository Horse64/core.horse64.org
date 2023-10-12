
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
   or right-hand to a variable definition or simple assignment to
   a local variable. A `later ignore` call's return value must be
   ignored. Examples:

     ```Horse64
     import net.fetch from core.horse64.org
     func main {
         # Valid calls:

         net.fetch.get_str(
            "https://horse64.org"
         ) later ignore

         var value = net.fetch.get_str(
            "https://horse64.org"
         ) later:
         await value  # Required.

         # Invalid calls:

         value["abc"] = net.fetch.get_str(
            "https://horse64.org"
         ) later:  # Not allowed, a complex assignment.
         await value["abc"]

         var value2 = net.fetch.get_str(
            "https://horse64.org" 
         ) later ignore  # Not allowed, must ignore return value.
     }
     ```

   A `later ignore` call's return value needs to be ignored,
   and if the return value was assigned it needs to be
   `await`ed after a `later:`.

3. Calling any later function with `later:` or `later repeat`
   makes the surrounding calling function also a later function.

4. Otherwise, using `return later ...` in a function will also
   make it a later function. It's otherwise not needed, any
   return in a later function is possibly returned later (after
   a time skip).

5. Returning anything from a later function may cause other
   functions and program parts to run in between, rather than
   a guaranteed direct return to the caller. The same applies
   for calling any later function.

6. Currently, later calls can't be inside a `while` or `for`
   loop. Instead, use a `later:` ... `later repeat` loop
   if needed.

7. You cannot nest `later:` ... `later repeat` loops. Both
   paired calls must be in the same code block. Both paired
   calls must assign their return value, and they must assign
   it to the same local variable. [See here for an
   example of `later repeat` loops.](
   /docs/Concurrency.md#later-repeat)


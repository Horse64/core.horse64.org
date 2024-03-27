
<!-- For license of this file, see LICENSE.md in the base dir. -->

Introduction to Horse64 Concurrency
===================================

Horse64 has a built-in handing for async, or so-called concurrent
functions. These usually depend on external I/O or networking.


Basic concurrent call
---------------------

To avoid that any external resources stalling will freeze your
program, functionality like disk or network access in Horse64 is
*concurrent*. This means that while it happens, other code
in your program can continue to run.

You call any concurrent functions annotated with the `later`
keyword, indicating a **time skip, see this call example:**

  ```Horse64
  import net.fetch from core.horse64.org
  func main {
      var contents = net.fetch.get_str(
          "https://horse64.org"
      ) later:  # Execution after this runs later, after a time skip.

      await contents  # Access the results of your async call.
      print("Obtained website contents: " + contents)
  }
  ```

Concurrent functions in Horse64 are also called *"later functions"*.
During the time skip, any other code can still run which will keep
[any parallel executions your program has still going](
#running-code-in-parallel) resuming smoothly.

The `await` keyword extracts the results, and causes errors
to bubble up that happened in the call, if any.
**Here is how you catch errors after the time skip:**

  ```Horse64
  import net.fetch from core.horse64.org

  func main {
     var contents = net.fetch.get_str(
         "https://horse64.org"
     ) later:  # Execution after this runs later, after a time skip.

     do {
         await contents  # Errors bubble up here.
         print("Obtained website contents: " + contents)
     } rescue NetworkIOError {
         print("Oops, our download failed!")
     }
  }
  ```


Running code in parallel
------------------------

The real gain from concurrency comes from running multiple
things in parallel, which will then not interrupt each other:

  ```Horse64
  import net.fetch from core.horse64.org
  import time from core.horse64.org

  func parallel_counter {
      print("This is my parallel logic!")
      var i = 1
      while i < 10 {
          print("Tick")
          time.sleep(0.5)
          i += 1
      }
      return i
  }

  func main {
     var contents, count = net.fetch.get_str(
         "https://horse64.org"
     ), parallel_counter()
     later:  # Execution after this runs later, after a time skip.

     do {
         await contents, count  # Errors bubble up here.
         print("Obtained website contents: " + contents)
     } rescue NetworkIOError {
         print("Oops, our download failed!")
     }
  }
  ```


`later ignore`
--------------

**Don't want to wait?** If you don't care about a later
function's return value or its success, you can follow
the call up with `later ignore`. This will make
them run in the background in parallel as well:

  ```Horse64
  import net.fetch from core.horse64.org

  func main {
      net.fetch.get_str(
         "https://horse64.org"
      ) later ignore  # <- We don't care about success or return value.

      print("The internet fetch is likely still in progress now,
            but we don't care.")
  }
  ```

In this case, the execution won't be delayed until the
later call fully completes but instead continue without
a possibly long time skip.


`later repeat`
--------------

Since later calls aren't supported by [horsec](/docs/Resources.md#horsec)
inside loops like `for` or `while`, whenever you need to
call later functions in some repeating block,
use `later repeat` instead in a pair like this:

**Note:** the repeat call at the bottom can be
passed different arguments whenever that comes in handy!

  ```Horse64
  import my_line_fetch

  func main {
      var line = my_line_fetch.next_line(
          "https://horse64.org"
      ) later:

      await line
      print("Here's another line: " + line)

      line = my_line_fetch.next_line(
          "https://horse64.org"
      ) later repeat  # Jumps back up to right after `later:`
  }
  ```

**Note:** both calls of such a `later repeat` pair must
assign to the same variable.


`with ... later`
----------------

To use a concurrently created resource inside a [with statement](
/docs/Error%20Handling.md#with-statement), instead of
`with create_my_resource_non_concurrent() as my_name { ... }`
use `with create_my_resource_concurrent() later as my_name { ... }`.

This is needed for all cases where the create function
is a later function and hence it can only be called concurrently.

(You can always call normal functions with `later` as well,
but a later function can't be called *without* `later`.)


Further reading
---------------

For the [formal calling rules, go here](
/docs/Language%20Specs/Concurrency%20Model.md#formal-rules-for-later-funcs).

**Note on race conditions:** concurrent functions don't run
truly in parallel. Only during the time skips, so during
your `later` calls, can other interleaved later functions run.
[See more on the formal concurrency model here.](
/docs/Language%20Specs/Concurrency%20Model.md)


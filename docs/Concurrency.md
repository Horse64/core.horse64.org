
<!-- For license of this file, see LICENSE.md in the base folder. -->

Introduction to Horse64 Concurrency
===================================

Horse64 has a built-in handing for async, or so-called concurrent
functions. These usually depend on external I/O or networking.


Basic concurrent call
---------------------

To have stalling external resources not freeze your program,
you call any concurrent functions such that there's a time skip
where other code of yours may run.
**Here is how to do a concurrent call via the `later` keyword:**

  ```Horse64
  import net.fetch from core.horse64.org
  func main {
      var contents = net.fetch.get_str(
          "https://horse64.org"
      ) later:  # <- Execution after this runs later, after a time skip.

      await contents  # <- You're acknowledging this resouce must be ready.
      print("Obtained website contents: " + contents)
  }
  ```

Concurrent functions in Horse64 are also called *"later functions"*
which is how [horsec](/docs/Resources#horsec) usually names them.

Calls to such later functions must always be followed by `later`
for a time skip, and then `await` on their return value.
The await is where errors bubble up, **so here is how you catch
errors after the time skip:**

  ```Horse64
  import net.fetch from core.horse64.org
  func main {
     var contents = net.fetch.get_str(
         "https://horse64.org"
     ) later:  # <- Execution after this runs later, after a time skip.

     do {
         await contents  # <- Errors bubble up here.
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
the call up with `later ignore`:

  ```Horse64
  import net.fetch from core.horse64.org
  func main {
      net.fetch.get_str(
         "https://horse64.org"
      ) later ignore  # <- We don't care if it succeeds or what it returns.

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
inside `for` or `while`,
do loops via `later` repeat instead (which must assign to the same
local variable in both calls):

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


Further reading
---------------

For the [formal calling rules, go here](
/docs/Language%20Specs/Concurrency%20Model.md#formal-rules-for-later-funcs).

**Note on race conditions:** concurrent functions don't run
truly in parallel. Only during the time skips, so during
your `later` calls, can other interleaved later functions run.
[See more on the formal concurrency model here.](
/docs/Language%20Specs/Concurrency%20Model.md)


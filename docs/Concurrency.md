
<!-- For license of this file, see LICENSE.md in the base folder. -->

Introduction to Horse64 Concurrency
===================================

Horse64 has a built-in handing for async, or so-called concurrent
functions. These usually depend on external I/O or networking.

To have stalling external resources not freeze your program,
you call any concurrent functions such that there's a time skip
where other code of yours may run. This happens via the `later` keyword:

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

## Rules for calling later functions

The rules for calling later functions are as follows:

1. Calls to later functions must be followed by `later`
   to indicate that there is a time skip. Such calls must be in
   their own statement.

2. After the time skip, you must `await` the return value. This
   await statement will cause any runtime errors to bubble up,
   so you can put it into `do ... rescue` to handle them:

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

3. Usually, later functions will have a return value that you
   can reasonably `await` and then use.

4. If you don't care about a later function's return value or
   its success, you can follow the call with `later ignore`.
   In that case, execution continues immediately:

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

## Rules for creating later functions

The rules for creating your own later function are as follows:

1. Any function that contains a `later` call that is **not**
   followed by `later ignore`, so there's an actual time skip,
   itself automatically becomes a later function.

2. If you want a function to be a later function despite no
   no `later` call being inside, use `return later ...`. This
   allows other scheduled concurrent functions to run right
   in the time slot between the function ending, and execution
   returning to its caller function. (This can be useful to
   avoid blocking other functions for too long, if you have
   any others stuck waiting to resume after a time skip.)

3. Remember, a later function needs to be called with `later`.
   A regular function *can't* ever be called with `later`.

**Note on race conditions:** concurrent functions don't run
truly in parallel. Only during the time skips, so during
your `later` calls, can other interleaved later functions run.
[See more on the formal concurrency model here.](
/docs/Language%20Specs/Concurrency%20Model.md)


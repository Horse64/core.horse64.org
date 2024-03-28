
<!-- For license of this file, see LICENSE.md in the base dir. -->

Concurrency model of Horse64
============================

Horse64's concurrency model has the following properties:

- It has two types of functions, the concurrent *"later functions"*
  and the regular ones, while the former ones need to be called
  differently. Regular ones can always also be called as later func.

- Any concurrent execution is interleaved, with execution switching
  over at any `later:` time skip.

- **If your program ever launches things [in parallel](
  /docs/Concurrency.md#running-code-in-parallel), then
  [be careful to avoid race conditions](#avoiding-race-conditions).**

- However, immediate parallel execution isn't guaranteed even with
  `later parallel`. It only happens if there is a free [worker](
  /docs/Runtime%20Concerns.md#vm-worker-threads).
  If there isn't one, parallel functions might **stall and wait**.

  In practice, this is only a problem if you have multiple long-running
  functions without any internal `later` calls to break them up,
  all running at the same time, and enough that each occupies one
  of the [VM workers](/docs/Runtime%20Concerns.md#vm-worker-threads).

  To work around that, break up particularly long-running computations
  up into multiple later functions that you call sequentially.

- Technically, concurrency is handled fully at compile time and
  reshaped by the compiler into closures under the hood.


Avoiding race conditions
------------------------

If you never launch things in parallel, other funcs can only
ever interleave during `later:` time skips. Therefore, you
don't need any special precautions if you **never use `parallel`.**

**If anywhere in your code you [use parallelism via
the `parallel` keyword](
/docs/Concurrency.md#running-code-in-parallel),
then continue reading:**

Basic access like indexing, setting or getting an attribute or
a variable, and so on are all thread-safe. Basically, each
single operation seen in a Horse64 code file is made to be
atomic, including `+=` and similar operators. Any other
truly parallel later call will either see the old value
or the new one, never any corrupted in-between.

However, you'll need a [threading lock (mutex)](/docs/FIXME) if:

1. You launch funcs truly in parallel by using `later parallel`,

2. **and** more than one of these funcs are written to use a shared
   object or value (see next point),

3. **and** this shared complex object or value is ever accessed via
   multiple operations that depend on each other.

   This is e.g. the case if you get the length of
   a list in one line (which in itself is thread-safe), and then
   index the list based on the obtained index in a separate line.

   This is e.g. also the case if you want to change two
   attributes on a [custom object](#custom-types-in-horse64) and
   other parallel funcs are meant to only access the object
   with either none, or both of these values changed.

**Note:** not using a threading lock for parallel access
can cause **⚠️ severe and insidious program errors** like
unpredictable wrong results, timing-induced failures, and
crashes of your code. ([HVM itself](/docs/Resources.md#hvm)
should handle it fine, but your code may not.)

**Note:** make sure to check any third-party Horse64 libraries
to ensure they won't unexpectedly run funcs of your own in
parallel either, for example via callbacks. The official
integrated functionality doesn't do this without a warning in
its documentation and also shouldn't ever do this by default.


Formal rules for later `func`s
------------------------------

*(These are the formal rules, for a gentle introduction
on calling so-called "later functions", [go here
for examples](/docs/Concurrency.md).)*

The rules for calling later functions are as follows:

### Rule 1: All "later" calls need special syntax.

Calls to later functions must be followed by either `later:`
or `later ignore`, or `later repeat`. Calls to regular
functions can use this syntax, or regular calls.
This means you need to know in advance if the
function you're calling is possibly a later function, **but
the compiler will in many cases tell you when you did it wrong**
before you even run the program. For the other uncaught
cases, you'll get an `InvalidCallError` whenever you
call a later function incorrectly.

### Rule 2: You can't inline nest later calls.

Any later call cannot be a nested inline call inside a
bigger expression. It needs to be a standalone call statement,
or right-hand to a variable definition, or
right-hand to simple assignment to
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

A `later ignore` call's return value needs to be ignored.
After a regular `later:` call, the return value that was
assigned needs to be `await`ed.

### Rule 3: Calling later marks a function.

Calling anything with `later:` or `later repeat`
makes the surrounding calling function also a later function.
This excludes `later ignore` calls, making this the only
way to call a later function while keeping the caller
a regular function.

### Rule 4: Return later marks a function.

A `return later ...value...` denotes after a return after a
time skip, and also makes the surrounding function a later
function.
Any function with neither a later call or a return later
is automatically a normal function.

### Rule 5: A later function has implicit delayed returns:

Once a function is a later function, for any `return`,
a `return later` is assumed. This means if you already have
`later:` calls in the same function, you can omit the
explicit `return later` use if you want.

### Rule 6: A time skip can cause interleaved execution.

Any later call and any later return may cause both a
time delay, and for other functions and program runs to run
in between, excluding only `later ignore` calls.
**Write your code accordingly to avoid race conditions.**
Neither regular later calls nor
`later ignore` calls **have any guarantees to run any code
immediately** of the called function, or in any specific
time frame, it's merely run timely on a best-effort basis.
Also, for all the later functions waiting to run
or resume, there's **no guaranteed ordering** of execution.

### Rule 7: `later repeat` replaces later inside loops.

Later calls can't be inside a `while` or `for`
loop due to technical limitations. While this might
change at some point, there are currently no plans.
Instead, you can use a `later:` ...code... `later repeat`
loop whenever needed.

### Rule 8: You can't nest later repeats.

You mustn't nest `later:` ...code... `later repeat`
loops inside each
other. Both paired calls must be in the same code block.
Both paired calls must assign their return value, and they
must assign it to the same local variable. [See here for an
example of `later repeat` loops.](
/docs/Concurrency.md#later-repeat)


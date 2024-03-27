
<!-- For license of this file, see LICENSE.md in the base dir. -->

Migrating from Other Languages
==============================

**This is a tutorial for people who can already program in
Python, Javascript, or Lua,** but who aren't familiar with Horse64
yet.

This tutorial will go over the main differences that you might
not be expecting.


Basic syntax differences
------------------------

Compared to Python, Javascript, or Lua, the syntax of Horse64
can all be written in one line but uses curly braces:

  ```Horse64
  func main { print("Hello World! Better use line breaks though.") }
  ```

It's not encouraged to write everyhing in one line or to avoid
indentation, but the compiler won't get in your way if you do.


Program structure
-----------------

In comparison, Horse64 is probably most similar to a Python
program with its layout. Any program will have a main function:

```Horse64
func main {
    print("Hello World! My program started in the main func.")
}
```

From then on, you can import any neigboring code files for
use as modules.

**Note:** In Horse64, **code can't be outside
a `func`** like it could in Python, Javascript, or Lua.

Even a simple script must have a `func main` starting point!


Starting a program
------------------

Python, Javascript, or Lua usually are used to run a program
directly, like in this run command example:

```bash
python my_project/my_python_program.py
```

When using Horse64, instead you'll want to compile the program
first (which allows better safety analysis and optimization):

```bash
horsec compile -o program my_project/my_horse64_program.h64
./program
```

You can also run a Horse64 script directly, but the launch
might be slightly delayed:

```bash
horserun my_horse64_script.h64
```


Concurrency and its differences
-------------------------------

You'll notice pretty early that Horse64 often uses so-called
"later functions" that must be called with `later:` or similar.
These are like **async in Python or Javascript** or like
coroutines in Lua.

Here's a more in-depth comparison of differences:

Here is an **async example in JavaScript**:

```JavaScript
function my_function() {
    var delayed_result = some_func_that_is_async_but_you_wouldnt_see()
    do_something()  // This call runs automatically in parallel with
                    // the above, but you can't easily see that.
    await delayed_result  // May do a time skip if by now, your
                          // original async call hasn't completed.
}
```

Here is a **later call example in Horse64**:

```Horse64
func my_function {
    var delayed_result = some_func_that_is_async()
    later:  # This marker is mandatory and tells you the call above is
            # concurrent, and marks a clear expected time skip.

    do_something()  # This will actually NOT run in parallel but after
                    # above call fully completed.
    await delayed_result  # Make result available and bubble up errors.
                          # This will never cause a delay or time skip.
}
```

As you can see, in Horse64 the time skips and concurrent calls are,
unlike in other languages, syntactically obvious and not hidden.

This makes the code flow easy and transparent to the reader.

**If you wanted `do_something` in parallel in Horse64 like above**:

```Horse64
func my_function {
    var delayed_result, _unused = some_func_that_is_async(),
        do_something()
    later:

    ...
}
```

As you can see, Horse64 can run things at the same time just like
Python or JS can, but you'll have to be obvious about it.

[**Continue reading here for more concurrency** explained
more in-depth for Horse64](/docs/Concurrency.md).


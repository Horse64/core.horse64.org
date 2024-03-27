
<!-- For license of this file, see LICENSE.md in the base dir. -->

Migrating from Other Languages
==============================

**This is a tutorial for people who can already program in
Python, Javascript, or Lua,** but who aren't familiar with Horse64
yet.

This article will explain what differences might surprise you the most.


Feature comparison
------------------

There's an [overall feature overview here](
/docs/Features.md#comparison-with-other-languages-and-use-cases).

Read on for a more detailed look at various parts:


Basic syntax differences
------------------------

Horse64's syntax has the following qualities:

- In overall, a mix of Lua and Go with how it looks like.

- No significant whitespace, indent code however you like.

  (If you really want to, you can even write all in one line:
  ```Horse64
  func main { print("Hello World! Better use line breaks though.") }
  ```
  For obvious reasons, please don't do this however.)

- Curly braces for code blocks, but no line terminator.

- No type annotations, everything pretty simple.

- Generally a minimal but readable look that is less
  technical than e.g. the C/C++ style of JavaScript.


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


Running a program
-----------------

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


Data type differences
---------------------

Most of Horse64's core data types work almost the same as in
Python, JavaScript, or Lua. A quick overview:

- Strings in Horse64 are passed by value and immutable,
  same as also in Python and Javascript and Lua.

- All basic data types are passed by value. Complex
  data types like user type objects ("Class objects" in
  Python and JavaScript), lists ("Arrays" in
  JavaScript) or maps ("Dictionaries" in Python and
  "objects" in JavaScript, "tables" in Lua) are passed
  by reference.

- Similar to Python and JavaScript, Horse64 has
  relatively complex unicode support built into its core.

- Similar to Python, Horse64 has a separate unicode
  string and a bytes data type. Both are immutable and
  passed by value. The unicode string operates on
  unicode code points as units, while a bytes
  string is made up of 8-bit bytes. (Unlike Lua,
  which defaults to byte strings fore verything.)


Object-oriented programming
---------------------------

Similar to Python, Horse64 has relatively high-level
object-oriented programming mechanisms built-in and ready
to go. However, it also offers **traits vaguely
similar to Go.** [Here's an **OOP** introduction](
/docs/OOP.md).


Concurrency and its differences
-------------------------------

You'll notice pretty early that Horse64 often uses so-called
"later functions" that must be called with `later:` or similar.
These are like **async in Python or Javascript** or like
coroutines in Lua. However, in Horse64 they work quite a bit
differently.

Here's a more in-depth comparison of differences:

Here is an **async example in JavaScript**:

```JavaScript
async function my_function() {
    var result = some_func_that_is_async_but_you_wouldnt_see();
    do_something();  // This call runs automatically in parallel with
                     // the above, but you can't easily see that.
    result = await result;  // May cause a time skip if by now, your
                            // earlier async call hasn't completed.
    console.log("Intermediate result: " + result);
    // ...do something further with result here...
}
```

Here is a **later call example in Horse64**:

```Horse64
func my_function {
    var result = some_func_that_is_async()
    later:  # This marker is mandatory and tells you the call above is
            # concurrent, and it marks a clear expected time skip.

    do_something()  # This will actually NOT run in parallel but after
                    # above call fully completed.
    await result  # Make result available and bubble up errors.
                  # This will never cause a delay or time skip.
    print("Intermediate result: " + result.as_str())
    # ...do something further with result here...
}
```

As you can see, in Horse64 the time skips and concurrent calls are,
unlike in many other languages, syntactically obvious and not hidden.
This makes the code flow easy and transparent to the reader.

**If you wanted `do_something()` run in parallel** in Horse64 too:

```Horse64
func my_function {
    var delayed_result, other_result = some_func_that_is_async(),
        do_something()
    later:

    await delayed_result, other_result
}
```

As you can see, Horse64 can run things at the same time just like
Python or JS can, but you'll have to be obvious about it.

[**Continue reading here for more concurrency**](
/docs/Concurrency.md) to see how to use it in practice in Horse64.


Differences of modules and dependencies in Horse64
--------------------------------------------------

- As is common, Horse64 treats one file as one module.

- But Horse64 allows cyclic imports always. E.g in Python that
  isn't always the case.

- Horse64 has its own package manager [horp](
  https://codeberg.org/Horse64/horp.horse64.org).

[See here for **how modules in Horse64 work**](
/docs/Modules, Packages, Imports).


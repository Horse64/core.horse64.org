
<!-- For license of this file, see LICENSE.md in the base folder. -->

Introduction to Horse64 Error Handling
======================================

Horse64 has a runtime error system. A runtime error is an
unexpected event stopping a command you intended, like for
example an I/O error when reading a file or a network error
when downloading a file. Any runtime error occuring will by
default end your program. This is to ensure your program
doesn't mindlessly continue with the wrong assumption some
operation succeeded and break even worse.

Here is how to handle errors gracefully:


Errors and `do ... rescue`
--------------------------

Whenever a runtime error occurs, you may not want your
program to just stop. Instead, you may want to handle it.
**To make an uenxpected error not end your program,
handle that error with a `rescue` clause:**

```Horse64
func main {
    do {
        var f = some_func_causing_io_error()
        print("Everything alright.")
    } rescue IOError as e {
        print("Oops, we had an IOError!")
    }
}
```

With this code, **any IOError caused by
`some_func_causing_io_error` won't just end your program.**

Above code will either print out "Everything alright." or
"Oops we had an IOError!" but never both. This is because
when an error occurs in a called function, like in
`some_func_causing_io_error`, the execution jumps ahead into
your surrounding rescue clause. When there's no error,
the rescue clause will be ignored and skipped.


`finally` clause
----------------

Because errors interrupt your program and may even end it,
in some cases like when reading a file, you may want to
clean up and close a resource safely *both* for
normal operation and in case of an error.

**Handle clean-up safely with a finally clause,**
which contains a code block that always runs after the main
`do` clause block no matter if it ended with an error or not
(unlike a `rescue` clause which only runs for errors):

```Horse64
import io from core.horse64.org

func main {
    # Clunky, but works:
    var f = io.open("some_file.txt", "r") later:

    await f
    do {
        var contents = f.read() later:

        await contents
        print("Read contents: '" + contents)
    } finally {
        f.close()  # Ensure file is closed even in case of errors.
    }
}
```
*(However, above code is a little clunky, [see the
with statement](#with-statement).)*


`with` statement
----------------

There's a catch to [finally](#finally-clause), which is that
it can be tedious to write:

Therefore, **using a `with` statement ensures easy clean-up**
for any resource used inside, by making sure the resource's
`close` attribute is called after the code block has run:

```Horse64
import io from core.horse64.org

func main {
    with io.open("some_file.txt", "r") later as f {
        var contents = f.read() later:

        await contents
        print("Read contents: '" + contents)
    }  # Leaving this, f.close() will be automaticalily called.
}
```
*(Note: the `later` here is only required because `io.open`
is a [later function](/docs/Concurrency.md), and for regular
functions it must be omitted.)*

As you can see, for handling closing resources on both
error and success, `with` produces way less cluttered code than
a `do ... rescue` or `do ... finally` clause.
**With statements are therefore always better style than
finally clauses, in cases where they can be used.**


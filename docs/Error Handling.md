
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
    } rescue IOError {
        print("Oops, we had an IOError")
    }
}
```

With this code, **any IOError, or other error with
an IOError [base type](/docs/OOP.md#base-types), caused by
`some_func_causing_io_error` won't just end your program.**
To know what func can throw which errors, check
its [documentation, like for the standard library](
/docs/FIXME)!

How it works in detail:

Above code will either print out "Everything alright." or
"Oops we had an IOError!" but **never both.** When an error occurs,
the execution jumps ahead into your surrounding rescue clause.
When there's no error, the rescue clause will be ignored and skipped.


Multiple errors in `rescue`
---------------------------

Looking at some funcs like [net.fetch.get_str's documentation](
/docs/FIXME), you'll notice they can throw **multiple different
errors.** You can handle these by listing them
and, if needed, add custom labels like `cerror`, like in
the example below:

```Horse64
import net from core.horse64.org

func main {
    do {
        var f = net.fetch.get_str("https://horse64.org")
        print("Everything alright.")
    } rescue net.ClientError as cerror, net.NetworkIOError {
        print("Oops, we had a network error! Was it our fault?")
        if cerror != none {
            print("Yes, our fault! Maybe this page doesn't exist?")
        } else {
            print("Nope, maybe it was just a connection hiccup.")
        }
    }
}
```
Above, the first listed [error type](#error-types)
with its label that matches will be assigned the error,
with the others set to `none`. An error's type matches
if it's either the exact listed type, **or it has any
[base type](/docs/OOP.md#base-types) matching the listed
type.**

*(Note: `cerror` above is a random name choice, you
can pick any name you like.)*

Want more clearly separate error handling? Then you can also split
it up into multiple clauses (where the first matching one will run):

```Horse64
import net from core.horse64.org

func main {
    do {
        var f = net.fetch.get_str("https://horse64.org")
        print("Everything alright.")
    } rescue net.ClientError as cerror {
        print("Oops, a client error so we must have fetched
            something invalid or forbidden!")
    } rescue net.NetworkIOError {
        print("Oops, some other unspecified network error!")
    }
}
```


Any error in `rescue`
---------------------

**Warning: only use the following if you're sure the code calling you
wouldn't want to know about this error, and you're logging the
error somehow.** (Otherwise this is bad [coding style](
/docs/Coding%20Style.md#what-and-why), hiding possibly important
errors.)

If you want to really catch any type of error, no matter how
unexpected and what type, then use the `any` keyword:

```Horse64
import io as core.horse64.org

func main {
    do {
        var f = net.fetch.get_str("https://horse64.org")
        print("Everything alright.")
    } rescue any {
        print("Something went wrong, we really don't know "
            "what though. (Which is maybe why we shouldn't "
            "indiscriminately catch everythign like this.")
    }
}
```

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
        # (The code in here runs both after successful completion
        #  of the 'do' code block, and after any error aborting it.)
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


Error types
-----------

An error is simply a special custom type that has as [base
type](/docs/OOP.md#base-types) the built-in type `BaseError`,
or any other error type.
You can therefore declare your own error types like this:

```Horse64
import net from core.horse64.org

type MySpecialNetworkSituationError base net.NetworkIOError {
}
```


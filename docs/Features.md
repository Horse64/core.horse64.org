
Features
========

Here's cool stuff Horse64 can do:

Concurrency
-----------

Use effortlessly **concurrent networking** and disk I/O:

```Horse64
import net.fetch from core.horse64.org

func download_my_page {  # This won't block your entire program!
    var main_page = net.fetch.get_str("https://horse64.org")
    later:

    await main_page
    print("Downloaded web page: " + main_page)
}
```

*This helps with designing programs that are scalable and
can handle many remote resources at once without freezing.*

Batteries included
------------------

The standard library offers many features,
like an **`.ini` config parser** or a **JSON parser**:

```Horse64
import confparse from core.horse64.org

func check_config {
    # Read an ini file:
    var contents = confparse.parse_from_file("myconf.ini")
    print(contents["mysection"]["myvalue"])

    # ...or read it from the web?
    var remote_contents = confparse.parse_from_uri(
        "https://example.com/conf.ini"
    ) later:

    await remote_contents
    print("Got remote config!")
}
```

Comparison to Python
--------------------

Horse64 is a dynamically typed, high-level language. Here is
how it compares to the [Python programming language](
https://python.org):

|Horse64|Python|                                                         |
|-------|------|---------------------------------------------------------|
|✓      |✓     | **Dynamically-typed** approachable design.              |
|✓      |✓     | **Large standard library** with high-level features.    |
|✓      |      | **No indent forced,** a clean but flexible syntax.      |
|✓      |      | **AOT-compiled** by developer for great error checks.   |
|✓      |      | **Portable program binaries** as default output.        |
|       |✓     | **Fast launch** of small, not-precompiled scripts.      |
|✓      |      | **No runtime preinstall** needed on user machine.       |
|✓      |✓     | **Bytecode interpreter** handles basic execution.       |
|✓      |      | **Concurrency** of standard I/O and net APIs.           |
|✓      |      | **Static name resolution** to catch typos early.        |


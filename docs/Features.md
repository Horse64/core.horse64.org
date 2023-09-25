
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

This helps with designing programs that are scalable and
can handle many remote resources at once without freezing.

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

Comparison to other languages
-----------------------------

Horse64 is a dynamically typed, high-level language. Here is
how it compares to the other programming languages
[Python](https://python.org),
[JavaScript](https://www.javascript.com/),
[Go](https://go.dev/), and
[C++](https://cplusplus.com/).

|Horse64|Python|JavaScript|Go|C++|                                      |
|-------|------|----------|--|---|--------------------------------------|
|●|●|●| | |**Dynamic types** as a beginner-friendly default.            |
|●|●| |◒| |**Minimal, clean syntax**, no semicolons, clean keywords.    |
|●|●|●|◒| |**High runtime safety** for beginners, not crash-prone.      |
|●|●|◒|●| |**Big standard library** for all developers, no extra setup. |
|●| |●|◒|●|**Line breaks optional** for easier versatile code layout.   |
|●| | |●|●|**Precompiled** always, for great large project error checks.|
|●| | |●|●|**Portable program binaries** as a default output.           |
| |●|●| | |**Instant script use** with fast, non-precompiled launch.    |
|●| | |●|●|**No runtime install** for desktop apps for end users.       |
|●|●|●| | |**Bytecode interpreter** handles basic execution.            |
|●| |◒|●| | **Concurrency** of all the I/O and network default APIs.    |
|●| | |●|●|**Static name resolution** to catch typos early.             |
| | | |●|●|**Outputs machine code** always, for extreme runtime speed.  |

**Disclaimer: this is a subjective list and all facts are subject to
change, no guarantee for accuracy or fitness of this
list for any particular purpose.** If you find a mistake or want to
suggest an improvement, [please file a documentation issue](
https://codeberg.org/Horse64/core.horse64.org/issues/new?template=.gitea%2fISSUE_TEMPLATE%2fdocs.yml
).


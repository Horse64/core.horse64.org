
<!-- For license of this file, see LICENSE.md in the base folder. -->

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


Comparison with other languages and use cases
---------------------------------------------

Horse64 is a dynamically typed, high-level language. Here is
how it compares to the other programming languages
[Python](https://python.org),
[JavaScript](https://www.javascript.com/),
[Go](https://go.dev/), and
[C++](https://cplusplus.com/). *Disclaimer: the
following list is subjective and all languages are subject to
change, **no guarantee provided for accuracy or fitness
for any particular purpose** of this list at all.** 

|Horse64|Python|JavaScript|Go|C++|Feature                             |
|-------|------|----------|--|---|------------------------------------|
|✔|✔|✔| | |**Dynamic types** as a beginner-friendly default.          |
|✔|✔| |✔| |**Minimal, clean syntax**, including no semicolons.        |
|✔|✔|✔| | |**Avoids concurrency crashes** from threading bugs.        |
|✔|✔|〰|✔| |**Big standard library** always, with no extra setup.      |
|✔| |✔|〰|✔|**Line breaks optional** for versatile code layout.        |
|✔| | |✔|✔|**Precompiled** always, for better large project checks.   |
|✔| | |✔|✔|**Portable program binaries** as a default output.         |
|✔| | |✔|✔|**No runtime install** for desktop apps for end users.     |
|✔|✔|✔| | |**Bytecode interpreter** handles basic execution.          |
|✔| |〰|✔| | **Concurrency** of all the I/O and network default APIs.  |
|✔| | |✔|✔|**Static name resolution** to catch typos early.           |
|✔|✔| |✔| |**Official packaging tools** for easy project handling.    |
| | | |✔|✔|**Outputs machine code** always, for extreme speed.        |
| |✔|✔| | |**Instant script use** with fast, non-precompiled launch.  |
| | |✔| | |**Runs in web browser** by default for simple web use.     |

If you find a mistake or want to
suggest an improvement, [please file a documentation issue](
https://codeberg.org/Horse64/core.horse64.org/issues/new?template=.gitea%2fISSUE_TEMPLATE%2fdocs.yml
).


What Horse64 is good at
-----------------------

This is what Horse64 is intended to be suited for:

- Helping beginners and contributors **get started
  🚀 quickly** while still suitable for larger projects.

- Desktop **apps are shipped 📦 mostly self-contained** by default.

- Creation and maintenance of **server backends using the 📶 integrated networking.**

- Concurrency out-of-the-box supports **📱 responsive, non-blocking behavior.**


What Horse64 is bad at
----------------------

This is what Horse64 is likely to be bad at:

- 🚫 Extreme raw speed, since it uses a bytecode VM.

- 🚫 Complex offline code type checking, since it's dynamically typed.
  *(The compiler will however catch more basics beyond many other
  scripting languages.)*

- 🚫 Maximum fast compiler, since that's not a project focus.

- 🚫 Heavily functional programming, since Horse64 is more focused on
  clean in-order imperative code and object-oriented code.


Technical specifications
------------------------

There's also [a more technical summary and specs here](
/docs/Language%20Specs/Overview.md).


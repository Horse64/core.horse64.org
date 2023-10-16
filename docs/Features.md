
<!-- For license of this file, see LICENSE.md in the base folder. -->

Features
========

Here's cool stuff Horse64 can do:


Concurrency
-----------

Use effortlessly **[concurrent](
/docs/Concurrency) networking** and disk I/O:

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

⚠️⚠️⚠️ **Horse64 is currently very unfinished. The following
information is based on the target state of a first release,
and not reflective of the current work in progress version.** ⚠️⚠️⚠️

Horse64 is a dynamically typed, high-level language. Here is
how it compares to the other programming languages
[Python](https://python.org),
[JavaScript (JS)](https://www.javascript.com/),
[Go](https://go.dev/), and
[C++](https://cplusplus.com/). *Disclaimer: the
following lists are subjective and all languages are subject to
change, **no guarantee provided for accuracy or fitness
for any particular purpose** of these lists at all.*

|Horse64|Python|JS|Go|C++|Lua|Syntax and Core Behavior & Code Flow     |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|✔| | |✔|**Dynamic types** as a beginner-friendly default.         |
|✔|✔| |✔| |✔|**Minimal, clean syntax** without line terminators.       |
|✔|✔|✔| | |✔|**Avoids concurrency crashes** from threading bugs.       |
|✔| |✔|〰|✔|✔|**Line breaks optional** for versatile code layout.       |
|✔| |〰|✔| | | **Concurrency** of all the I/O and network default APIs. |
|✔|✔|✔|✔| |✔|**Garbage-Collector** to make avoiding leaks easier.      |
|✔| |〰|✔| | |**1st-class type extending without inheritance.**         |
|✔|✔| | |✔| |**1st-class multiple base types inheritance.**            |
| |✔|✔|✔|✔|✔|**Floating-point decimals** for larger numeric range.     |
| | | | | |✔|**Tail-call optimization** (always used by default).      |
|✔| | | | | |**Fixed-point decimals** as a default number type.        |
| |✔|✔| | |✔|**Dynamic global scope** at runtime, extreme mutability.  |

|Horse64|Python|JS|Go|C++|Lua|Libraries and Desktop App Features       |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|〰|✔|〰| |**Big standard library** always, with no extra setup.     |
|✔| |✔| | | |**Integrated UI and graphics** for easy graphical apps.   |
|✔| | |✔|✔| |**Portable program binaries** as default output.          |
|✔| | |✔|✔| |**No runtime install** for desktop apps for end users.    |
| | |✔| | | |**Runs in web browser** by default for simple web use.    |
| |✔|✔| | |✔|**Easy to embed** for scripting, for only subordinate use.|
|〰|✔|✔| | |✔|**Instant script use** for fast script helper launch.     |

|Horse64|Python|JS|Go|C++|Lua|Tooling and Large Project Handling       |
|-------|------|--|--|---|---|-----------------------------------------|
|✔| | |✔|✔| |**Precompiled** always, for better large project checks.  |
|✔| | |✔|✔| |**Static name resolution** to catch typos early.          |
|✔|✔| |✔| | |**Official packaging tools** for easy project handling.   |

|Horse64|Python|JS|Go|C++|Lua|Organizational Structure, Contributions  |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|〰|✔| |✔|**One central default runtime** for combined efforts.    |
|✔|〰| |✔|✔| |**Default compiler self-hosted**, for easier changes.    |

|Horse64|Python|JS|Go|C++|Lua|Runtime Performance Features             |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|✔| | |✔|**Bytecode interpreter** for high portability.            |
| |〰| |✔|✔| |**Full memory-shared threads** for unlimited parallelism. |
| | |✔|✔|✔| |**Uses JIT** by default for speed, or 100% AOT compiled.  |
| | | |✔|✔| |**Outputs machine code** always, for extreme speed.       |

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

- [Concurrency out-of-the-box](/docs/concurrency) supports
  **📱 responsive, non-blocking behavior.**


What Horse64 is bad at
----------------------

This is what Horse64 is likely to be bad at:

- 🚫 Extreme raw speed, since it uses a bytecode VM.

- 🚫 Complex offline code type checking, since it's dynamically typed.
  *(The compiler still catches more errors than many scripting languages.)*

- 🚫 Maximum fast compiler, since that's not a project focus.

- 🚫 Heavily functional programming, it aims more at OOP and imperative.


Technical specifications
------------------------

There's also [a more technical summary and specs here](
/docs/Language%20Specs/Overview.md).


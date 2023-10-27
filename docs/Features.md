
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

When to use Horse64
-------------------

(This is very subjective.)

- **Approachable but capable.** Clean dynamic types, but more
  AOT error checks than common for dynamic languages.

- **Self-contained.** For deploying server and desktop apps easily.

- **Universal.** General-purpose and multi-paradigm, good OOP support.

- **Backend and cloud-ready.** Concurrent networking by design.

- **Portable tooling.** Package manager included, no giant toolchains.

- **Not flawless:** Horse64 isn't good at 🚫 [extreme raw speed](
  #runtime-performance-and-lowlevel-features),
  🚫 [self-mutating scripting use](#scripting-features),
  and 🚫 limitless offline type checking (since it's
  dynamically typed, so analysis is limited).


Comparison with other languages and use cases
---------------------------------------------

⚠️⚠️⚠️ **Horse64 is currently very unfinished. The following
information is based on the target state of a first release,
and not reflective of the current work in progress version.** ⚠️⚠️⚠️

Horse64 is a dynamically typed, multi-paradigm, high-level language.
Here is how it compares to the other programming languages
[Python](https://python.org),
[JavaScript (JS)](https://www.javascript.com/),
[Go](https://go.dev/), and
[C++](https://cplusplus.com/). *Disclaimer: the
following lists are subjective and all languages are subject to
change, **no guarantee provided for accuracy or fitness
for any particular purpose** of these lists at all.*

If you find a mistake or want to
suggest an improvement, [please file a documentation issue](
https://codeberg.org/Horse64/core.horse64.org/issues/new?template=.gitea%2fISSUE_TEMPLATE%2fdocs.yml
).

### Syntax, Core, and Code Flow Features

|Horse64|Python|JS|Go|C++|Lua|Syntax, Core, and Code Flow              |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|✔| | |✔|**Dynamic types** as a beginner-friendly default.         |
|✔|✔| |✔|✔|✔|**Strongly typed** to avoid silent harmful conversions.   |
|✔|✔| |✔| |✔|**Minimal, clean syntax** without line terminators.       |
|✔|✔|✔| | |✔|**Avoids concurrency crashes** from threading bugs.       |
|✔| |✔|〰|✔|✔|**Line breaks optional** for versatile code layout.       |
|✔| |〰|✔| | |**Concurrency** of all I/O and network default APIs.      |
|✔|✔|✔|✔| |✔|**Garbage-Collector** to make avoiding leaks easier.      |
|✔| |〰|✔| | |**1st-class type extending without inheritance.**         |
|✔|✔| | |✔| |**1st-class multiple base types inheritance.**            |
| |✔|✔|✔|✔|✔|**Floating-point decimals** for larger numeric range.     |
| | | | | |✔|**Tail-call optimization** (always used by default).      |
|✔| | | | | |**Fixed-point decimals** default, for numeric stability.  |
| |✔|✔|❓| |✔|**Ships with dynamic REPL** by default for instant use.  |
| |✔|✔| | |✔|**Dynamic global scope** at runtime, extreme mutability.  |
|✔| | | | |✔|**1-based indexing** to be more beginner-friendly.        |

### Libraries and Desktop App Features

|Horse64|Python|JS|Go|C++|Lua|Libraries and Desktop App Features       |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|〰|✔|〰| |**Big standard library** even without extra setup.        |
|✔| |✔| | | |**UI and graphics integrated** for easy graphical apps.   |
|✔|✔|✔|✔| | |**High-level networking by default** for servers etc.     |
|✔|✔|✔|✔|❓| |**Unicode with full grapheme support** by default.        |

### Deployment Features

|Horse64|Python|JS|Go|C++|Lua|Deployment Features                      |
|-------|------|--|--|---|---|-----------------------------------------|
|✔| | |✔|✔| |**Portable program binaries** as default output.          |
|✔| | |✔|✔| |**Self-contained, no install** needed for end users.      |
|✔|✔| |✔| | |**Official packaging tools** for easy project handling.   |
|✔|✔|✔|❓| |✔|**Compiler trivially usable at runtime**, if needed.      |
|✔| | |❓|❓| |**Easily bake in all binary resources** like images.      |
|✔| | |❓| | |**Virtual archive mounting** for all standard I/O.        |

### Scripting Features

(⚠️ Horse64 is bad for this!)

|Horse64|Python|JS|Go|C++|Lua|Scripting Features                       |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|✔|❓| |✔|**Compiler trivially usable at runtime**, if needed.      |
|〰|✔|✔| | |✔|**Instant script use** for fast script helper launch.     |
| |〰|✔| | |✔|**Easy runtime `eval()`** for trivial script injection.   |
| | |✔| | | |**Runs in web browser** by default for simple web use.    |
| |✔|✔| | |✔|**Easy to embed** for scripting, for subordinate use.     |
| |✔|✔| | |✔|**Easy runtime module loading** for trivial mutability.   |

### Tooling and Large Project Features

|Horse64|Python|JS|Go|C++|Lua|Tooling and Large Project Features       |
|-------|------|--|--|---|---|-----------------------------------------|
|✔| | |✔|✔| |**Precompiled** always, for better large project checks.  |
|✔| | |✔|✔| |**Static name resolution** to catch most typos early.     |
|✔| | |✔|✔| |**Non-trivial optimizations and warnings** by default.    |
| | | |✔|✔| |**Forced type declarations** for most in-advance checks.  |

### Organizational Structure Comparison

|Horse64|Python|JS|Go|C++|Lua|Organizational Structure Comparison      |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|〰|✔| |✔|**One central default runtime** for combined efforts.    |
|✔|〰| |✔|✔| |**Default compiler self-hosted**, for easier changes.    |

### Runtime Performance and Lowlevel Features

(⚠️ Horse64 isn't good at this!)

|Horse64|Python|JS|Go|C++|Lua|Runtime Perfomance and Lowlevel Features |
|-------|------|--|--|---|---|-----------------------------------------|
|✔|✔|✔| | |✔|**Bytecode interpreter** for high portability.            |
|✔| |❓|✔|✔| |**Compiler made for AOT optimizations.**                  |
| |〰| |✔|✔| |**Full memory-shared threads** for extra flexibity.      |
| | |✔|✔|✔| |**Always uses JIT** for speed, or 100% AOT compiled.      |
| | | |✔|✔| |**Outputs machine code** always, for extreme speed.       |
| | | | |✔| |**Inline assembly and manual allocation** easy to do.     |


Technical specifications
------------------------

There's also [a more technical summary and specs here](
/docs/Language%20Specs/Overview.md).


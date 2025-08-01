
<!-- For license of this file, see LICENSE.md in the base dir. -->

Resources
=========

This section has various external resources useful when using the
[Horse64 programming language](https://horse64.org). This
includes the code location for all the core tooling, where
to report bugs, etc.


SDK
---

If you want to get started, [**go here for
the SDK** (Software Development Kit) for Horse64 and
Moose64](https://horse64.org/get).


Report bugs
-----------

Before you report a bug, you might want to check the
[standard library reference documentation](
./docs/FIXME)
and the [💬 community chat](https://horse64.org/chat)
to verify if what you found is truly a bug or rather
a misunderstanding.

To report bugs, here are the locations for core components:

- [Compiler bug reports (this includes both Horse64's horsec
  and Moose64's moosec)](
  https://codeberg.org/Horse64/core.horse64.org/issues).

- [Standard library bug reports for Horse64 (behavior
  of built-in libraries like opening files, etc.)](
  https://codeberg.org/Horse64/core.horse64.org/issues).

- [Standard library bug reports for Moose64](
  https://codeberg.org/Moose64/m64.horse64.org/issues
  ).

- ["Horp" package manager bug reports](
  https://codeberg.org/Horse64/horp.horse64.org/issues).

- [HVM (Horse64's runtime) bug reports](
  https://codeberg.org/Horse64/hvm.horse64.org/issues).

- [Syntax highlighting and other extra developer
  libraries bug reports](
  https://codeberg.org/Horse64/devtools.horse64.org/issues).

If you are unsure where to file a bug, **simply guess**,
the maintainers will move it around if needed.


Documentation
-------------

If you're reading this, you found the documentation! If you got
some offline copy, you can find [the latest online copy of the
**Horse64** documentation here](https://horse64.org/docs/Welcome).
There is also [the online copy of the **Moose64**
documentation](https://m64.horse64.org/docs/Introduction).

If you want to contribute to and change the docs, go look here:

- Find the [🧬 documentation code files for Horse64 here](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/src).

- Find the [🧬 documentation code for Moose64 here](
  https://codeberg.org/Moose64/m64.horse64.org/src/branch/main/src).


License
-------

The core projects are **dual-licensed under either a
BSD-style license or the Apache 2 license,** with the minor
exception to that being the official artwork images. **Read
the respective license files** for details, the licenses
of the core projects are almost the same.

- Here's [the **core.horse64.org license** as an example](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/LICENSE.md).

- Read about the [**Developer Certificate of Origin** here](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/LICENSE.md#contributions).

  Please note **we cannot accept any code that used AI-based
  code generation or code completion, like "Co-Pilot" etc.,**
  [see details here](
  /docs/How%20to%20Contribute.md#why-ai-contributions-are-not-allowed).

- For the respective other projects, check the
  `LICENSE.md` file for each. It's part of each
  project's code. **E.g. here's [horp's code](
  #horp).**

- For seeing all dependencies, `horp license .` can help you.

  Example to check what the SDK includes:

  1. [Download and extract the SDK source code](
     https://codeberg.org/Horse64/helpers-for-sdk-download.horse64.org/archive/main.zip).

  2. Make sure [**horp**](#horp) is available on your system.

  3. Open a terminal, go into the extracted code folder, and run:

     ```bash
     horp license .
     ```


Standard library
----------------

The standard library provides all the built-in functionality
like opening files, parsing basic formats like JSON, and
basic text formatting and so son.

### Horse64 standard library

For Horse64, the standard library is in the `core.horse64.org`
package which is the same repository that also contains
[horsec](#Horsec).

- Get the standard library by fetching the [**SDK**](#sdk).

- Find the [🧬 standard library code for Horse64 here](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/src).

### Moose64 standard library

For Moose64, the standard library is in the `m64.horse64.org`
package.

- Find the [🧬 standard library code for Moose64 here](
  https://codeberg.org/Moose64/m64.horse64.org/src/branch/main/src).


Horp
----

This is the **Hor**se **p**ackage manager.

- Get horp by fetching the [**SDK**](#sdk).

- [Find the 🧬 horp code here](
  https://codeberg.org/Horse64/horp.horse64.org/).


Horsec
------

The official compiler for Horse64 code is a binary called `horsec`.
It's written primarily in Horse64.

- [The compilation section describes some details on horsec](
  /docs/Compilation.md).

- Get it by fetching the **SDK**.

- Find [🧬 horsec's code here](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/src/compiler/)
  along with the other parts of the standard library.


Moose64
-------

Moose64 is a sibling language developed together with Horse64,
particularly useful for handling C integration and low level code.

- Check out the [Moose64 website](https://m64.horse64.org).

- Here's the [Moose64 standard library](
  https://codeberg.org/Moose64/m64.horse64.org).


Moosec
------

The official compiler for [Moose64](#moose64) code is a binary called
`moosec`. It's actually just a slightly different build of
[horsec](#horsec), they share the same code base.


HVM
---

HVM, the "Horse Virtual Machine", provides the
runtime powering Horse64 programs.
HVM is primarily written in [Moose64](#moose64) and
using some [C](
https://en.wikipedia.org/wiki/C_(programming_language)
libarries.

- Get it by fetching the **SDK**.

- Find the [🧬 HVM source code here](
  https://codeberg.org/Horse64/hvm.horse64.org/src/branch/main/src/
  ).

- Read here about [advanced technical runtime concerns](
  /docs/Runtime%20Concerns.md).


Spew3D
------

**Spew3D** is the base library used for accessing operating system
facilities, multimedia, and other base functionality, used
by [HVM](#hvm). [🧬 Find its code here](
https://codeberg.org/Spew3D/Spew3D).
While it can be used separately for any [C program](
https://en.wikipedia.org/wiki/C_%28programming_language%29),
it's maintained as part of the Horse64 project.


Contributing
------------

For info on how to contribute, [read here](
/docs/How%20to%20Contribute.md).


Creators
--------

For a full list of who worked on and created Horse64,
check the **contributors for the central packages:**

- [Core tools and stdlib authors (includes both horsec and
  moosec)](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/AUTHORS.md),
- [Byte code VM authors](
  https://codeberg.org/Horse64/hvm.horse64.org/src/branch/main/AUTHORS.md),
- [Package manager authors](
  https://codeberg.org/Horse64/horp.horse64.org/src/branch/main/AUTHORS.md),
- [Runtime base library (Spew3D) authors](
  https://codeberg.org/Spew3D/Spew3D/src/branch/main/AUTHORS.md).

And for Moose64 specifically:

- [Moose64 stdlib authors](
  https://codeberg.org/Moose64/m64.horse64.org/src/branch/main/AUTHORS.md).


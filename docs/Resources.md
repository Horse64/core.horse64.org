
<!-- For license of this file, see LICENSE.md in the base folder. -->

Resources
=========

This section has various external resources useful when using the
[Horse64 programming language](https://horse64.org). This
includes the code location for all the core tooling, where
to report bugs, etc.


SDK
---

If you want to get started, [**go here for
the SDK** (Software Development Kit) for Horse64](
https://horse64.org/download
).


Report bugs
-----------

Before you report a bug, you might want to check the
[standard library reference documentation](
./docs/FIXME)
and the [💬 community chat](https://horse64.org/chat)
to verify if what you found is truly a bug or rather
a misunderstanding.

To report bugs, here are the locations for core components:

- [Compiler bug reports](
  https://codeberg.org/Horse64/core.horse64.org/issues).

- [Standard library bug reports](
  https://codeberg.org/Horse64/core.horse64.org/issues).

- [Horp (package manager) bug reports](
  https://codeberg.org/Horse64/horp.horse64.org/issues).

- [HVM (C runtime) bug reports](
  https://codeberg.org/Horse64/hvm.horse64.org/issues).


Documentation
-------------

If you're reading this, you found the documentation! If you got
some offline copy, [switch to the latest online copy of the
documentation](https://horse64.org/docs/Welcome).


License
-------

**The license files for all core projects are almost the
same,** but feel free to check the license for each one
yourself.

**LICENSING:** All projects are dual-licensed under either a
BSD-style license or the Apache 2 license, with minor
exceptions (like the official artwork). **Check the
respective license files for details:**

- Here's [the `LICENSE.md` file for the core.horse64.org
  package.](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/LICENSE.md)

- For the respective other projects, **check the
  `LICENSE.md` file for each.** It's part of each
  project's code. **E.g. here's [horp's code](
  #horp).**


Standard library
----------------

The standard library providing all the built-in functionality in
the `core.horse64.org` can be found in the same location as
[horsec](#Horsec).

- Get it by fetching the **SDK**.

- Find the [🧬 standard library code here](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/src).


Horp
----

This is the **Hor**se **p**ackage manager.

- Get horp by fetching the **SDK**.

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


HVM
---

HVM, the "Horse Virtual Machine", provides the
runtime powering Horse64 programs.
HVM is primarily written in [C](
https://en.wikipedia.org/wiki/C_%28programming_language%29).

- Get it by fetching the **SDK**.

- Find the [🧬 HVM source code here](
  https://codeberg.org/Horse64/hvm.horse64.org/src/branch/main/src/
  ).

- Read here on [advanced technical runtime concerns](
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


Creators
--------

For a full list of who worked on and created Horse64,
check the **contributors for the central packages:**

- [Core tools and stdlib authors](
  https://codeberg.org/Horse64/core.horse64.org/src/branch/main/AUTHORS.md),
- [Byte code VM authors](
  https://codeberg.org/Horse64/hvm.horse64.org/src/branch/main/AUTHORS.md),
- [Package manager authors](
  https://codeberg.org/Horse64/horp.horse64.org/src/branch/main/AUTHORS.md),
- [Runtime base library authors](
  https://codeberg.org/Spew3D/Spew3D/src/branch/main/AUTHORS.md).


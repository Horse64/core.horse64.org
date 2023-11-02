
<!-- For license of this file, see LICENSE.md in the base folder. -->

Runtime Concerns
================

Get the Horse64 runtime as part of the [SDK](
/docs/Resources.md#sdk). This document talks about
technical detail concerns regarding the runtime and
underlying implementations.


How code reaches the runtime
----------------------------

Check [the compilation section](/docs/Compilation.md)


Garbage collection
------------------

To make Horse64 powerful to use while still efficient for the
programmer, it helps you out with automatic memory management
using an approach *Garbage Collection*. This is implemented
in [HVM](/docs/Resources.md#hvm).

Generally, [data types](/docs/Language%20Specs/Data%20Types.md) that
allow referencing to other values that may reference back in cycles
need more complex cleanup. Therefore, they cause so-called
*GC load* when created. Items that can't produce complex cyclic
references are cheaper to handle (in terms of computation time)
and therefore may make your code faster if used instead.


Multimedia, filesystem access, and else
---------------------------------------

For a lot of its base functionality HVM, and therefore by
extension Horse64 programs, use [Spew3D](/docs/Resources.md#spew3d).


Platforms
---------

Horse64 should be portable to almost all Unix-like platforms
with some effort, at least for headless apps, for all gcc or
clang style compilers. For graphical apps, it's mostly bound
to [SDL2](https://libsdl.org/)'s platform support. Here's
the current state on platform support:

| Platform support           |Rating| Details                     |
|----------------------------|------|-----------------------------|
| Windows x64                |★★★   | Official build.             |
| Linux x64 glibc            |★★★   | Official build.             |
| Linux ARM64 glibc          |★★★   | Official build.             |
| Any Linux (MIPS, musl, ...)|★★    | Works, if **SDL2** does.    |
| Windows x86                |★★    | Works on Vista or newer.    |
| macOS ARM64                |★     | Might work, patches welcome.|
| Generic Unix, BSD          |★     | Might work, patches welcome.|
| Android ARM64              |      | Tons of work needed first.  |
| iOS ARM64                  |      | Tons of work needed first.  |

### Platform names used by Horse64 tooling

| Platform             |`system.osname`| Build platform name  |
|----------------------|---------------|----------------------|
| Windows x64          |`"windows"`    | windows-x64-mingw    |
| Linux x64 glibc      |`"linux"`      | linux-x64-glibc      |
| Linux ARM64 glibc    |`"linux"`      | linux-arm64-glibc    |
| Linux x64, other libc|`"linux"`      | linux-x64-other      |
| FreeBSD x64          |`"freebsd"`    | freebsd-x64-default  |
| macOS ARM64          |`"macos"`      | macos-arm64-default  |
| Android ARM64        |`"android"`    | android-arm64-bionic |



<!-- For license of this file, see LICENSE.md in the base dir. -->

Runtime Concerns
================

Get the Horse64 runtime as part of the [SDK](
/docs/Resources.md#sdk). This document talks about
technical detail concerns regarding the runtime and
underlying implementations.


What is the runtime
-------------------

Horse64 has its own untime based on [HVM](/docs/Resources.md#hvm)
which is meant to be independent in a way that it should run
out-of-the-box on most systems without prior install.
Other than [C](
https://en.wikipedia.org/wiki/C_(programming_language) for
building it, it doesn't depend on other pre-existing languages.


How code reaches the runtime
----------------------------

Check [the compilation section](/docs/Compilation.md).


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


VM worker threads
-----------------

[HVM](/docs/Resources.md#Hvm) can run multiple concurrent executions
at the same time, as long as any are [scheduled in parallel](
/docs/Concurrency.md#running-code-in-parallel).
HVM uses a pool of multiple worker threads using
hardware threading to run with true parallelism. The amount
of workers depends on the detected amount of CPU cores, but
a minimum of two threads is used.


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
| Windows x86                |★★    | Should work, Vista or newer.|
| macOS ARM64                |★     | Might require minor patches.|
| Generic Unix, BSD          |★     | Might require minor patches.|
| Android ARM64              |      | Tons of work needed first.  |
| iOS ARM64                  |      | Tons of work needed first.  |

### Platform names used by Horse64 tooling

| Platform             |`system.osname`| Build platform name  |
|----------------------|---------------|----------------------|
| Windows x64          |`"windows"`    | windows-x64-mingw    |
| Linux x64 glibc      |`"linux"`      | linux-x64-glibc      |
| Linux ARM64 glibc    |`"linux"`      | linux-arm64-glibc    |
| Linux x64, other libc|`"linux"`      | linux-x64-other      |
| Windows x86          |`"windows"`    | windows-x86-mingw    |
| FreeBSD x64          |`"freebsd"`    | freebsd-x64-default  |
| macOS ARM64          |`"macos"`      | macos-arm64-default  |
| Android ARM64        |`"android"`    | android-arm64-bionic |


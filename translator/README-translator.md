
Python Translator Manual
========================

This is a brief manual for `translator/translator.py`, the 
Horse64-to-Python translator used to bootstrap `horsec`,
the official compiler.


Dependencies To Run Translator
------------------------------

The following dependencies are needed to run the translator and the
basic test suite:

- Your host should be Linux or Unix, even for bootstrapping
  the Windows compiler. Use a Linux VM or WSL on Windows.

- Python 3.8+

- Bash shell, GNU Make, Git, gcc, Python development headers

- `Cython`, `requests`, `pywildcard` packages (from PyPI)

The following is additionally needed to bootstrap from scratch:

- Git, GNU make, [all build dependencies of HVM](#FIXME)


How to run it
-------------

You probably just want to check it with `make test`.

After that, you might want to bootstrap. To do that,
go through the following steps:

1. Run in this `translator` folder (not the repository root):

   `make get-deps`

2. You should now have a sub-repository of HVM inside
   `horse_modules/hvm.horse64.org` (path relative to the repository
   root!).

   **Ensure this is the HVM version you want. You can move
   to a different commit, or replace this entire sub-repository
   folder with a fork.**

3. Either build HVM in that sub-repository manually for full control,
   or otherwise you can now bootstrap right away:

   `make bootstrap` (Run this here inside the `translator` folder!)

   This command will attempt to build HVM automatically for you if
   needed. However, you might need to read HVM's build instructions
   and to it yourself if it fails.


Shortcomings of Translator
--------------------------

The translator is meant for bootstrap, not for everyday use.
Here are some of its biggest shortcomings:

- Almost no error checking. Will happily run blatantly wrong code.

- Needs strict indents, 4 spaces, max. one statement per line, etc.

- Lacks lots of the standard lib, like audio, graphics, and UI.

- Many concurrency corner cases are straight up broken. It really
  can't run your every day programs properly.


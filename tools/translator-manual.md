Python Translator Manual
========================

This is a brief manual for `tools/translator.py`, the Horse64-to Python
translator used to bootstrap `horsec`, the official compiler.

Dependencies To Run Translator
------------------------------

The following dependencies are needed to run the translator and the
basic test suite:

- Your host should be Linux or Unix, even for bootstrapping
  the Windows compiler. Use a Linux VM or WSL on Windows.

- Python 3.8+

- Bash shell

- `requests`, `pywildcard` packages (from PyPI)

The following is additionally needed to bootstrap from scratch:

- Git, GNU make, [all build dependencies of HVM](#FIXME)

Shortcomings of Translator
--------------------------

The translator is meant for bootstrap, not for everyday use.
Here are some of its biggest shortcomings:

- Almost no error checking. Will happily run blatantly wrong code.

- Needs strict indents, 4 spaces, max. one statement per line, etc.

- Lacks lots of the standard lib, like audio, graphics, and UI.

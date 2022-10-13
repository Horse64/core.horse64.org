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

- Git, GNU make, [all the build dependencies of HVM](#FIXME)


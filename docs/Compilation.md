
<!-- For license of this file, see LICENSE.md in the base folder. -->

Compilation
===========

A program's code is written in an `.h64` text file, then translated
by [horsec](/docs/Resources.md#horsec) to bytecode combined with
[HVM](/docs/Resources.md#hvm) in various [stages](#stages).
The result is a mostly standalone executable.

Other tooling like [horp](/docs/Resources.md#horp) helps
with project management.


Stages
------

These are the current compilation stages of horsec as of 2023-11-02:

1. `--stage token` does tokenization.

2. `--stage ast` applies the AST parser for a syntax tree and computes
   a global scope, which can be output with `--stage global-scope` if
   desired.

3. `--stage checked-ast` processes all imports and applies the previous
   stages to them as well, and then does full project-wide symbol
   resolution.

4. `--stage transformed-code` takes the fully symbol resolved code and
   applies all concurrency transforms and the part of the optimizations
   that happen still on the AST tree level. You can alternatively
   output the corresponding AST via `--stage corresponding-ast` if
   desired.

5. `--stage bytecode` will take the fully resolved and transformed
   AST and generate the resulting bytecode.

6. (Maybe upcoming at some point, another optimization stage on the
   bytecode level.)


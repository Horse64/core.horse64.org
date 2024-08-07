
<!-- For license of this file, see LICENSE.md in the base dir. -->

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

These are the current compilation stages of horsec as of 2024-06-08:

1. `--stage token` does tokenization.

2. `--stage ast` applies the AST parser for a syntax tree and computes
   a global scope, which can be output with `--stage global-scope` if
   desired.

3. `--stage checked-ast` processes all imports and applies the previous
   stages to them as well, and then does full project-wide symbol
   resolution to verify all symbol references.

4. `--stage transformed-code` takes the fully checked code and
   applies all concurrency transforms and the part of the optimizations
   that happen still on the AST tree level. You can alternatively
   output the corresponding AST via `--stage transformed-ast` if
   desired.

5. `--stage bytecode` will take the fully resolved and transformed
   AST and generate the resulting bytecode.

   *(Upcoming maybe at some point, more optimizations here.)*

6. `--stage binary` will write out the bytecode binary representation
   attached to a VM binary.




<!-- For license of this file, see LICENSE.md in the base folder. -->

Coding style
============

This document explains [what a coding style is](#what-and-why),
and what common style is recommended for use in Horse64.
**Much of this is subjective,** but sticking with some
shared rules can make it much easier for other contributors
to jump in.


What and Why
------------

A **coding style** simply describes how your code is layed out
and organized *beyond the pure functionality*. For example,
how you name your variables doesn't make the code run
differently, but it affects how other people can read your code.

Even if you're working on a project alone, you should try
to keep the code readable, because if you work on it for longer
you'll forget what each piece was meant to do. **Clear naming
and code layout can help grasping a code's intended purpose.**

As a beginner you might find this irrelevant, which is fair.
The larger and more advanced your code, the more relevant style is.


Recommended style for Horse64
-----------------------------

The following common style guideline is recommended for
Horse64 code:

- Indent code blocks inside `{ ... }` by 4 spaces,
  and keep the opening brackets on the same line.
  ```Horse64
  func main {  # Opening bracket on same line!
      print("Hello!")  # Indented by 4 spaces.
  }
  ```

- Use lower-case names with underscore separation for
  variables, functions, and modules.
  ```Horse64
  var my_variable = 64
  ```

- Use mixed case names with no word separation for types.
  ```Horse64
  type MyReusableType {
  }
  ```


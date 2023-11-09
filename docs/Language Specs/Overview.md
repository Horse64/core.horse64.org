
<!-- For license of this file, see LICENSE.md in the base folder. -->

Overview on Horse64
===================


What is Horse64
---------------

*(This is a technical in-depth look,
[go here for easy to grasp features](/docs/Features.md),
or check out the [tutorials section for easy introductions
and overviews](/docs/Tutorials/Start)).*

Horse64 is on the technical side a [dynamically but
strongly typed](
https://medium.com/android-news/magic-lies-here-statically-typed-vs-dynamically-typed-languages-d151c7f95e2b), object-oriented and imperative, bytecode executed,
partially ahead-of-time
[compiled (with horsec)](/docs/Resources#horsec) language.

- Check the [formal grammar](/docs/Language%20Specs/Grammar.md)
  of Horse64.

- Check the [data types](/docs/Language%20Specs/Data%20Types.md),
  includes Garbage Collection and runtime performance behavior.

- Check below for [object-oriented programming in
  Horse64](#oop-in-horse64-by-using-type).

- Check [the formal concurrency rules here](
  /docs/Language%20Specs/Concurrency%20Model.md),
  or read [an introduction on concurrency](/docs/Concurrency.md).

- Check also [the advanced concepts making up Horse64](
  /docs/Tutorials/Start#advanced-concepts) beyond just the
  core specifications.


Design Goals
------------

Major design goals of Horse64 are:

- Approachability and productivity for beginners,
  without sacrificing big project suitability.

- Clean and minimal, as much as possible
  without sacrificing big project suitability.

- Base tooling and resulting programs should be portable,
  and easy to install and expand.

  *(This is why the [compiler](/docs/Resources.md#horsec) is
  custom and self-hosted, without LLVM or bison or other similar
  external tooling.)*

- Desktop app and server app creation should be easy.


OOP in Horse64 by using `type`
------------------------------

The `type` keyword allows declaring the use of a so-called *custom
type*. A custom type can be used for object-oriented programming
(OOP).
Any *object instance*, or *object* in short, will have the
*attributes* specified on the type, which can be variables or funcs.

A custom type can either be `base`d on another one to form
a subtype which inherits all attributes and can add more.
[See here for a friendly introduction to base types](
/docs/OOP.md#base-types) Or it can be `extend`ed by
another module to add more shared attributes to all
its instances.

**The following rules apply to custom types:**

- `typename(...)` on any custom type object returns
  `"object"`.

- For any type with a `base` type, you can override any
  `func` attributes of the base type by just declaring
  them again on your new type. However, you can never
  override `var` attributes.

- If your type has multiple `base` types that all
  provide a `func` attribute with the same name,
  the type listed first in your `base` type list
  will always be the one the attribute called is
  picked from.

- Using `base.some_func()` will call the overridden
  func attribute in your overriding function. If multiple
  base types had that function, it will call the one
  first in your `base` type list.

- If any attribute name begins with an underscore,
  it can only be accessed from inside any func attribute
  via `self`, not from the outside.

- If any var attribute is declared using `protect`,
  it can be accessed read-only from the outside but
  it can only be changed inside the type's func attributes.


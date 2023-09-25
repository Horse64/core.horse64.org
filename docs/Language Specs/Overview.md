
Overview over Horse64
=====================

What is Horse64
---------------

*(This is a technical in-depth look,
[go here for easy to grap features](/docs/Features.md)).*

Horse64 is on the technical side a [dynamically but
strongly typed](
https://medium.com/android-news/magic-lies-here-statically-typed-vs-dynamically-typed-languages-d151c7f95e2b), object-oriented and imperative, bytecode executed,
partially ahead-of-time
[compiled (with horsec)](/docs/Resources#horsec) language.

- Check the [formal grammar](/docs/Language Specs/Grammar.md) of Horse64.

- Check the [data types](/docs/Data Types.md), includes
  Garbage Collection and runtime performance behavior.

- Check below for [object-oriented programming in
  Horse64](#oop-in-horse64-using-type).

- 

OOP in Horse64 by using `type`
------------------------------

The `type` keyword allows declaring the use of a so-called *custom
type*. A custom type can be used for object-oriented programming.

Here is an example, where you can see `type` being used to specify
a reusable concept of a "car", and then it can be used to create
multiple actual *instances*:

```Horse64
type Car {
    var speed = 90
    var color = "green"
}

func main {
    var my_car = new Car()
}
```

A custom type has so-called *attributes*, in above example `speed`
and `color`. These are stored separately for every single
created instance and can be modified separately for each.

A custom type can also have `func` attributes that access the
current instance they're called on via `self`:

```Horse64
func Car.speed_up {
    self.speed *= 1.5
}
```



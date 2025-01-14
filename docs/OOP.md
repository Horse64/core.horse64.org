
<!-- For license of this file, see LICENSE.md in the base dir. -->

Object-oriented programming in Horse64
======================================

**Note:** If you're new to programming, you might
want to read [this basic example first](
/docs/Tutorial/Syntax.md#types
).

Programming with so-called *object types* in Horse64
can be useful for organizing your code.
But initially, the following may seem convoluted:
**You'll only find this essential to use in
larger programs.** (But it's not considered bad [coding style
](/docs/Coding%20Style.md#what-and-why) to use it in
small ones either.)


Custom `types` in Horse64
-------------------------

You can declare a so-called `type`, a custom type, in your Horse64
programs. Think of it like a blueprint for a reusable object,
which always will have some listed attributes like values,
like for example the blueprint for a car:

```Horse64 
type Car {
    var speed = 90
    var color = "green"
}

func main {
    var my_car = new Car()
    var my_other_car = new Car()
    my_car.speed = 80

    print("My car has now a speed of: " +
        my_car.speed.as_str())  # Outputs speed 80!
    print("However, my other car is a separate object
        and therefore still has a speed of: " +
        my_other_car.speed.as_str())  # Outputs 90!
} 
```

You can also put functions on all your objects by
using the `func` keyword to make func attributes:

```Horse64 
type Car {
    var speed = 90
    var color = "green"
}

func Car.honk {
    print("HONK! HONK!")
}

func main {
    var my_car = new Car()
    my_car.honk()  # Make it honk!
}
```

Any such func attribute can access its current object's
var attributes and their values via the `self` keyword:

```Horse64   
type Car {
    var speed = 90
    var color = "green"
}

func Car.increase_speed {
    self.speed += 10
}
```

This allows you to craft easily reusable, complex objects
with their own neatly contained data and behavior.
**Types do nothing you couldn't also do with just using
basic functions, it simply is there to help you organize
your code!**


Base types
----------

If you need a new `type` for new variants of objects
that reuses behavior of an already existing type,
you can `base` it on an existing type:

```Horse64         
type Vehicle {
    var speed = 90
    var color = "green"
}

func Vehicle.increase_speed {
    self.speed += 10
}

type Truck base Vehicle {
    var cargoload = 0
}

func main {
    var my_truck = new Truck()
    print("This truck also has a speed,
        since it's based on a generic Vehicle: " +
        my_truck.speed.as_str())
}
```

You can also base it on a type [imported from another
module](/docs/Modules, Packages, Imports):

```Horse64
import my_other_module

type MySpecialType base my_other_module.BaseType {
    var new_value
}
```


Extend things
-------------

**(⚠️ Warning, this is very advanced functionality for
large projects. If this sounds strange to you,
just don't use it and make [new types based on others
instead](#base-types).)**

### `extend type`

You can split up a very complex type across multiple
modules, by declaring it and some of its attributes in one
module, but then extending it with more attributes in the
other module:

```Horse64
# (Assume this file is module_a.h64)

type MyType {
    var value1 = 5
}
```

```Horse64
# (Assume this file is module_b.h64)

import module_a

extend type module_a.MyType {
    var value2 = 6
}
```

The difference to [basing a new type on an existing
type](#base-types) is that instead of having your own
specialized variant for just your own uses, it allows
expanding types for already pre-existing code using them.

### `extend enum`

Similarly, you can use `extend enum` to add new enum
entries. Any extended enum entries without an explicit
numbering may have any arbitrary number, there's no longer
any guarantee of them maintaining a specific order.

### `extend func`

Similarly, you can also use `extend func` to extent
functions:

```
extend func some_other_module.some_existing_func(
        added_new_parameter=5
        ) {
    var inner_result = extended(original_parameter1,
        original_parameter2)

    // Do something additional here that you wish
    // to do, somehow relating to your new parameter.

    return inner_result
}
```

Conceptually, you're replacing the original function
with your wrapped one that gets all the original parameters
plus some additional ones, then calls the original
now-extended function via `extended(...)` somewhere.

Please note:

- Extending funcs is a powerful tool for plugins
  and other third-party added functionality **that
  should be used sparingly. Of all extend variants,
  it will impact readability the most.**

- Multiple `extend func`s targeting the same function
  will be applied in arbitrary order.

- Only **optional keyword parameters** can be added when
  extending a function. Positional parameters can't be
  added.

- The original function parameters
  **still exist, even though your `extend func` statement
  doesn't list them.** They **keep their original names**
  as in the original function definition.

- Any parameters that the original
  function should get, **including its original ones**,
  you must **pass through to the `extended()` call.**


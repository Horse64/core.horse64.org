
<!-- For license of this file, see LICENSE.md in the base folder. -->

Object-oriented programming in Horse64
======================================

Programming with so-called *object types* in Horse64
can be useful for organizing your code.
But initially, the following may seem convoluted:
**You'll only find this essential to use in
larger programs.** (But it's not bad [coding style
](/docs/Coding%20Style.md#what-and-why) to use it in
small ones.)


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

It's possible to base your new type on multiple others in
which case it inherits all their attributes, by listing
them after the `base` keyword separated by commas:

```Horse64
type MySpecialBehavior base FunnyBehavior, Strangebehavior {
    var new_value
}
```


Extend types
------------

**(⚠️ Warning, this is very advanced functionality for
large projects. If this sounds strange to you,
just don't use it.)**

You can also split up a very complex type across multiple
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

extend module_a.MyType {
    var value2 = 6
}
```


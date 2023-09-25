
Overview over Horse64
=====================

Custom types with `type`
------------------------

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
 


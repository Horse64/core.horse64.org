
<!-- For license of this file, see LICENSE.md in the base dir. -->

Syntax Basics
=============

**Warning:** While this tutorial is meant for complete beginners
new for programming, please note programming can be **difficult**
and seem arcane at first. Make sure to have the Horse64 code
editor running to try things right away, and to experiment a lot
so you can get a practical intuition for what you're doing.

Code for Horse64 is stored in `.h64` text files. These are files
holding for instructions to run that make up your programs.
When such a program runs, the instructions are executed,
making up the behavior of your program.

Continue reading for an explanation of how to write a program.
How a program is laid out in code is commonly called the
"syntax" of the program. This syntax will be explained here.


Functions
---------

Most code in a Horse64 program needs to be inside
so-called functions, outside of rare exceptions.
A basic program with a single function looks like this:

```Horse64
func main {
    print("Hello World!")
}
```
*(Store this in a file named "test.h64" to run it later.)*

If you run this, it will output "Hello World!" and exit.

### What is a function?

It's simply a way to group
a set of instructions together. You can write your entire
program in just one function, like the small program above,
or use additional functions for different tasks with
memorable names that you like.

To prevent programs
from becoming too unorderly once they become large,
Horse64 requires that you organize your code in functions.

### How do I test this function?

To test it, make a new "test.h64" file with above code and
press the "Run" button in your Horse64 code editor,
or use this on the command line:

```bash
horserun ./test.h64
```

If it doesn't work, ensure the exact file contents are as follows:
```Horse64
func main {
    print("Hello World!")
}
```

### How do I use functions?

You declare new functions by using a `func` statement
like above, after which you then put some name, like
"main" in this case. The "main" function is started by
default when your program launches, but you can use any
additional functions with other names:

```
func main {
    print("Hello World!")
}
func my_other_func {
    print("This outputs something else!")
}
```

### What exactly are those weird `{` brackets?

The `{` and `}` braces, that follow your `func` statement
header with the func name you picked, simply mark the start
and end of all the step-by-step statements for the program
to run whenever this function is invoked.

To test it, press the "Run" button in your Horse64 code editor,
or use this on the command line:
```Horse64
horserun ./test.h64
```


Calls
-----

A call is for example this line of code from the above program:

```Horse64
   print("Hello World!")
```

### What is a call?

A call will tell another function to run, in this case the built-in
function "print", called from your "main" user-defined function.
This allows you to make use of code found in other functions.

### How do I make a call?

To make a call, simply put the name of the target function, in
this case "print", followed by a `(` parenthesis, followed by
the parameters the function expects, followed by `)` to end the
call expression. A call means the called function, in this case
"print", will be executed immediately in place of your call, which
allows you to chain functions together.

### What are function parameters?

The parameters for a func are a fixed set of named values,
also called variables, that it expects you to provide to do
something with them. Your "main" function has no parameters,
and the "print" function is usually called with a single
parameter for the item to be printed.

To find out what variables are, continue reading.

Variables
---------

You can define a variable with any given name like this:
```
var my_variable
```
You can then assign it a value like this inside any of
your funcs, and reuse it later:

```
var my_variable

func main {
    my_variable = 5
    print(my_variable)
}
```

The above example will print the number `5`.

### What are variables?

Variables are simply named placeholders that can hold a
variable value that you can set and change at any point
in your program. This can be used to remember a number or
text or something else that needs to be reused later in
your program. If you want your program to ask the user
to input any text while it runs, this will also be commonly
held in such a variable.

### How do I use variables?

You declare them as above with a name of your choice.
Then you can reference them by that name, for example
to use them as parameters for calls, or to change their
value. To change the value of a variable, use `=` to
specify the new value on the right-hand side:

```
my_variable = "this text will now be stored inside the variable"
```

As you can see, a value can be a number, a text put
inside quotes, and many other value types that you
will learn about later. One value type is a
so-called object, see the section on [#types](types).


Types
-----

To combine a set of data commonly associated with one complex
object into a reusable class type, use the `type` statement:

```
type Bicycle {
    var wheel_size = 0.5
    var weight = 2.0
}

func main {
    var my_bicycle = new Bicycle()
    print(my_bicycle.weight)
}
```

The variable with name "my_bicycle" is set to contain an object of
the so-called user type named "Bicycle" in above example. This
can now be seen as a concrete instance with the data you need
for your program's idea of a bicycle, in this example holding a
wheel size and a weight that can be different for each such
instance of a bicycle. This is how you handle two different
bicycles:

```
type Bicycle {
    var wheel_size = 0.5
    var weight = 2.0
}

func main {
    var my_bicycle = new Bicycle()
    print(my_bicycle.weight)
    var my_second_bicycle = new Bicycle()
    my_second_bicycle.weight = 5
    print(my_second_bicycle.weight)
}
```

This example now uses a different weight than the default weight
of 2.0 for your second bicycle object. These objects can now
be passed around to various functions to do things with
them.

If you want to learn more on types and objects, [read here
for an explanation of object-oriented
programming](/docs/OOP.md).



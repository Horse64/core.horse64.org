
<!-- For license of this file, see LICENSE.md in the base dir. -->

Modules, Packages, Imports
==========================

This document describes how Horse64 code is organized, and how you can
integrate third-party libraries and code. For a simple program
you can have some single `myprogram.h64` text file with all your code,
but for non-trivial programs you'll want to use multiple files.
Each such file is then called a module, but read on for details:


How a project is organized
--------------------------

A **package** is Horse64's name for a more-or-less complete project,
e.g. a project directory holding your piece of software or library
would be a package. (Or as another example, `core.horse64.org` is
the package holding all the standard library functionality,
with things like I/O and math basics likely needed by most
programs.)

A **module** is Horse64's name for what you organize in either a single
code file, or whatever is then grouped in a directory. For example, the
`math` module in `core.horse64.org` is implemented in a respective
`math.h64` file. The `compiler.main` module sits in a `compiler/main.h64`
file, and it's a **submodule** of the `compiler` module.

To use code from a separate module, simply import it:
```Horse64
import math from core.horse64.org

func main {
    print("Maximum of 5 and 6: " + math.max(5, 6).as_str())
}
```

An **import** simply declares what external module you want to use.
All global vars and funcs and types in that module then become
available by prefixing them with `module.`, see `math.` in above
example.

The **`from` clause** of an import statement declares the package
that module is in. The clause can and should be omitted if it's
from the same package or project that your code file is already in.

**Global initialization code, like assigned default values for
global variables, runs for each import module** before the actual
program main entrypoint starts.

The **main entrypoint is the `main` function** you have to declare
somewhere for your program.

Summed up: `my/random/dir/codefile.h64` becomes a module
that can be imported as `my.random.dir.codefile` for use.


Neighboring modules are automatically imported
----------------------------------------------

Neighbor modules in the same subdirectory also always get pulled
in and processed. Example:

*In file `mymodule/neighbor.h64`:*
```Horse64
import mytype

extend mytype.Storage {
    var buckets
}
```
*In file `mymodule/mytype.h64`:*
```Horse64
type Storage {
    var brooms
}
```
When you use `import mymodule.mytype`, then the custom type
`mymodule.mytype.Storage` will automatically have both the
var attributes `brooms` and `buckets`, even if you never
explicitly import `mymodule.neighbor` anywhere.

This is because **any import of a module also processes
all the ones in the same directory,** allowing easy use
of [extending types](/docs/OOP.md#extend-things) like
in the example above. However, anything in deeper
subdirectories or outside of the directory won't be pulled in.


Folder init module files
------------------------

As a special case, when a code file has the same name as the
surrounding directory e.g. named `mymodule`, it sort of
"represents" the functions of that module directory.

See here, an example:

*In file `mymodule/mymodule.h64`:*
```Horse64
var test = print_hello()

func print_hello {
    print("Hello from mymodule")
}
```

*Above code gets triggered with this import:*
```Horse64
import mymodule
```
Also, after this import, `mymodule.print_hello` and
`mymodule.test` can be accessed.


How to get more packages
------------------------

To download packages for your project, use [horp](
/docs/Resources.md#horp) in your project directory:
```bash
$ horp install my.package.name
```
Read more in *horp*'s documentation to find out about details.


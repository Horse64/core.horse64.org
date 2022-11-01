
# Data Types

These are the data types available in Horse64:

| Data type name   | How to instantiate          | Mutable | GC load |
|------------------|-----------------------------|---------|---------|
| none             | `none`                      | no      | no      |
| num              | `1`, `1.0`, `-2.332`, `0x3` | no      | no      |
| str              | `"bla"`, `'bla'`, `""`      | no      | no      |
| bytes            | `b"test"`, `b''`            | no      | no      |
| bool             | `yes`, `no`                 | no      | no      |
| vector           | `[x:1, y:5, z:3, w:1.1]`    | no      | no      |
| list             | `[]`, `[1, 2]`              | yes     | yes     |
| map              | `{"price"-> 5.0}`, `{->}`   | yes     | yes     |
| set              | `{}`, `{1, 2}`              | yes     | yes     |
| type             | `new MyCustomType()`        | yes     | yes     |
|------------------|-----------------------------|---------|---------|


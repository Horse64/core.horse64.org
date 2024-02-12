
<!-- For license of this file, see LICENSE.md in the base dir. -->

Operators
---------

This is a listing of the various operations on variables
possible in Horse64, like addition, substraction, and
so on. You may find this interesting as an expert user.

All operators will raise a `TypeError` if not applied to
the supported types specified:

### Math operators (`T_MATH`)

| Operator  | Type   | Purpose                                        |
|-----------|--------|------------------------------------------------|
| A `+` B   | Math   | Adds two numbers.                              |
| A `-` B   | Math   | Substracts one number from the other.          |
| `-`A      | Math   | Computes the negated inverse of a number.      |
| A `*` B   | Math   | Multiplies two numbers.                        |
| A `/` B   | Math   | Multiplies two numbers.                        |
| A `%` B   | Math   | Computes the modulo of a divsion.              |
| A `^` B   | Math   | Computes the exponent of `B` over `A`.         |
| A `<<` B  | Bitwise | Bit shifts `A` left `B` times, zero padded.   |
| A `>>` B  | Bitwise | Bit shifts `A` right `B` times, zero padded.  |
| `~`A      | Bitwise | Inverts all the bits in `A`.                  |
| A `&` B   | Bitwise | Computes bitwise "and" on the bits.           |
| A &#124; B| Bitwise | Computes bitwise "or" on the bits.            |
| A `^^` B  | Bitwise | Computes bitwise "xor" on the bits.           |

*(All operators except for `-` always take a left-hand
and right-hand side, so they're all binary operators)*

- All these operators can be applied to any pair of numbers,
  and cause an `OverflowError` if a 64bit double value is
  exceeded. There are no `NaN` or infinity values.

- The bitwise operators will round the number to an integer
  first if it has a fractional part and cause an `OverflowError`
  if the number exceeds a 32bit int value.

- The `+` operator can also be applied to two strings, or
  two lists, or two sets, or two vectors, or two maps,
  or one list and one set (any order, left-hand
  determines the return type).

- The `-` operator can also be used as a unary operator.

### Comparison operators (`T_COMPARE`)

`==`, `!=`, `>`, `<`, `>=`, `<=`.

*(These all take a left-hand and right-hand side,
so they're all binary operators)*

- The first two, `==` and `!=`, can be applied to any types,
  the others to either a pair of numbers, or a pair of strings
  which compares them based on unicode code point values.
  All comparisons evaluate to either boolean `yes` or boolean `no`.

- The `==` operator compares **by value if the data types are
  passed by contents, otherwise it compares if the instance
  is the same.** [Check this list to see which data type
  is by value](/docs/Language%20Specs/Data%20Types.md).

  For example, for numbers or strings, `==` will
  compare the actual contents for equality. So the following
  prints out `yes`:

  ```Horse64
  func main {
      var n1 = 2
      var n2 = 2
      print(n1 == n2)  # yes!
  }
  ```

  However, for a list or object instance of a custom type,
  it will check if the given two sides are both **the exact
  same list or object instance, not just the contents.**
  This means the following prints out `no`:

  ```Horse64
  func main {
      var l1 = []
      var l2 = []
      print(l1 == l2)  # no!
  }
  ```

- To compare lists, sets, maps, etc. by value, use their
  `alike` func attribute: `[].alike([])` returns `yes`,
  for example. You can also implement `alike` for your
  own [custom types](/docs/OOP.md), if desired.

### Boolean operators (`T_BOOLCOMP`)

`not`, `and`, `or`.

*(The `not` operator only takes a right-hand side
and is therefore unary, the others are binary operators.)*

- All of these can be applied to any pair of booleans,
  and will return a boolean (`yes`/`no`).

- The `and` operator will only evaluate the right-hand side
  if the left-hand turns out to be boolean `yes`.

- The `or` operator will only evaluate the right-hand side
  if the left-hand turns out to be boolean `no`.

### `new` operator (`T_NEWOP`)

`new`.

*(It just takes a right-hand side, it's an unary operator.)*

Example: `new type_name(arg1, arg2)`

- This operator can be applied to an identifier that
  refers to a type, combined with arguments
  for the constructor.

- The operator evaluates to an object instance, or it may
  raise any error caused by the `init` function
  attribute when run.

### Index by expression operator

`[` with closing `]`.

*(It takes both a right-hand and left-hand side,
so it's a binary operator)*

Example: `somecontainer[<indexexpr>]`.

- This operator can be applied to any container of type
  list or vector, and takes a number type for indexing. It
  evaluates to the respective nth list or vector item.

- If the number passed in is lower than `1` or higher than
  the amount of items, an `IndexError` will be raised.

### Attribute by identifier operator

`.` (dot).

*(It has both right- and left-hand side,
it's a binary operator)*

Example: `someitem.identifier`.

- The item can be any arbitrary expression.
  The operator can be applied on any item, even numbers or
  booleans or even none, but will raise an `AttributeError`
  if the given data type doesn't have this attribute.

- For object instances created from your [custom types](
  /docs/OOP#custom-types-in-horse64) via `new`, the attributes
  are as specified by your type. Beyond that, many values
  have special attributes, see the [data types listing](
  /docs/Language%20Specs/Data%20Types.md) for these.
  E.g., all values have the `.as_str()` attribute
  that when called returns a string value representing them.

### Call operator

`(` with closing `)`.

*(Also a binary operator with left- and right-hand side.)*

Example: `left_hand_called_side(right_hand_argument_side)`

- This calls the left-hand side with the given arguments
  inside the parenthesis.

### Operator precedences

If operators aren't clearly nested via parenthesis to indicate
evaluation order, then it is determined by operator precedence.
For simplicity, precedence is presented here by pasting the
according implementation code of [horsec](../horsec/horsec.md)
found in `src/compiler/operator.h64`:

```
var precedence_table = [  # From closest-binding to loosest:
    ["new"],
    [["-", token.T_UNARYMATH]],
    ["~", "&"],
    ["|"],
    ["^^"],
    ["/", "*", "%", "^"],
    ["+", ["-", token.T_MATH]],
    ["<<", ">>"],
    ["==", "!="],
    [">=", "<="],
    [">", "<"],
    ["not"],
    ["and"],
    ["or"],
]
```


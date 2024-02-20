
<!-- For license of this file, see LICENSE.md in the base dir. -->

Grammar Rules
=============

This document attempts to specify the Horse64 grammar in written
rules. The actual AST parser of [horsec](/docs/Resource.md#horsec)
isn't directly based on this ruleset, so it's possible for this
to lag behind. [Please report mistakes you find](
https://horse64.org/docs/Resources#report-bugs).

**Important note on precedence:** this grammar ignores operator precedence.
For the `operatorexpr` expansion of the `expr ::= ...` grammar rule,
you must pick the expansions with the **right-most** occurrence of the
**highest precedence number** operator that is applicable.
You must also always expand to an `operatorexpr` if possible, and only
to other `expr` expansions if that isn't possible.
For precedence numbers, check the [operators precedence section](
/docs/Operators.md#operator-precedences).

**Grammar formatting notes:**

- The grammar lists the expansion rules, starting with a `program`
  item, that produce the concrete values possible for program.

- Lists of chained expanded elements are specified as
  `(element_1, element_2, ...)`. Special characters are specified
  in single quotes, like `','` for a literal comma,
  or `'('` for a literal parenthesis. If there's no single quotes,
  it's not meant as the literal character.

- Literal words like for keywords are specified with double quotes,
  e.g. `"import"` for the the `import` keyword.

- Multiple expansion choices are separated by a single pipe, `|`.

- Optional items are followed by a question mark, e.g. `item?`.

- Any `identifier` refers to any custom choice of identifier,
  e.g. `my_thing`.
  And `typepath_identifier` refers to an identifier that optionally
  has a type path in front, e.g. `some.module.MyType`.


### Grammar listing

The actual grammar rules follow:

#### Grammar listing: top-level structure
```
program ::= (toplvlstmt_1, toplvlstmt_2, ...)
toplvlstmt ::= vardefstmt | funcdefstmt | importstmt |
               typedefstmt | enumstmt | extendtypestmt |
               extendenumstmt
```

#### Grammar listing: top-level statements
```
vardefstmt ::= "var" identifier "deprecated"? |
                "var" identifier "deprecated"? '=' expr |
                "var" identifier "deprecated"? '=' latercallexpr
funcdefstmt ::= "func" identifier (funcprop_1, funcprop_2, ...)
                codeblock
importstmt ::= "import" typepath_identifier importlibinfo?
               importrename?
typestmt ::= "type" identifier
             baseinfo? (typeprop_1, typeprop_2, ...)
             typecodeblock
enumstmt ::= "enum" identifier '{'
             enumlist '}'
extendtypestmt ::= "extend" "type" typepath_identifier
                   typecodeblock
extendenumstmt ::= "extend" "enum" typepath_identifier
                   enumlist
```

#### Grammar listing: code blocks and general statements
```
codeblock ::= '{' (innerstmt_1, innerstmt_2, ...) '}'
innerstmt ::= vardefstmt | funcdefstmt | callstmt | assignstmt |
              ifstmt | whilestmt | forstmt | withstmt |
              dorescuefinallystmt | vardefstmt |
              awaitstmt
callstmt ::= callexpr
assignstmt ::= lvalueexpr '=' expr |
               lvalueexpr assignbinop expr
ifstmt ::= "if" expr codeblock elseifblocklist? elseblock?
whilestmt ::= "while" expr codeblock
forstmt ::= "for" identifier "in" expr codeblock
withstmt ::= "with" withitemlist codeblock
dorescuefinallystmt ::= "do" codeblock rescueblock? finallyblock?
returnstmt ::= "return" | "return" expr
throwstmt ::= "throw" | "throw" expr
awaitstmt ::= "await" expr
continuestmt ::= "continue"
breakstmt ::= "break"
```

#### Grammar listing: detail rules for top-level statements
```
importlibinfo ::= "from" typepath_identifier
importrename ::= "as" identifier
typepath_identifier ::= identifierwithdot identifier
identifierwithdot ::= identifier '.'

typecodeblock ::= '{' (typeattrstmt_1, typeattrstmt_2, ...) '}'
typeattrstmt ::= varattrstmt | funcdefstmt
baseinfo ::= "base" expr
typeprop ::= "deprecated"
funcprop ::= "deprecated"
varattrprops ::= "protect"? "deprecated"?
varattrstmt ::= "var" identifier varattrprops? |
                "var" identifier varattrprops? '=' expr |
                "const" identifier varattrprops? |
                "const" identifier vardefporps? '=' expr

enumlist ::= (enumentry_1, enumentry_2) enumlastitem
enumitem ::= identifier enumnumberassign? ','
enumnumberassign ::= '=' numliteral
enumlastitem ::= identifier enumnumberassign? ','?
```

#### Grammar listing: detail rules for general statements
```
elseifblocklist ::= (elseifblock_1, elseifblock_2, ...)
elseifblock ::= "elseif" expr codeblock
elseblock ::= "else" codeblock

withitemlist ::= (withitem_1, withitem_2, ...) withlastitem
withitem ::= expr "as" identifier ','
withlastitem ::= expr "as" identifier

rescueblock ::= "rescue" rescuelist codeblock
rescuelist ::= (rescueitem_1, rescueitem_2, ...) rescuelastitem
rescueitem ::= 'any' | rescuespecificitem
rescuelastitem ::= 'any' | rescuelastspecificitem
rescuespecificitem ::= expr "as" identifier ','
rescuelastspecificitem ::= expr "as" identifier

finallyblock ::= "finally" codeblock
```

#### Grammar listing: inline expressions
```
expr ::= '(' expr ')' | callexpr | literalexpr |
         operatorexpr | inlineifexpr

callexpr ::= expr '(' terminatedcommaexprlist kwarglist ')' |
             expr '(' commaexprlist ')' |
             expr '(' kwarglist ')'
latercallexpr ::= callexpr "later:" |
                  callexpr "later" "repeat" |
                  callexpr "later" "ignore"

terminatedcommaexprlist ::= (commaitem_1, commaitem_2, ...)

commaexprlist ::= (commaitem_1, commaitem_2, ...) commalastitem?
commaitem ::= expr ','
commalastitem ::= expr

kwarglist ::= (kwargitem_1, kwargitem_2, ...) kwarglastitem?
kwargitem ::= identifier '=' expr ','
kwarglastitem ::= identifier '=' expr

operatorexpr ::= binopexpr | unopexpr
binopexpr ::= expr binop expr
unopexpr ::= unop expr

inlineifexpr ::= "if" expr '(' expr ')' "else" '(' expr ')'
```

#### Grammar listing: literal constructors
```
literalexpr ::= "none" | "yes" | "no" | numliteral |
                stringliteral | containerexpr

containerexpr ::= setexpr | mapexpr | listexpr | vecexpr
listexpr ::= '[' commaexprlist ']'
setexpr ::= '{' commaexprlist '}'
mapexpr ::= '{' mapitemlist '}'
mapitemlist ::= (mapitem_1, mapitem_2, ...) maplastitem?
mapitem ::= expr '->' expr ','
maplastitem ::= expr '->' expr
vecexpr ::= '[' vecitemlist ']'
vecitemlist ::= vec2itemlist | vec3itemlist | vec4itemlist
vec2itemlist ::= vecitem veclastitem
vec3itemlist ::= vecitem vecitem veclastitem
vec4itemlist ::= vecitem vecitem vecitem veclastitem
vecitem ::= numliteral ':' expr ','
veclastitem ::= numliteral ':' expr ','?
```

### A few missing rules in writing

`assignbinop` can be `+=`, `-=`, `*=`, and `/=`. Assignments
with these assignment math operators are just a short hand,
e.g. `lvalue += expr` means `lvalue = lvalue + expr`.

`binopexpr` ignores that the index by expression binary operator
has a closing element `']'` afterwards.
You must also exclude the call binary operator `(` from the expansion
choices of `binop`, since that one is handled by `callexpr`.

`lvalueexpr` is a special expression that can be either a `binopexpr`
using the index by expression operator, or the attribute by identifier
operator, or a plain `identifier`. It cannot be any other expression.

`vecexpr` has some rules omitted above for brevity, e.g.
the numbers need to start with `1` and count up:
`[1: <expr>, 2: <expr>, ...]`. You can also optionally
specify xyzw for the first three items, e.g. `[x: <expr>, y: <expr>]`.

`numliteral` can be anything that matches any of these regexes:
```
-?[0-9]+(\.[0-9]+)?
0x[0-9a-f]+
```

`stringliteral` can be anything that matches any of these regexes:
```
"([^"]|\\")"
'([^']\\')'
```

The `breakstmt` and `continuestmt` rules can only be used in code
blocks that are inside `while` or `for` loop code blocks (including
nested blocks).


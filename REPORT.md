# Technical Report: Mini Interpreter with Scope & Function Support

**Course:** Programming Languages  
**Project:** Mini Interpreter — Lexer → Parser → Evaluator Pipeline  
**Language Implemented:** Mini  
**Implementation Language:** Python 3.12  
**Date:** June 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Language Design and Features](#2-language-design-and-features)
3. [System Architecture](#3-system-architecture)
4. [Lexer — Tokenization](#4-lexer--tokenization)
5. [Parser — Syntax Analysis and AST](#5-parser--syntax-analysis-and-ast)
6. [Interpreter — Tree-walking Evaluation](#6-interpreter--tree-walking-evaluation)
7. [Scope and Environment](#7-scope-and-environment)
8. [Type System and Runtime Types](#8-type-system-and-runtime-types)
9. [Implementation of PL Concepts](#9-implementation-of-pl-concepts)
10. [Challenges and Discussion](#10-challenges-and-discussion)
11. [Testing and Sample Programs](#11-testing-and-sample-programs)
12. [Conclusion](#12-conclusion)
13. [PL Concept Mapping Table](#13-pl-concept-mapping-table)

---

## 1. Introduction

This project implements a fully functional **Mini Interpreter** for a custom
scripting language called *Mini*, demonstrating the core concepts taught in a
Programming Languages course. The interpreter is built as a clean three-stage
pipeline:

```
Source Text  →  [Lexer]  →  Token Stream  →  [Parser]  →  AST  →  [Interpreter]  →  Output
```

The design goal was to keep every stage independently understandable, with each
module mapping to one or more Programming Languages concepts. The system supports
the full set of required PL concepts plus all three elected elective concepts:
**Recursion**, **Exception Handling**, and **Higher-order Functions**.

### What Mini Can Do

Mini is a dynamically-typed, expression-oriented scripting language with:

- Variables (`let`), arithmetic, comparisons, logical operators
- If/else chains, while loops
- First-class named and anonymous functions with closure semantics
- User-defined struct types with named fields
- Dynamic lists backed by a singly linked list
- Try/catch/throw exception handling
- Built-in higher-order functions: `map`, `filter`, `reduce`, `forEach`
- A built-in library: `print`, `input`, `str`, `num`, `type`, `len`, `range`,
  `abs`, `sqrt`, `max`, `min`, `split`, `join`, and more

### Project Structure

```
mini_interpreter/
├── main.py                        Entry point: REPL + file runner
├── lexer/
│   └── lexer.py                   Tokenizer (Lexer class)
├── parser/
│   ├── ast_nodes.py               All AST node dataclasses
│   └── parser.py                  Recursive-descent parser
├── interpreter/
│   ├── environment.py             Scope chain (Environment class)
│   ├── builtins.py                Built-in function registry
│   └── interpreter.py            Tree-walking evaluator
├── runtime/
│   ├── types.py                   Runtime value type hierarchy
│   └── exceptions.py             Custom exception hierarchy
└── tests/
    ├── test_interpreter.py        59-test unit/integration suite
    └── programs/                  Sample .mini source files
        ├── fibonacci.mini         Recursion demonstration
        ├── closures.mini          Higher-order functions and closures
        ├── linked_list.mini       User-defined types and dynamic structures
        ├── exceptions.mini        Exception handling
        ├── structs.mini           Struct types and encapsulation
        └── all_features.mini      Full integration demo
```

---

## 2. Language Design and Features

### 2.1 Syntax Overview

Mini uses a clean, curly-brace block syntax inspired by modern scripting
languages. Newlines are insignificant; statements end at natural boundaries.

```mini
# Variable declaration
let x = 10
let name = "Alice"

# Arithmetic and string operations
let result = (x * 2 + 5) % 7
let greeting = "Hello, " + name

# Conditional
if result > 3 {
    print("big")
} else if result == 3 {
    print("three")
} else {
    print("small")
}

# Loop
let i = 0
while i < 5 {
    print(i)
    i = i + 1
}

# Named function
fun factorial(n) {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

# Anonymous function / lambda
let double = fun(x) { return x * 2 }

# Higher-order functions
let nums    = [1, 2, 3, 4, 5]
let doubled = map(nums, double)
let evens   = filter(nums, fun(x) { return x % 2 == 0 })
let total   = reduce(nums, fun(a, x) { return a + x }, 0)

# Exception handling
try {
    throw "oops"
} catch(e) {
    print("Caught: " + e)
}

# User-defined struct type
struct Point { x, y }
let p = new Point(3, 4)
print(p.x + p.y)    # 7
```

### 2.2 Operator Precedence

Operators follow standard mathematical precedence, implemented by the parser's
layered recursive-descent methods:

| Level | Operator(s) | Associativity |
|-------|-------------|---------------|
| 1 (lowest) | assignment `=` | Right |
| 2 | `or` | Left |
| 3 | `and` | Left |
| 4 | `not` (prefix) | — |
| 5 | `== !=` | Left |
| 6 | `< > <= >=` | Left |
| 7 | `+ -` | Left |
| 8 | `* / %` | Left |
| 9 | unary `-` `not` | — |
| 10 | call `()` · member `.` · index `[]` | Left |
| 11 (highest) | literals, identifiers, `(expr)` | — |

### 2.3 Type System Summary

Mini is dynamically typed. Values carry their type at runtime:

| Mini Type | Description | `type()` returns |
|-----------|-------------|-----------------|
| `Number` | IEEE 754 float | `"Number"` |
| `String` | Immutable UTF-8 string | `"String"` |
| `Bool` | `true` / `false` | `"Bool"` |
| `Null` | Singleton null value | `"Null"` |
| `List` | Dynamic linked-list | `"List"` |
| `Function` | User-defined / closure | `"Function"` |
| `Builtin` | Native Python function | `"Builtin"` |
| `StructDef` | Struct type constructor | `"StructDef"` |
| `<StructName>` | Struct instance | the struct's name |

---

## 3. System Architecture

### 3.1 Pipeline Overview

The interpreter follows the classic three-stage pipeline:

```
┌──────────────────────────────────────────────────────────────┐
│  Stage 1: Lexical Analysis                                   │
│  lexer/lexer.py  →  Lexer.tokenize()                        │
│  Input:  raw source string                                   │
│  Output: list[Token]  (type, value, line)                   │
└──────────────────────────┬───────────────────────────────────┘
                           │ Token stream
┌──────────────────────────▼───────────────────────────────────┐
│  Stage 2: Syntax Analysis                                    │
│  parser/parser.py  →  Parser.parse()                        │
│  Input:  list[Token]                                         │
│  Output: Program (AST root node)                            │
└──────────────────────────┬───────────────────────────────────┘
                           │ Abstract Syntax Tree
┌──────────────────────────▼───────────────────────────────────┐
│  Stage 3: Evaluation                                         │
│  interpreter/interpreter.py  →  Interpreter.run()          │
│  Input:  Program (AST)                                       │
│  Support: Environment (scope), MiniValue (runtime types)    │
│  Output: side-effects + optional last MiniValue             │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Module Dependency Graph

```
main.py
  ├── lexer.lexer          (no dependencies on other project modules)
  ├── parser.parser
  │     └── parser.ast_nodes
  │     └── runtime.exceptions
  └── interpreter.interpreter
        ├── parser.ast_nodes
        ├── runtime.types
        ├── runtime.exceptions
        ├── interpreter.environment
        └── interpreter.builtins
              └── runtime.types
```

Each stage depends only on stages before it and the shared runtime layer.
There are no circular dependencies.

### 3.3 Data Flow Through a Function Call

```
Source: "add(3, 4)"

Lexer:
  IDENTIFIER("add") LPAREN NUMBER(3) COMMA NUMBER(4) RPAREN EOF

Parser:
  CallExpr(
    callee = Identifier("add"),
    args   = [NumberLiteral(3), NumberLiteral(4)]
  )

Interpreter._eval_call():
  1. Resolve "add" in env  → MiniFunction(name="add", params=["a","b"], closure=global_env)
  2. Evaluate args         → [MiniNumber(3), MiniNumber(4)]
  3. _call_mini_function():
       call_env = global_env.child("<fn:add>")
       call_env.define("a", MiniNumber(3))
       call_env.define("b", MiniNumber(4))
       exec body → return MiniNumber(7)
  4. Catch ReturnSignal    → return MiniNumber(7)
```

---

## 4. Lexer — Tokenization

**File:** `lexer/lexer.py`

### 4.1 Responsibilities

The Lexer converts the raw source string into a flat sequence of `Token` objects.
It handles:

- Numeric literals (integer and float): `42`, `3.14`
- String literals with escape sequences: `"hello\nworld"`
- Identifiers and keywords: `fun`, `let`, `if`, `while`, …
- Two-character operators: `==`, `!=`, `<=`, `>=`
- Single-character operators: `+`, `-`, `*`, `/`, `%`, `<`, `>`, `=`
- Delimiters: `(`, `)`, `{`, `}`, `[`, `]`, `,`, `.`, `;`
- Single-line comments starting with `#`
- Whitespace and newlines (discarded)

### 4.2 Token Design

```python
@dataclass
class Token:
    type:  TokenType   # enum — the category
    value: object      # float for NUMBER, str for IDENTIFIER, None for keywords
    line:  int         # source line for error reporting
```

`TokenType` is a Python `Enum` with one variant per category. This is a
**user-defined type** — a discriminated tag for the token classification.

### 4.3 Algorithm

The lexer is a single-pass scanner. It maintains three pieces of state: the
source string, a position cursor, and a line counter. The main loop calls
`_scan_token()` which reads one character, dispatches to the appropriate
sub-scanner, and appends a Token.

```python
def tokenize(self) -> list[Token]:
    while self._pos < len(self._source):
        self._scan_token()
    self._add(TokenType.EOF)
    return self._tokens
```

### 4.4 Keyword Classification

Identifiers are first scanned as a word, then looked up in the `KEYWORDS`
dictionary. If a match is found, the token type is replaced with the keyword
type; otherwise it remains `IDENTIFIER`. This avoids special-casing every
keyword character by character.

```python
KEYWORDS = { "let": TokenType.LET, "fun": TokenType.FUN, … }

def _identifier(self, first: str) -> None:
    name = first + read_while(alnum_or_underscore)
    ttype = KEYWORDS.get(name, TokenType.IDENTIFIER)
    self._add(ttype, name if ttype == TokenType.IDENTIFIER else None)
```

### 4.5 Error Handling

`LexerError` is raised immediately on encountering an unrecognised character or
an unterminated string literal, with the current line number attached.

---

## 5. Parser — Syntax Analysis and AST

**Files:** `parser/parser.py`, `parser/ast_nodes.py`

### 5.1 Abstract Syntax Tree Node Design

Every AST node is a Python `@dataclass`. Dataclasses implement the
**User-defined Types** concept: each is a named product type (record) with typed
fields. The full set of node types constitutes a **discriminated union** (sum
type) for the language's grammar.

Key node families:

```
Statements                     Expressions
──────────────────────         ────────────────────────────
Program          LetStatement  BinaryExpr      UnaryExpr
FunctionDecl     AssignStatement  CallExpr     IndexExpr
ReturnStatement  IfStatement   MemberExpr      ListExpr
WhileStatement   Block         LambdaExpr      NewExpr
TryCatchStatement ThrowStatement  NumberLiteral StringLiteral
StructDecl       ExprStatement  BoolLiteral    NullLiteral
                               Identifier
```

Each node carries a `line: int = 0` field (always last, satisfying Python's
dataclass default-field ordering rule) for error-message line numbers.

### 5.2 Recursive-Descent Parser

The parser is a hand-written recursive-descent parser. Each grammar production
rule maps directly to one method. The layered method hierarchy encodes operator
precedence without a separate precedence table:

```
parse()
  └─ _statement()
       ├─ _let_stmt()
       ├─ _fun_decl()
       ├─ _if_stmt()
       ├─ _while_stmt()
       ├─ _try_catch_stmt()
       ├─ _struct_decl()
       └─ _expr_statement()
            └─ _expression() → _assignment() → _or_expr() → _and_expr()
                 → _not_expr() → _equality() → _comparison()
                 → _addition() → _multiplication() → _unary()
                 → _call() → _primary()
```

**Modular Decomposition:** every production is its own method with a single
responsibility. Adding a new language construct requires adding one method and
one dispatch case — no other method changes.

### 5.3 Expression Parsing Example

Parsing `3 + 4 * 2` with correct precedence:

```
_addition() calls _multiplication() for the left operand
  _multiplication() calls _unary() → _call() → _primary() → NumberLiteral(3)
  No * or / → returns NumberLiteral(3)
_addition() sees +, advances
_addition() calls _multiplication() for the right operand
  _multiplication() gets NumberLiteral(4)
  Sees *, advances
  _multiplication() gets NumberLiteral(2)
  Returns BinaryExpr(NumberLiteral(4), '*', NumberLiteral(2))
_addition() returns BinaryExpr(NumberLiteral(3), '+', BinaryExpr(4,'*',2))
```

The evaluator processes this tree and produces `11`.

### 5.4 Parse Error Reporting

`_expect(ttype, msg)` consumes a token of the required type or raises
`ParseError` with the expected type, actual type, and source line:

```
[Line 5] ParseError: Expected IDENTIFIER, got NUMBER (42.0)
```

---

## 6. Interpreter — Tree-walking Evaluation

**File:** `interpreter/interpreter.py`

### 6.1 Design

The interpreter is a **tree-walking evaluator**: it traverses the AST and
directly executes each node. This is the simplest and most readable evaluator
design, well-suited for demonstrating PL concepts because the code structure
mirrors the language semantics.

There is no intermediate bytecode or compilation step. The trade-off is
performance (slower than compiled approaches), but correctness and clarity are
maximised.

### 6.2 Dispatch

Two main dispatch methods handle all nodes:

- `_exec(node, env)` — dispatches statement nodes using `isinstance` checks
- `_eval(node, env)` — dispatches expression nodes, always returns a `MiniValue`

```python
def _exec(self, node, env):
    if isinstance(node, LetStatement):      return self._exec_let(node, env)
    if isinstance(node, IfStatement):       return self._exec_if(node, env)
    if isinstance(node, WhileStatement):    return self._exec_while(node, env)
    if isinstance(node, FunctionDecl):      return self._exec_fun_decl(node, env)
    if isinstance(node, TryCatchStatement): return self._exec_try_catch(node, env)
    …
```

### 6.3 Function Calls

Function calls follow the lexical scoping model:

```python
def _call_mini_function(self, fn, args, line):
    # 1. Create a new scope rooted in the CLOSURE environment (lexical scoping)
    call_env = fn.closure.child(f"<fn:{fn.name}>")

    # 2. Bind parameters to arguments in the new scope
    for param, arg in zip(fn.params, args):
        call_env.define(param, arg)

    # 3. Execute the body; catch ReturnSignal
    try:
        self._exec_block(fn.body, call_env)
        return MiniNull()
    except ReturnSignal as ret:
        return ret.value
```

The key insight is step 1: the new scope extends `fn.closure` (where the function
was *defined*), not the caller's environment. This implements **lexical scoping**.

### 6.4 Control Flow Signals

Two Python exceptions serve as control-flow signals within the interpreter:

| Signal | Purpose |
|--------|---------|
| `ReturnSignal(value)` | Raised by `return`; caught at the function-call boundary to extract the return value |
| `MiniThrown(value, line)` | Raised by `throw`; propagates up until caught by a `try/catch` handler |

Both are subclasses of Python's `Exception` so they unwind the Python call stack
naturally — no manual stack tracking is needed.

### 6.5 Short-circuit Evaluation

Logical `and` and `or` are short-circuit evaluated:

```python
if node.op == "and":
    left = self._eval(node.left, env)
    return left if not left.is_truthy() else self._eval(node.right, env)
```

The right operand is never evaluated if the left operand determines the result.

---

## 7. Scope and Environment

**File:** `interpreter/environment.py`

### 7.1 Environment as a Scope Chain

An `Environment` is a dictionary of name-to-value bindings plus a reference to
a parent `Environment`. This forms a linked chain from the innermost (most local)
scope to the global scope.

```
Global env: { print: <builtin>, fib: <fun>, x: 10 }
     ↑ parent
  Function env <fn:fib>: { n: 7 }
       ↑ parent
    Recursive call env <fn:fib>: { n: 6 }
```

### 7.2 Scope Operations

| Operation | Method | Behaviour |
|-----------|--------|-----------|
| Declare | `define(name, value)` | Always creates in *this* frame (shadows outer) |
| Read | `get(name, line)` | Walks chain inward→outward until found |
| Mutate | `assign(name, value, line)` | Walks chain to find the owning frame |
| New scope | `child(name)` | Creates a child Environment extending this one |

**Shadowing example:**

```mini
let x = 10          # bound in global env
fun f() {
    let x = 20      # new binding in f's env — shadows global x
    return x        # → 20
}
print(f())          # => 20
print(x)            # => 10  (global x unchanged)
```

### 7.3 Lexical vs Dynamic Scoping

This interpreter implements **lexical (static) scoping**: a function's scope
chain is determined by *where it was defined* in the source code, not where it
is called from. This is the key to making closures work correctly:

```mini
fun make_adder(x) {
    return fun(y) { return x + y }   # captures x from make_adder's scope
}

let add5 = make_adder(5)   # make_adder returns; its frame still referenced by add5's closure
print(add5(3))              # => 8   (x=5 is still alive in the closure)
```

When `make_adder(5)` returns, the lambda's `closure` field still references the
frame containing `x = 5`. That frame is kept alive by Python's garbage collector
as long as the lambda exists.

### 7.4 Variable Lifetime

A binding's lifetime is tied to the `Environment` object that contains it:

- **Global variables** live for the entire interpreter session.
- **Function-local variables** live for the duration of the function call.
- **Block-local variables** (inside if/while) live for the duration of that
  block's execution, since each if/while creates a child environment.
- **Closure-captured variables** live as long as the closure function object exists.

---

## 8. Type System and Runtime Types

**File:** `runtime/types.py`

### 8.1 Type Hierarchy

All runtime values inherit from the abstract base class `MiniValue`:

```
MiniValue  (abstract)
  ├── MiniNumber          float storage; integer display when whole
  ├── MiniString          immutable str
  ├── MiniBool            true / false
  ├── MiniNull            singleton (only one null exists)
  ├── MiniList            singly linked list of LinkedNode objects
  ├── MiniFunction        user-defined function + closure environment
  ├── MiniBuiltin         native Python callable wrapped for Mini
  ├── MiniStructDef       struct type definition (callable constructor)
  └── MiniObject          struct instance (dict of named field values)
```

### 8.2 Abstract Interface

`MiniValue` defines three abstract methods that every concrete type must implement:

```python
class MiniValue(ABC):
    @abstractmethod
    def is_truthy(self) -> bool: …   # used by if/while conditions

    @abstractmethod
    def to_display(self) -> str: …   # used by print() and error messages

    @abstractmethod
    def type_name(self) -> str: …    # used by the built-in type() function
```

The interpreter only ever calls these three methods on a `MiniValue` — it never
inspects raw Python attributes. This satisfies **Abstraction & Encapsulation**.

### 8.3 MiniList — Linked List Implementation

`MiniList` stores its elements as a singly linked list of `LinkedNode` objects:

```python
class LinkedNode:
    __slots__ = ("value", "next")
    def __init__(self, value: MiniValue, next_node: Optional["LinkedNode"] = None):
        self.value = value    # payload
        self.next  = next_node  # "pointer" to next node
```

Each `LinkedNode` is independently heap-allocated. The list head is a reference to
the first node. Operations:

| Operation | Complexity | Description |
|-----------|-----------|-------------|
| `prepend` | O(1) | Re-point head to new node |
| `push` (append) | O(n) | Traverse to tail, attach new node |
| `get(i)` | O(n) | Pointer-chase i times from head |
| `set(i, v)` | O(n) | Pointer-chase then update value field |
| `pop` | O(n) | Traverse to second-to-last, set next = None |

The O(n) cost of append and indexing is a **deliberate pedagogic choice** to
demonstrate the classic trade-off of linked lists versus array-backed lists.

### 8.4 Null Singleton

`MiniNull` is implemented as a Python singleton (only one instance ever exists):

```python
class MiniNull(MiniValue):
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

This means `null == null` is always true by identity, matching user expectations.

### 8.5 Type Safety

Arithmetic operators require Number operands. `_req_num()` enforces this:

```python
def _req_num(self, val, op, line):
    if isinstance(val, MiniNumber):
        return val.value
    raise MiniRuntimeError(
        f"Operator '{op}' requires a Number, got {val.type_name()}", line
    )
```

This produces errors like:
```
[Line 3] MiniRuntimeError: Operator '+' requires a Number, got Bool
```

rather than a cryptic Python `AttributeError`.

---

## 9. Implementation of PL Concepts

### 9.1 Required Concepts

#### 9.1.1 Functions / Procedures

**Where:** `interpreter/interpreter.py` (`_exec_fun_decl`, `_call_mini_function`),
`runtime/types.py` (`MiniFunction`)

Functions are first-class values stored as `MiniFunction` objects. A `FunctionDecl`
statement creates a `MiniFunction` and binds it by name in the current scope. An
anonymous `LambdaExpr` does the same without binding a name.

Calling any function follows the same path through `_call_value()`, regardless of
whether it is user-defined or built-in. This uniform dispatch is a direct
application of the **Abstraction** principle.

```mini
# Named function
fun greet(name) {
    return "Hello, " + name
}

# Anonymous function stored in a variable
let square = fun(x) { return x * x }

# Functions as arguments (higher-order)
let result = map([1,2,3], square)
```

#### 9.1.2 Scope and Environment

**Where:** `interpreter/environment.py`

The `Environment` class implements a scope chain. Each function call creates a
child environment. Variable lookup walks the chain. Assignment finds and modifies
the owning frame. See Section 7 for the full discussion.

Key invariant: the scope chain is a **tree**, not a stack. When closures are
created, multiple function instances can share a parent scope without interfering.

#### 9.1.3 Dynamic Memory / Heap Usage

**Where:** `runtime/types.py` (`LinkedNode`, `MiniList`, `MiniObject`), `interpreter/environment.py`

Every value in Mini is heap-allocated by Python's memory manager. The project
explicitly demonstrates this through:

1. **MiniList / LinkedNode**: each `LinkedNode` is an independently heap-allocated
   object with a `next` pointer, modelling a classical C-style linked list.
2. **MiniObject**: each struct instance is a heap-allocated dict of field values.
3. **Environment**: each scope frame is a heap-allocated dict; the chain of frames
   lives as long as any reference to it (e.g., a closure) exists.

#### 9.1.4 User-defined Types

**Where:** `parser/ast_nodes.py` (all dataclass nodes), `runtime/types.py` (`MiniStructDef`, `MiniObject`), `lexer/lexer.py` (`Token`, `TokenType`)

Two distinct manifestations:

**In the interpreter implementation** — all AST nodes and runtime types are Python
dataclasses and class hierarchies, demonstrating user-defined types in the host
language.

**In the Mini language** — users declare struct types with named fields:

```mini
struct Point    { x, y }
struct BankAccount { owner, balance }

let p = new Point(3, 4)
print(p.x)        # 3
p.y = 10
print(p.y)        # 10
```

`StructDecl` registers a `MiniStructDef` in the environment. Calling the struct
name (or using `new`) invokes `_construct_struct()` which creates a `MiniObject`
with the named fields bound to the provided values.

#### 9.1.5 Abstraction and Encapsulation

**Where:** `runtime/types.py` (`MiniValue` ABC), `interpreter/builtins.py`, `interpreter/interpreter.py`

**Abstraction** is demonstrated at multiple levels:

1. `MiniValue` abstract base class: the evaluator interacts with all values
   through `is_truthy()`, `to_display()`, `type_name()` — never through
   concrete subclass attributes.
2. `Environment.get/assign/define`: callers never touch `_bindings` directly.
3. `Interpreter.run()`: callers never interact with the internal `_exec`/`_eval`
   dispatch machinery.
4. Built-in functions: from Mini code, `map` and `print` are indistinguishable
   from user-defined functions. The interface hides the Python implementation.

**Encapsulation** is enforced by Python's naming conventions (`_bindings`,
`_pos`, `_tokens` etc. are private to their classes).

#### 9.1.6 Dynamic Data Structures

**Where:** `runtime/types.py` (`MiniList`, `LinkedNode`)

`MiniList` is a heap-allocated singly linked list. Nodes are created, linked, and
released dynamically at runtime. The implementation explicitly models:

- **Allocation**: `LinkedNode(value, next_node)` — a new heap object
- **Pointer manipulation**: `current = current.next` — following the link
- **Deallocation**: Python's GC automatically reclaims unreferenced nodes after
  `pop()` sets a node's predecessor's `next` to `None`

Users also implement linked lists *in Mini itself* using structs:

```mini
struct Node { value, next }
struct LinkedList { head, size }

fun push_front(lst, val) {
    let node = new Node(val, lst.head)  # allocate new node
    lst.head = node                      # update head pointer
    lst.size = lst.size + 1
}
```

This double-layer demonstration (once in Python, once in Mini) reinforces the
concept from both sides.

#### 9.1.7 Type Usage / Type Design

**Where:** `runtime/types.py`, `interpreter/interpreter.py` (`_req_num`)

The type design decisions in Mini are:

- **Number** unifies integers and floats (like JavaScript/Lua), simplifying the
  language for learners while avoiding integer/float confusion.
- **Null** is a singleton distinct from 0, `""`, and `false` — preventing
  subtle truthy/falsy bugs present in languages that overload zero as null.
- **Bool** is a separate type; `0 == false` evaluates to `false` (different
  types are never equal), enforcing type precision.
- Struct instances carry their struct name as their `type_name()`, making runtime
  type inspection meaningful.

---

### 9.2 Elective Concepts

#### 9.2.1 Recursion

**Where:** `interpreter/interpreter.py` (`_call_mini_function`)

Recursion works because every function call creates a new, independent
`Environment` frame. The Python call stack implicitly tracks the recursion depth.
The interpreter does not impose a custom recursion limit; Python's default
`sys.setrecursionlimit` (1000) applies, and the REPL catches `RecursionError`
with a clean message.

**Demonstration — Fibonacci (tree recursion):**

```mini
fun fib(n) {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}
print(fib(10))   # => 55
```

Each call to `fib(n)` generates two recursive calls, forming a binary tree of
frames. Because each frame is independent (different `n`), correctness is
guaranteed by the Environment design.

**Demonstration — Mutual recursion:**

```mini
fun is_even(n) {
    if n == 0 { return true }
    return is_odd(n - 1)
}
fun is_odd(n) {
    if n == 0 { return false }
    return is_even(n - 1)
}
```

Mutual recursion works because function names are resolved at *call time* by
looking up the name in the environment, not at *definition time*. As long as both
functions are defined before either is called, it works correctly.

#### 9.2.2 Exception Handling

**Where:** `runtime/types.py` (`MiniThrown`, `ReturnSignal`), `interpreter/interpreter.py` (`_exec_try_catch`, `_exec_throw`), `runtime/exceptions.py`

Mini implements a `throw` / `try` / `catch` mechanism that closely models
mainstream exception handling:

```mini
try {
    if x < 0 {
        throw "negative value"
    }
    print("ok: " + str(x))
} catch(e) {
    print("Caught: " + e)
}
```

**Implementation mechanism:**

1. `throw expr` evaluates `expr` to a `MiniValue` and raises Python's
   `MiniThrown(value, line)`.
2. `MiniThrown` propagates up the Python call stack, unwinding through any
   number of nested function calls and blocks — exactly as a real exception
   would.
3. `try/catch` is implemented by Python's `try/except MiniThrown`:

```python
def _exec_try_catch(self, node, env):
    try:
        self._exec_block(node.body, env.child("<try>"))
    except MiniThrown as exc:
        handler_env = env.child("<catch>")
        handler_env.define(node.error_name, exc.value)
        self._exec_block(node.handler, handler_env)
```

4. If no `catch` intercepts the throw, `MiniThrown` propagates to `main.py`
   which reports it as an uncaught throw.

**Throwing struct instances** enables structured error objects:

```mini
struct AppError { code, message }
try {
    throw new AppError(404, "not found")
} catch(e) {
    print(str(e.code) + ": " + e.message)
}
```

#### 9.2.3 Higher-order Functions

**Where:** `interpreter/builtins.py` (`_map_fn`, `_filter_fn`, `_reduce_fn`, `_foreach_fn`), `interpreter/interpreter.py` (`_eval_lambda`, `_call_value`)

Higher-order functions are functions that accept or return other functions.
Mini implements this through:

**First-class functions:** `MiniFunction` and `MiniBuiltin` are values that can
be stored in variables, passed as arguments, and returned.

**Built-in HOFs:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `map` | `(list, fn)` | Apply `fn` to each element, return new list |
| `filter` | `(list, predicate)` | Retain elements where `predicate(x)` is truthy |
| `reduce` | `(list, fn, initial)` | Fold `fn` over list from left |
| `forEach` | `(list, fn)` | Call `fn(x)` for each element (side effects) |

**Closures** make HOFs powerful. `make_adder` below produces specialised
functions that remember the `x` value from their creation scope:

```mini
fun make_adder(x) {
    return fun(y) { return x + y }
}
let add5  = make_adder(5)
let add10 = make_adder(10)
print(add5(3))   # => 8
print(add10(7))  # => 17
```

**Function composition via `reduce`:**

```mini
fun compose(fns) {
    return fun(x) {
        return reduce(fns, fun(acc, f) { return f(acc) }, x)
    }
}
let pipeline = compose([
    fun(x) { return x * 2 },
    fun(x) { return x + 10 },
    fun(x) { return 0 - x }
])
print(pipeline(3))   # => -(3*2+10) = -16
```

---

## 10. Challenges and Discussion

This section describes four concrete technical problems encountered during
development, the alternatives considered, and the reasoning behind each final
design decision.

---

### 10.1 Challenge: Lexical vs Dynamic Scoping

**The problem.** When designing how variable lookup should work for function
calls, two models are possible:

- **Dynamic scoping** — a function looks up names in the *calling* environment.
  `f()` called from inside `g()` would see `g()`'s local variables.
- **Lexical (static) scoping** — a function always looks up names in the
  environment where it was *defined*, regardless of who calls it.

Early prototypes used a simpler approach that inadvertently produced dynamic
scoping: the interpreter passed the current `env` to each function call and
created a child of *that* environment:

```python
# WRONG — dynamic scoping
call_env = env.child(f"<fn:{fn.name}>")   # env is the caller's env!
```

This appeared to work for simple programs but produced wrong results for
closures:

```mini
fun make_adder(x) {
    return fun(y) { return x + y }
}
let add5 = make_adder(5)
let x = 99
print(add5(3))   # Dynamic scoping would print 102 (caller's x), not 8!
```

**The fix.** The `MiniFunction` object stores the *defining* environment as
`self.closure`. The call site always creates a child of the closure, not the
calling environment:

```python
# CORRECT — lexical scoping
call_env = fn.closure.child(f"<fn:{fn.name}>")   # fn.closure = defining env
```

This single-line change made closures, higher-order functions, and recursive
inner functions all work correctly, because they always see the variables
that were in scope when they were written — independent of where or how deeply
they are called.

**Lesson.** The distinction between lexical and dynamic scoping is one of the
most consequential design choices in a programming language. Lexical scoping is
predictable (the programmer can reason about a function by reading only its
definition), while dynamic scoping ties behaviour to the call stack at runtime.
Modern languages universally prefer lexical scoping for this reason.

---

### 10.2 Challenge: Linked List vs Array for MiniList

**The problem.** The obvious implementation of a dynamic list in Python is to
wrap a Python `list`. That would have made every operation O(1) amortized and
required zero pointer logic. Yet the project requires demonstrating *dynamic
data structures* and *heap usage* — two concepts that are invisible when Python's
built-in list handles everything.

**The alternatives considered:**

| Option | Implementation effort | Pedagogic value |
|--------|----------------------|-----------------|
| Wrap Python `list` | Trivial | Low — heap/pointer work is hidden |
| Doubly-linked list | High | High — but adds complexity without much gain |
| Singly-linked list | Medium | High — pointer allocation, traversal, deallocation |

**The decision.** A singly linked list using explicit `LinkedNode` heap objects
was chosen. This produces concrete, inspectable pointer operations:

```python
class LinkedNode:
    __slots__ = ("value", "next")
    def __init__(self, value, next_node=None):
        self.value = value      # payload on the heap
        self.next  = next_node  # the "pointer"
```

Every `push()` call allocates a new `LinkedNode`. Every `pop()` severs a
`next` pointer so the GC can reclaim the node. `_node_at(i)` follows `next`
pointers in a loop — exactly as a C program would follow `node->next`.

The O(n) cost of append and indexing was accepted *deliberately* to demonstrate
the classic linked-list trade-off: O(1) prepend at the cost of O(n) random
access. This trade-off is documented in comments and in the report.

**The double benefit.** The same concept is demonstrated at *two levels*:
once in Python (the `MiniList` implementation), and again in Mini itself (the
`linked_list.mini` sample program uses structs to build a manual linked list
in the mini language). A learner sees the pattern from both the host-language
and the implemented-language perspective.

---

### 10.3 Challenge: Implementing `return` and `throw` via Python Exceptions

**The problem.** A function's `return` statement can appear deep inside nested
`if`/`while`/`try` blocks. The interpreter needs to stop executing the current
block and all ancestor blocks, transferring control back to the function call
site. The naïve approach is to propagate a sentinel return value through every
`_exec` call:

```python
# NAÏVE — every method must check and forward the sentinel
def _exec_if(self, node, env):
    result = self._exec_block(node.then_branch, env)
    if isinstance(result, ReturnSentinel):   # must check on every return
        return result                         # must forward on every return
    …
```

This approach is error-prone: any `_exec_*` method that forgets to check loses
the return value silently. The same pattern would be needed for `throw`.

**The solution.** Both control-flow exits are implemented as Python exceptions:

```python
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

class MiniThrown(Exception):
    def __init__(self, value, line): self.value = value; self.line = line
```

- A `return` statement raises `ReturnSignal(value)`.
- Python's own call-stack unwinding propagates it through every intermediate
  `_exec_*` frame automatically.
- `_call_mini_function` catches `ReturnSignal` and extracts the value.
- A `throw` statement raises `MiniThrown(value, line)`.
- `_exec_try_catch` catches `MiniThrown` and runs the handler.

```python
# In _call_mini_function — the ONLY place ReturnSignal needs to be caught
try:
    self._exec_block(fn.body, call_env)
    return MiniNull()
except ReturnSignal as ret:
    return ret.value    # clean extraction; no forwarding boilerplate
```

There is one subtle complication: `ReturnSignal` must *escape* loops. If a
`while` body executes `return`, the loop's own `try/except ReturnSignal: raise`
block re-raises it so that the signal continues propagating upward to the
function boundary:

```python
def _exec_while(self, node, env):
    while self._eval(node.condition, env).is_truthy():
        try:
            self._exec_block(node.body, env.child("<while>"))
        except ReturnSignal:
            raise   # must not swallow the return signal!
```

**Lesson.** Reusing the host language's exception mechanism to implement the
guest language's control flow is a common and elegant pattern in tree-walking
interpreters. It avoids building a separate stack-management module and keeps
all the unwinding logic in one well-understood place.

---

### 10.4 Challenge: Operator Precedence in the Recursive-Descent Parser

**The problem.** The parser must produce AST nodes that encode correct operator
precedence without an explicit precedence table. For example:

```
3 + 4 * 2   must parse as   3 + (4 * 2)   not   (3 + 4) * 2
```

A naive single-level expression parser would treat all operators equally and
produce left-to-right grouping, giving wrong results.

**The solution: precedence climbing via layered methods.** Each precedence level
is a distinct parsing method that calls the *next higher* level for its
operands:

```
_assignment()          (lowest)
  → _or_expr()
      → _and_expr()
          → _not_expr()
              → _equality()
                  → _comparison()
                      → _addition()
                          → _multiplication()
                              → _unary()
                                  → _call()
                                      → _primary()   (highest)
```

`_addition()` calls `_multiplication()` on both sides of a `+` or `-`:

```python
def _addition(self):
    left = self._multiplication()     # binds tighter than +
    while self._check(PLUS, MINUS):
        op    = …
        right = self._multiplication()  # right side also binds tight
        left  = BinaryExpr(left, op, right)
    return left
```

This guarantees `4 * 2` is evaluated before `3 +` because `_multiplication`
runs to completion before `_addition` even sees the `+`.

**Right-associativity for assignment.** Assignment `=` is right-associative
(`a = b = 1` means `a = (b = 1)`). This is handled by making `_assignment`
call *itself* recursively for the right-hand side instead of calling
`_or_expr`:

```python
def _assignment(self):
    left = self._or_expr()
    if self._match(ASSIGN):
        value = self._assignment()   # recursive call → right-associative
        return AssignStatement(left, value)
    return left
```

**Short-circuit evaluation interaction.** `and` and `or` are at two separate
precedence levels (`_and_expr` and `_or_expr`), ensuring `a or b and c` parses
as `a or (b and c)`. The short-circuit behaviour itself is implemented in the
*evaluator* (`_eval_binary`), not the parser — the parser only records the tree
structure.

**Lesson.** Operator precedence in a recursive-descent parser falls naturally
out of the call hierarchy. Adding a new operator at an existing level costs one
line (add it to the `while self._check(…)` set). Adding a new precedence level
costs one new method and one call site. This extensibility is a key advantage
of the hand-written recursive-descent approach over parser-generator tools,
which require learning a DSL and produce less readable error messages.

---

## 11. Testing and Sample Programs

### 11.1 Test Suite

**File:** `tests/test_interpreter.py`

The test suite contains **59 unit and integration tests** organised by PL concept:

| Test Class | Tests | Concepts Covered |
|-----------|-------|-----------------|
| `TestLexer` | 5 | Tokenisation, keyword detection |
| `TestParser` | 4 | AST structure, parse errors |
| `TestVariables` | 6 | Let, arithmetic, strings, assignment |
| `TestScope` | 4 | Shadowing, mutation, lexical scope |
| `TestFunctions` | 4 | Declaration, return, first-class |
| `TestRecursion` | 3 | Fibonacci, factorial, mutual recursion |
| `TestExceptions` | 6 | Basic catch, propagation, nesting, structs |
| `TestHigherOrder` | 5 | map, filter, reduce, closures |
| `TestStructs` | 5 | Creation, mutation, type names |
| `TestDynamicStructures` | 7 | List operations, range, len |
| `TestTypeSafety` | 3 | Arithmetic mismatch, index error |
| `TestBuiltins` | 7 | str, num, type, abs, sqrt, split/join |

All 59 tests pass:

```
$ python -m pytest tests/test_interpreter.py -v
59 passed in 0.91s
```

### 11.2 Sample Programs

#### fibonacci.mini — Recursion

```mini
fun fib(n) {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}
let i = 0
while i < 10 {
    print("fib(" + str(i) + ") = " + str(fib(i)))
    i = i + 1
}
```

**Output:**
```
fib(0) = 0
fib(1) = 1
fib(2) = 1
fib(3) = 2
fib(4) = 3
fib(5) = 5
fib(6) = 8
fib(7) = 13
fib(8) = 21
fib(9) = 34
```

#### closures.mini — Higher-order Functions & Closures

```mini
fun make_adder(x) {
    return fun(y) { return x + y }
}
let add5 = make_adder(5)
print(add5(3))    # 8

let numbers = [1, 2, 3, 4, 5]
let doubled = map(numbers, fun(x) { return x * 2 })
let evens   = filter(numbers, fun(x) { return x % 2 == 0 })
let total   = reduce(numbers, fun(acc, x) { return acc + x }, 0)

print(doubled)    # [2, 4, 6, 8, 10]
print(evens)      # [2, 4]
print(total)      # 15
```

#### linked_list.mini — User-defined Types + Dynamic Data Structures

```mini
struct Node { value, next }
struct LinkedList { head, size }

fun push_back(lst, val) {
    let node = new Node(val, null)
    if lst.head == null { lst.head = node }
    else {
        let current = lst.head
        while current.next != null { current = current.next }
        current.next = node
    }
    lst.size = lst.size + 1
}

fun sum_list(node) {
    if node == null { return 0 }
    return node.value + sum_list(node.next)
}

let myList = create_list()
push_back(myList, 10)
push_back(myList, 20)
push_back(myList, 30)
print(to_string(myList))              # 10 -> 20 -> 30 -> null
print("sum = " + str(sum_list(myList.head)))  # sum = 60
```

#### exceptions.mini — Exception Handling

```mini
struct AppError { code, message }

fun validate_age(age) {
    if age < 0 or age > 150 {
        throw new AppError(400, "Invalid age: " + str(age))
    }
    return true
}

try {
    validate_age(200)
} catch(err) {
    print("Error " + str(err.code) + ": " + err.message)
}
# Output: Error 400: Invalid age: 200
```

---

## 12. Conclusion

### 12.1 What Was Achieved

This project successfully implements a fully functional interpreter for the Mini
scripting language, covering **all seven required PL concepts** and **all three
chosen elective concepts**. The 59-test suite passes completely, and six sample
programs demonstrate the language's capabilities end-to-end.

| Required Concept | Status |
|-----------------|--------|
| Functions / Procedures | ✓ Named, anonymous, closures, first-class |
| Scope and Environment | ✓ Lexical scoping, scope chain, shadowing |
| Dynamic Memory / Heap | ✓ LinkedNode heap allocation, MiniObject, Environment |
| User-defined Types | ✓ Struct declaration and instantiation, dataclass AST nodes |
| Abstraction & Encapsulation | ✓ MiniValue ABC, private state, uniform callable interface |
| Dynamic Data Structures | ✓ Linked list (Python and Mini), list operations |
| Type Usage / Type Design | ✓ Type hierarchy, type safety guards, type() builtin |

| Elective Concept | Status |
|-----------------|--------|
| Recursion | ✓ Fibonacci, factorial, mutual recursion |
| Exception Handling | ✓ throw/try/catch, propagation, struct errors |
| Higher-order Functions | ✓ map, filter, reduce, closures, function composition |

### 12.2 Key Design Decisions

1. **Linked list for MiniList:** Choosing a linked list over a Python list for the
   dynamic data structure was a deliberate pedagogic decision. It makes heap
   allocation and pointer manipulation explicit and visible in the source code,
   rather than hiding them inside Python's list implementation.

2. **Lexical scoping over dynamic scoping:** Lexical scoping was chosen because
   it is the standard in modern languages and makes program behaviour easier to
   reason about. The closure implementation naturally follows from this choice.

3. **Signals as Python exceptions:** Using `ReturnSignal` and `MiniThrown` as
   Python exceptions to implement Mini's return and throw is an elegant reuse of
   Python's own control-flow mechanism. It avoids writing a manual stack
   unwinding loop.

4. **Uniform callable interface:** Both `MiniFunction` and `MiniBuiltin` are
   dispatched through `_call_value()`. Users cannot tell the difference; built-in
   functions can be passed to higher-order functions exactly like user-defined ones.

### 12.3 Possible Extensions

- **For loops:** `for x in list { … }` — syntactic sugar over while + index
- **String interpolation:** `f"value is {x}"` for ergonomic output
- **Modules / imports:** `import "math.mini"` for multi-file programs
- **Tail-call optimisation:** Convert tail-recursive calls to iteration to
  remove the Python recursion limit constraint
- **Bytecode compilation:** Replace tree-walking with a simple stack VM for
  significantly better performance

---

## 13. PL Concept Mapping Table

| PL Concept | Category | Primary File(s) | Key Class / Function | Mini Language Feature |
|-----------|----------|----------------|---------------------|----------------------|
| **Functions / Procedures** | Required | `runtime/types.py` · `interpreter/interpreter.py` | `MiniFunction` · `_exec_fun_decl` · `_call_mini_function` | `fun name(params) { body }` |
| **Scope and Environment** | Required | `interpreter/environment.py` | `Environment` · `define` · `get` · `assign` · `child` | Variable visibility, shadowing |
| **Dynamic Memory / Heap** | Required | `runtime/types.py` | `LinkedNode` · `MiniObject` · `MiniList` | List and struct allocation |
| **User-defined Types** | Required | `parser/ast_nodes.py` · `runtime/types.py` | All `@dataclass` nodes · `MiniStructDef` · `MiniObject` | `struct Name { fields }` |
| **Abstraction & Encapsulation** | Required | `runtime/types.py` · `interpreter/interpreter.py` | `MiniValue` (ABC) · `_call_value` · private `_` members | Uniform callable interface |
| **Dynamic Data Structures** | Required | `runtime/types.py` | `MiniList` · `LinkedNode` (push, pop, prepend, get) | `[1,2,3]` list literals; mini-language linked list via structs |
| **Type Usage / Type Design** | Required | `runtime/types.py` · `interpreter/interpreter.py` | `MiniNumber` · `MiniString` · `MiniBool` · `MiniNull` · `_req_num` | `type(x)` · arithmetic type guards |
| **Recursion** | Elective | `interpreter/interpreter.py` | `_call_mini_function` (no special handling needed) | `fun fib(n) { … return fib(n-1) + fib(n-2) }` |
| **Exception Handling** | Elective | `runtime/types.py` · `interpreter/interpreter.py` · `runtime/exceptions.py` | `MiniThrown` · `ReturnSignal` · `_exec_try_catch` · `_exec_throw` | `try { … } catch(e) { … }` · `throw value` |
| **Higher-order Functions** | Elective | `interpreter/builtins.py` · `interpreter/interpreter.py` | `_map_fn` · `_filter_fn` · `_reduce_fn` · `_eval_lambda` | `map(lst, fn)` · `filter` · `reduce` · `fun(x){…}` closures |

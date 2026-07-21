# Mini Interpreter

A tree-walking interpreter for **Mini**, a small dynamically-typed scripting
language, implemented from scratch in Python. Built as the final project for
a university Programming Languages course, it covers the full pipeline —
lexer, recursive-descent parser, and evaluator — along with closures,
recursion, exception handling, user-defined struct types, and higher-order
functions.

The project has zero third-party runtime dependencies: everything is
standard-library Python.

```mini
fun make_adder(x) {
    return fun(y) { return x + y }
}

let add5 = make_adder(5)
print(add5(3))              # 8

let numbers = [1, 2, 3, 4, 5]
let evens   = filter(numbers, fun(x) { return x % 2 == 0 })
print(evens)                 # [2, 4]

struct Point { x, y }
let p = new Point(3, 4)
print(p.x + p.y)             # 7
```

## Features

- **Variables and expressions** — `let` bindings, arithmetic, comparisons, string concatenation, `and`/`or`/`not` with short-circuit evaluation
- **Control flow** — `if` / `else if` / `else` chains, `while` loops
- **Functions** — named declarations, anonymous lambdas, and first-class values with proper lexical closures
- **Recursion** — direct and mutual recursion, backed by independent scope frames per call
- **Structs** — user-defined record types (`struct Name { fields }`) with `new` construction and field mutation
- **Exception handling** — `try` / `catch` / `throw`, including propagation through nested calls and throwing struct instances as structured errors
- **Higher-order functions** — built-in `map`, `filter`, `reduce`, `forEach` operating on first-class functions
- **Dynamic lists** — backed by a hand-written singly linked list (not Python's `list`), to make heap allocation and pointer manipulation explicit
- **A small standard library** — `print`, `input`, `str`, `num`, `type`, `bool`, `len`, `range`, `append`, `prepend`, `pop`, `abs`, `max`, `min`, `floor`, `sqrt`, `pow`, `split`, `join`, `trim`, `error`
- **Descriptive runtime errors** — every error carries the source line and a human-readable message instead of a raw Python traceback

## Project Structure

```
mini-interpreter/
├── main.py                    Entry point — REPL and script runner
├── lexer/
│   └── lexer.py                Tokenizer: source text → token stream
├── parser/
│   ├── ast_nodes.py             AST node definitions (dataclasses)
│   └── parser.py                Recursive-descent parser: tokens → AST
├── interpreter/
│   ├── environment.py           Scope chain / lexical scoping
│   ├── builtins.py              Standard library functions
│   └── interpreter.py           Tree-walking evaluator
├── runtime/
│   ├── types.py                 Runtime value types (MiniNumber, MiniList, …)
│   └── exceptions.py            Error hierarchy (ParseError, MiniRuntimeError, …)
├── examples/                   Sample .mini programs
├── tests/
│   └── test_interpreter.py      59-test unit and integration suite
├── REPORT.md                   Full technical write-up and design rationale
├── LICENSE
├── requirements.txt
└── .gitignore
```

## Architecture

Mini follows the classic three-stage interpreter pipeline. Each stage is an
independent module and depends only on the stage before it plus the shared
runtime layer — there are no circular dependencies.

```
Source Code
     │
     ▼
  Lexer            lexer/lexer.py
     │              source string → list[Token]
     ▼
  Parser           parser/parser.py
     │              tokens → AST (Program)
     ▼
Interpreter        interpreter/interpreter.py
     │              walks the AST, evaluates each node
     ▼
  Runtime          runtime/types.py + interpreter/environment.py
     │              value types, scope chain, heap-allocated structures
     ▼
  Output
```

The parser is hand-written recursive-descent: each precedence level
(assignment, `or`, `and`, equality, comparison, addition, multiplication,
unary, call/index/member, primary) is its own method, so operator precedence
falls out of the call hierarchy rather than a separate precedence table. The
interpreter is a tree-walking evaluator — no intermediate bytecode — which
keeps the code structure close to the language semantics at the cost of raw
execution speed.

Function calls use **lexical scoping**: calling a function creates a new
scope as a child of the environment where the function was *defined*
(`fn.closure`), not the environment of the caller. This single design
decision is what makes closures behave correctly. `return` and `throw` are
both implemented as Python exceptions (`ReturnSignal`, `MiniThrown`) that
unwind the interpreter's own call stack, avoiding manual sentinel-passing
through every statement handler.

See [REPORT.md](REPORT.md) for the full design discussion, including the
alternatives that were considered and rejected for scoping and the list
data structure.

## Installation

Requires Python 3.8 or later. No packages need to be installed to run the
interpreter itself.

```bash
git clone https://github.com/<your-username>/mini-interpreter.git
cd mini-interpreter
```

`requirements.txt` only lists `pytest`, which is optional and needed solely
if you prefer running the test suite through pytest instead of `unittest`.

## Usage

Run a Mini source file:

```bash
python main.py examples/fibonacci.mini
```

Or start the interactive REPL:

```bash
python main.py
```

```
Mini Interpreter v1.0.0  —  type 'exit' or Ctrl-D to quit
mini> let x = 10
mini> print(x * 2)
20
```

## Examples

The `examples/` directory contains runnable programs, each focused on a
different part of the language:

| File | Demonstrates |
|------|---------------|
| `fibonacci.mini` | Recursion, tree recursion, iterative sum |
| `closures.mini` | Closures, `map` / `filter` / `reduce`, stateful counters |
| `structs.mini` | Struct types, a struct-based stack, encapsulation via helper functions |
| `linked_list.mini` | A linked list implemented in Mini itself, using structs as nodes |
| `exceptions.mini` | `try` / `catch` / `throw`, nested exception handling, struct-based error objects |
| `all_features.mini` | A small expression evaluator that exercises every language feature together |

Example output from `fibonacci.mini`:

```
$ python main.py examples/fibonacci.mini
fib(0) = 0
fib(1) = 1
fib(2) = 1
fib(3) = 2
fib(4) = 3
...
fib(10) = 55
sum 1..10 = 55
```

## Testing

The suite has 59 tests covering the lexer, parser, and interpreter,
organized by language concept (scope, recursion, exceptions, structs,
higher-order functions, type safety, and the built-in library).

```bash
python -m unittest tests.test_interpreter -v
```

or, with pytest installed:

```bash
pytest tests/ -v
```

## Report

[REPORT.md](REPORT.md) is the accompanying technical report written for the
course. It documents the language design, walks through each pipeline
stage in more depth than this README, and includes a section on concrete
implementation challenges — lexical vs. dynamic scoping, why `MiniList` is a
linked list instead of a wrapped Python list, and how `return`/`throw` are
implemented as control-flow exceptions — along with the reasoning behind
each decision.

## Future Improvements

Possible extensions, not currently implemented:

- `for` loops as sugar over `while` + indexing
- String interpolation (`"value is {x}"`)
- A module system for multi-file programs (`import "math.mini"`)
- Tail-call optimization, to remove the dependency on Python's recursion limit
- A bytecode-compiled backend as an alternative to tree-walking, for comparison

## License

MIT — see [LICENSE](LICENSE).

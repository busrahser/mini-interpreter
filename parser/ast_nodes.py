"""
AST NODES MODULE
================
PL Concept: User-defined Types / ADTs — every AST node is a Python dataclass.
Together the node classes form a discriminated union (sum type): a program is a
tree built from exactly these types and no others.  The dataclass decorator
generates __init__, __repr__, and __eq__ automatically, keeping the definitions
declarative.

PL Concept: Abstraction — callers work with symbolic, high-level node objects
(IfStatement, BinaryExpr, …) rather than raw token strings.  The structure of
the tree *is* the semantics; the original source text is irrelevant beyond this
point.

PL Concept: Modular Decomposition — each node type is defined once and used by
both the parser (which creates nodes) and the interpreter (which dispatches on
them).  Neither module depends on the other's internals.

Note on field ordering
----------------------
The base Node class carries a 'line' field with a default value of 0.
Because dataclass inheritance places parent fields first, all concrete subclass
fields (which have no default) must appear after 'line' in the MRO — but that
violates the rule that non-default fields cannot follow default fields.
Solution: do NOT inherit node-specific fields from Node.  Instead every
concrete class is a standalone @dataclass that simply includes 'line: int = 0'
as the *last* field, satisfying Python's "non-default before default" rule.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class Program:
    # PL Concept: Modular Decomposition — top-level list of independent statements
    body: list
    line: int = 0


@dataclass
class LetStatement:
    # PL Concept: Scope — 'let' introduces a new binding in the current environment frame
    name: str          # identifier to bind
    value: object      # expression whose result is bound to name
    line: int = 0


@dataclass
class AssignStatement:
    """target is Identifier, IndexExpr, or MemberExpr."""
    # PL Concept: Scope — assignment mutates an existing binding (walks up the scope chain)
    target: object     # the l-value: variable, list slot, or struct field
    value: object      # the r-value expression
    line: int = 0


@dataclass
class FunctionDecl:
    # PL Concept: Functions / Procedures — names a callable unit of computation
    # PL Concept: Scope — params become local bindings in the function's own frame
    name: str
    params: list       # list[str] — parameter names
    body: object       # Block — executed in a child scope on each call
    line: int = 0


@dataclass
class ReturnStatement:
    # PL Concept: Functions — unwinds the call stack back to the call site via ReturnSignal
    value: Optional[object]   # None means implicit null return
    line: int = 0


@dataclass
class IfStatement:
    """else_branch is a Block or another IfStatement (else-if chain)."""
    # PL Concept: Scope — each branch executes in its own child scope
    condition: object
    then_branch: object         # Block
    else_branch: Optional[object]  # Block | IfStatement | None
    line: int = 0


@dataclass
class WhileStatement:
    # PL Concept: Scope — body runs in a fresh child scope on every iteration
    condition: object
    body: object    # Block
    line: int = 0


@dataclass
class TryCatchStatement:
    # PL Concept: Exception Handling — catch intercepts MiniThrown exceptions
    body: object        # Block — statements that may throw
    error_name: str     # name bound to the thrown value inside the handler
    handler: object     # Block — executed with error_name in scope
    line: int = 0


@dataclass
class ThrowStatement:
    # PL Concept: Exception Handling — raises MiniThrown, unwinding the stack
    value: object    # expression; its result becomes the exception payload
    line: int = 0


@dataclass
class StructDecl:
    # PL Concept: User-defined Types — declares a named record type with fixed fields
    name: str
    fields: list     # list[str] — ordered field names
    line: int = 0


@dataclass
class Block:
    # PL Concept: Scope — executed in a provided (or child) environment; local lets
    # are visible only within this block's lifetime
    statements: list
    line: int = 0


@dataclass
class ExprStatement:
    # PL Concept: Modular Decomposition — lifts any expression to statement level
    expr: object
    line: int = 0


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class BinaryExpr:
    # PL Concept: Type Safety — the interpreter checks operand types before applying op
    left: object
    op: str     # string token: '+', '-', '==', 'and', 'or', …
    right: object
    line: int = 0


@dataclass
class UnaryExpr:
    # PL Concept: Type Safety — '-' requires Number; 'not' coerces via is_truthy()
    op: str        # '-' or 'not'
    operand: object
    line: int = 0


@dataclass
class CallExpr:
    # PL Concept: Functions / Procedures — callee can be any expression (first-class)
    callee: object   # Identifier, MemberExpr, or another CallExpr (chaining)
    args: list       # list of expression nodes evaluated left-to-right
    line: int = 0


@dataclass
class IndexExpr:
    # PL Concept: Dynamic Data Structures — array/list element access
    obj: object
    index: object   # must evaluate to MiniNumber at runtime (type safety)
    line: int = 0


@dataclass
class MemberExpr:
    # PL Concept: User-defined Types / Encapsulation — field access on struct instances
    obj: object
    member: str     # field name; validated at runtime by MiniObject.get_field()
    line: int = 0


@dataclass
class ListExpr:
    # PL Concept: Dynamic Data Structures — literal syntax for MiniList construction
    elements: list
    line: int = 0


@dataclass
class LambdaExpr:
    # PL Concept: Higher-order Functions — anonymous function; closure over current env
    # PL Concept: Scope — params become local bindings when the lambda is called
    params: list    # list[str]
    body: object    # Block
    line: int = 0


@dataclass
class NewExpr:
    # PL Concept: User-defined Types — explicit struct instantiation syntax
    # PL Concept: Dynamic Memory — triggers MiniObject heap allocation
    struct_name: str
    args: list      # positional values for each declared field
    line: int = 0


# ---------------------------------------------------------------------------
# Literals and identifiers
# ---------------------------------------------------------------------------

@dataclass
class NumberLiteral:
    # PL Concept: Type Design — literal notation for the Number type
    value: float     # stored as float even if the source wrote an integer
    line: int = 0


@dataclass
class StringLiteral:
    # PL Concept: Type Design — literal notation for the String type
    value: str       # already escape-processed by the lexer
    line: int = 0


@dataclass
class BoolLiteral:
    # PL Concept: Type Design — 'true'/'false' keywords produce MiniBool values
    value: bool
    line: int = 0


@dataclass
class NullLiteral:
    # PL Concept: Type Design — 'null' keyword produces the MiniNull singleton
    line: int = 0


@dataclass
class Identifier:
    # PL Concept: Scope — resolved at evaluation time by looking up name in Environment
    name: str
    line: int = 0

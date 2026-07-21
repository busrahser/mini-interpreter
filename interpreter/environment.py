"""
ENVIRONMENT MODULE
==================
PL Concept: Scope and Environment — an Environment is a single scope frame in
a chain that implements lexical (static) scoping.

How scoping works in this interpreter
--------------------------------------
Global scope is the root Environment (parent = None).

Each function call creates a *child* of the function's *closure* environment
(not the call-site environment), which is the key to lexical scoping.

Variable lookup walks the chain from innermost to outermost until the name is
found or the root is reached (→ undefined-variable error).

Assignment also walks the chain to modify the frame that *owns* the binding, so
inner scopes can mutate outer variables without re-declaring them with 'let'.

PL Concept: Variable Lifetime — a binding exists exactly as long as the
Environment object that contains it.  When a function returns, its frame
is no longer referenced and becomes eligible for garbage collection.  Variables
defined inside a loop body live only for that iteration.

PL Concept: Dynamic Memory / Heap — each Environment is heap-allocated.  The
chain of parent pointers is a dynamic linked structure that models the call stack.

PL Concept: Abstraction & Encapsulation — the _bindings dict is private.
External code uses define / get / assign; it never touches the dict directly.
"""

from __future__ import annotations
from typing import Optional, Any
from runtime.exceptions import MiniRuntimeError


class Environment:
    """
    A single scope frame.

    define()  — create a new local binding (let / parameter)
    get()     — look up a name walking outward through parent frames
    assign()  — modify an existing binding in the frame that owns it
    child()   — create a nested scope that extends this one
    """

    def __init__(self, parent: Optional["Environment"] = None, name: str = "<scope>"):
        self._bindings: dict[str, Any] = {}  # PL Concept: Environment — name→value store for this scope frame
        self.parent = parent     # PL Concept: Scope Chain — link to the enclosing frame; None = global root
        self.name = name         # human-readable label for debug/REPL output

    # ---- core operations ----

    def define(self, name: str, value: Any) -> None:
        """
        Bind name in *this* frame.  Used by let statements and parameter binding.
        Always creates a local binding even if the name already exists in an
        outer frame (shadowing).
        """
        self._bindings[name] = value  # PL Concept: Variable Declaration — new binding in current frame only

    def get(self, name: str, line: int = 0) -> Any:
        """
        Resolve a name by walking the scope chain inward → outward.
        PL Concept: Lexical Scoping — inner frames shadow outer ones.
        """
        if name in self._bindings:
            return self._bindings[name]  # PL Concept: Lexical Scoping — inner frame shadows any outer binding with same name
        if self.parent is not None:
            return self.parent.get(name, line)  # PL Concept: Scope Chain — walk up one level and retry
        raise MiniRuntimeError(f"Undefined variable '{name}'", line)  # PL Concept: Scope — name not found in any frame

    def assign(self, name: str, value: Any, line: int = 0) -> None:
        """
        Update an existing binding in the frame that *owns* it.
        PL Concept: Scope — modifies the correct frame regardless of nesting depth,
        allowing inner functions to update variables declared in an outer scope.
        """
        if name in self._bindings:
            self._bindings[name] = value  # PL Concept: Scope — update binding in the frame that owns it
            return
        if self.parent is not None:
            self.parent.assign(name, value, line)  # PL Concept: Scope Chain — not here, delegate to parent
            return
        raise MiniRuntimeError(
            f"Undefined variable '{name}' (cannot assign before 'let')", line
        )  # PL Concept: Scope — assigning to an undeclared name is a runtime error

    def child(self, name: str = "<scope>") -> "Environment":
        """Create a child scope that extends this one.
        PL Concept: Dynamic Memory / Heap — each call allocates a new Environment on the heap.
        PL Concept: Scope — the new frame's parent pointer forms the scope chain link."""
        return Environment(parent=self, name=name)  # PL Concept: Variable Lifetime — frame lives as long as any reference to it exists

    # ---- introspection ----

    def locals(self) -> dict[str, Any]:
        """Return a snapshot of bindings in this frame only (excludes parents)."""
        return dict(self._bindings)

    def depth(self) -> int:
        """Nesting depth: 0 = global scope."""
        return 0 if self.parent is None else 1 + self.parent.depth()

    def __repr__(self) -> str:
        return (
            f"Environment(name={self.name!r}, depth={self.depth()}, "
            f"vars={list(self._bindings.keys())})"
        )

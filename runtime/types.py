"""
RUNTIME TYPES MODULE
====================
PL Concept: User-defined Types — every runtime value is an instance of a
MiniValue subclass.  The subclass hierarchy is an explicit type design: each
type has a single responsibility and a well-defined interface.

PL Concept: Abstraction & Encapsulation — MiniValue is the abstract interface.
The evaluator never inspects raw Python values; it always calls .is_truthy(),
.to_display(), or .type_name() through the interface.  Internal storage details
(float vs bool vs linked head pointer) are hidden.

PL Concept: Dynamic Memory / Heap Usage — every MiniValue object is heap-
allocated by Python.  MiniList additionally builds a chain of LinkedNode objects
that explicitly model a heap-allocated singly linked list, demonstrating pointer-
based dynamic data structure creation.

PL Concept: Dynamic Data Structures — MiniList is backed by LinkedNode objects
forming a singly linked list.  push/pop/get/set/prepend demonstrate the classic
linked-list operations with explicit pointer manipulation.

PL Concept: Type Usage / Type Design — arithmetic operators use _require_number
style guards in the interpreter; type_name() exposes a run-time tag for the
built-in type() function.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from interpreter.environment import Environment


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class MiniValue(ABC):
    """
    Abstract base class for all runtime values.

    PL Concept: Abstraction — callers interact with this interface only.
    PL Concept: Encapsulation — concrete subclasses hide their storage.
    """

    @abstractmethod
    def is_truthy(self) -> bool:
        """Boolean interpretation used by if/while conditions."""

    @abstractmethod
    def to_display(self) -> str:
        """Human-readable string for print() and error messages."""

    @abstractmethod
    def type_name(self) -> str:
        """Run-time type tag returned by the built-in type() function."""

    def __repr__(self):
        return f"<{self.type_name()}: {self.to_display()}>"


# ---------------------------------------------------------------------------
# Primitive scalar types
# ---------------------------------------------------------------------------

class MiniNumber(MiniValue):
    """
    Numeric value stored as a Python float.
    PL Concept: Type Design — integers and floats share one Number type;
    display logic hides the float representation when the value is integral.
    """

    def __init__(self, value: float):
        self.value = float(value)

    def is_truthy(self) -> bool:
        return self.value != 0.0

    def to_display(self) -> str:
        if self.value == int(self.value) and not (self.value != self.value):
            return str(int(self.value))
        return str(self.value)

    def type_name(self) -> str:
        return "Number"

    def __eq__(self, other):
        return isinstance(other, MiniNumber) and self.value == other.value

    def __hash__(self):
        return hash(self.value)


class MiniString(MiniValue):
    """Immutable string value backed by a Python str."""

    def __init__(self, value: str):
        self.value = value

    def is_truthy(self) -> bool:
        return len(self.value) > 0

    def to_display(self) -> str:
        return self.value

    def type_name(self) -> str:
        return "String"

    def __eq__(self, other):
        return isinstance(other, MiniString) and self.value == other.value

    def __hash__(self):
        return hash(self.value)


class MiniBool(MiniValue):
    """Boolean value."""

    def __init__(self, value: bool):
        self.value = bool(value)

    def is_truthy(self) -> bool:
        return self.value

    def to_display(self) -> str:
        return "true" if self.value else "false"

    def type_name(self) -> str:
        return "Bool"

    def __eq__(self, other):
        return isinstance(other, MiniBool) and self.value == other.value

    def __hash__(self):
        return hash(self.value)


class MiniNull(MiniValue):
    """
    The null / nil value.  Implemented as a singleton so identity checks work.
    PL Concept: Type Design — a dedicated Null type avoids overloading 0 or ""
    to mean "nothing", improving type clarity.
    """

    _instance: Optional["MiniNull"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def is_truthy(self) -> bool:
        return False

    def to_display(self) -> str:
        return "null"

    def type_name(self) -> str:
        return "Null"

    def __eq__(self, other):
        return isinstance(other, MiniNull)

    def __hash__(self):
        return hash(None)


# ---------------------------------------------------------------------------
# Dynamic data structure: singly linked list
# ---------------------------------------------------------------------------

class LinkedNode:
    """
    PL Concept: Dynamic Data Structure — a singly-linked list node.
    Each instance is an independent heap object containing a value payload and
    a 'next' reference (pointer) to the following node or None (end-of-list).

    Creating and threading these nodes at runtime models explicit heap allocation
    and pointer manipulation as found in C/C++ linked list implementations.
    """

    __slots__ = ("value", "next")

    def __init__(self, value: MiniValue, next_node: Optional["LinkedNode"] = None):
        self.value: MiniValue = value                  # PL Concept: Dynamic Memory — payload stored on the heap inside this object
        self.next: Optional[LinkedNode] = next_node   # PL Concept: Dynamic Data Structure — pointer to successor node (or None = end of list)


class MiniList(MiniValue):
    """
    Dynamic list backed by a singly linked list of LinkedNode objects.

    PL Concept: Dynamic Data Structure — nodes are heap-allocated on demand;
    the list grows and shrinks at run time without a fixed capacity.

    PL Concept: Encapsulation — push / pop / get / set / prepend expose the
    list's behaviour without leaking the internal node structure.  Callers
    never touch LinkedNode directly.

    Trade-off (intentional for pedagogic purposes):
      O(1) prepend  vs  O(n) append / index access — the classic linked-list
      trade-off compared with array-backed lists.
    """

    def __init__(self, elements: Optional[list[MiniValue]] = None):
        self.head: Optional[LinkedNode] = None   # PL Concept: Dynamic Data Structure — head pointer; None = empty list
        self._size: int = 0                       # PL Concept: Encapsulation — cached size, not recomputed by traversal
        for el in (elements or []):
            self.push(el)   # PL Concept: Dynamic Memory — each push() allocates a new LinkedNode on the heap

    # ---- internal helpers ----

    def _node_at(self, index: int) -> LinkedNode:
        """Pointer-chase to node at position index.
        PL Concept: Dynamic Data Structures — O(n) traversal is the fundamental cost
        of a linked list; there is no O(1) random access like an array."""
        current = self.head
        for _ in range(index):
            if current is None:
                break
            current = current.next   # PL Concept: Dynamic Data Structure — follow the 'next' pointer
        return current  # type: ignore[return-value]

    def _to_python_list(self) -> list[MiniValue]:
        """Collect all values into a Python list (used by display and builtins)."""
        result: list[MiniValue] = []
        current = self.head
        while current is not None:
            result.append(current.value)
            current = current.next
        return result

    # ---- public interface ----

    def push(self, value: MiniValue) -> None:
        """Append to the end — O(n) pointer traversal to the tail.
        PL Concept: Dynamic Memory — allocates a new LinkedNode on each call."""
        new_node = LinkedNode(value)   # PL Concept: Dynamic Memory — new heap object for each element
        if self.head is None:
            self.head = new_node       # PL Concept: Dynamic Data Structure — first node becomes the head
        else:
            current = self.head
            while current.next is not None:
                current = current.next   # PL Concept: Dynamic Data Structure — pointer-chase to find the tail
            current.next = new_node     # PL Concept: Dynamic Data Structure — link the new node at the tail
        self._size += 1

    def prepend(self, value: MiniValue) -> None:
        """O(1) insert at the front — the natural cheap operation for linked lists.
        PL Concept: Dynamic Data Structures — O(1) vs O(n) trade-off: prepend is fast,
        append is slow; the opposite of array-backed lists."""
        self.head = LinkedNode(value, self.head)  # PL Concept: Dynamic Memory — new node; old head becomes its 'next'
        self._size += 1

    def pop(self) -> MiniValue:
        """Remove and return the last element.
        PL Concept: Dynamic Data Structures — O(n) pointer traversal to find the
        second-to-last node, then set its 'next' to None (deallocation by GC)."""
        from runtime.exceptions import MiniRuntimeError
        if self.head is None:
            raise MiniRuntimeError("pop from empty list", 0)
        if self.head.next is None:
            val = self.head.value
            self.head = None   # PL Concept: Dynamic Memory — no references remain; GC reclaims the node
            self._size -= 1
            return val
        current = self.head
        while current.next.next is not None:
            current = current.next   # PL Concept: Dynamic Data Structure — chase to second-to-last node
        val = current.next.value
        current.next = None   # PL Concept: Dynamic Memory — sever link; tail node becomes unreachable (GC candidate)
        self._size -= 1
        return val

    def get(self, index: int) -> MiniValue:
        """Return value at index; supports negative indexing."""
        from runtime.exceptions import MiniRuntimeError
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise MiniRuntimeError(
                f"List index {index} out of range (size={self._size})", 0
            )
        return self._node_at(index).value

    def set(self, index: int, value: MiniValue) -> None:
        """Overwrite value at index."""
        from runtime.exceptions import MiniRuntimeError
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise MiniRuntimeError(f"List index {index} out of range", 0)
        self._node_at(index).value = value

    def length(self) -> int:
        return self._size

    # ---- MiniValue interface ----

    def is_truthy(self) -> bool:
        return self._size > 0

    def to_display(self) -> str:
        items = ", ".join(v.to_display() for v in self._to_python_list())
        return f"[{items}]"

    def type_name(self) -> str:
        return "List"


# ---------------------------------------------------------------------------
# Callable types
# ---------------------------------------------------------------------------

class MiniFunction(MiniValue):
    """
    User-defined function / closure.

    PL Concept: Functions / Procedures — bundles parameter names and an AST body.
    PL Concept: Scope — captures the *defining* environment at creation time
    (closure semantics / lexical scoping).  When called, a child of this captured
    environment is created, not a child of the *calling* environment.
    PL Concept: Higher-order Functions — MiniFunction is a first-class value:
    it can be stored in variables, passed as arguments, and returned.
    """

    def __init__(self, name: Optional[str], params: list[str], body, closure: "Environment"):
        self.name: str = name or "<anonymous>"
        self.params: list[str] = params      # PL Concept: Functions — ordered list of formal parameter names
        self.body = body                      # AST Block node — executed on each call
        self.closure = closure               # PL Concept: Closures / Lexical Scoping — environment captured at definition time

    def is_truthy(self) -> bool:
        return True

    def to_display(self) -> str:
        return f"<fun {self.name}({', '.join(self.params)})>"

    def type_name(self) -> str:
        return "Function"


class MiniBuiltin(MiniValue):
    """
    A function implemented in Python, exposed to the mini language.

    PL Concept: Abstraction — built-ins and user functions share the same
    callable interface; the interpreter calls both through _call_value() without
    knowing which kind it has.
    PL Concept: Higher-order Functions — map / filter / reduce are built-ins
    that accept MiniFunction values as first-class arguments.
    """

    def __init__(self, name: str, fn):
        self.name = name
        self.fn = fn  # (args: list[MiniValue], line: int, interpreter) -> MiniValue

    def is_truthy(self) -> bool:
        return True

    def to_display(self) -> str:
        return f"<builtin {self.name}>"

    def type_name(self) -> str:
        return "Builtin"


# ---------------------------------------------------------------------------
# User-defined struct types
# ---------------------------------------------------------------------------

class MiniStructDef(MiniValue):
    """
    A struct type definition.  Acts as a callable constructor.

    PL Concept: User-defined Types — users declare named record types with
    named fields.  MiniStructDef stores the type schema; MiniObject stores
    an instance.
    """

    def __init__(self, name: str, fields: list[str]):
        self.name = name
        self.fields = fields

    def is_truthy(self) -> bool:
        return True

    def to_display(self) -> str:
        return f"<struct {self.name}>"

    def type_name(self) -> str:
        return "StructDef"


class MiniObject(MiniValue):
    """
    An instance of a user-defined struct.

    PL Concept: User-defined Types — holds a dict mapping field names to values.
    PL Concept: Dynamic Memory / Heap — the fields dict is heap-allocated and
    grows/shrinks at runtime.
    PL Concept: Encapsulation — field access is mediated by get_field/set_field
    which validate field names; raw dict is not exposed.
    """

    def __init__(self, struct_name: str, fields: dict[str, MiniValue]):
        self.struct_name = struct_name
        self.fields: dict[str, MiniValue] = fields

    def get_field(self, name: str) -> MiniValue:
        # PL Concept: Encapsulation — field access is mediated; callers cannot read
        # arbitrary dict keys. Unknown field names raise a descriptive error.
        from runtime.exceptions import MiniRuntimeError
        if name not in self.fields:
            raise MiniRuntimeError(
                f"Struct '{self.struct_name}' has no field '{name}'", 0
            )  # PL Concept: Type Safety — prevents access to non-existent fields
        return self.fields[name]   # PL Concept: Dynamic Memory — value lives in this heap-allocated dict

    def set_field(self, name: str, value: MiniValue) -> None:
        # PL Concept: Encapsulation — field mutation is mediated; only declared fields may be set
        from runtime.exceptions import MiniRuntimeError
        if name not in self.fields:
            raise MiniRuntimeError(
                f"Struct '{self.struct_name}' has no field '{name}'", 0
            )  # PL Concept: Type Safety — prevents silent creation of undeclared fields
        self.fields[name] = value   # PL Concept: Dynamic Memory — mutates the heap-allocated field dict

    def is_truthy(self) -> bool:
        return True

    def to_display(self) -> str:
        parts = ", ".join(f"{k}: {v.to_display()}" for k, v in self.fields.items())
        return f"{self.struct_name}({{{parts}}})"

    def type_name(self) -> str:
        return self.struct_name


# ---------------------------------------------------------------------------
# Control-flow signals (not user-visible values)
# ---------------------------------------------------------------------------

class ReturnSignal(Exception):
    """
    Raised by a return statement and caught at the function call boundary.
    PL Concept: Functions / Procedures — allows return to escape deeply nested
    blocks inside a function body without touching every intermediate frame.
    PL Concept: Exception Handling (internal mechanism) — reuses Python's own
    stack-unwinding machinery so we don't need a manual call-stack data structure.
    """

    def __init__(self, value: MiniValue):
        self.value = value   # PL Concept: Functions — the return value travels up via this field


class MiniThrown(Exception):
    """
    Carries a user-thrown value up the call stack until a try/catch intercepts it.
    PL Concept: Exception Handling — models the throw/catch mechanism of the mini
    language using Python's own exception propagation machinery.
    The key insight: Python raises this; Python unwinds; _exec_try_catch catches it.
    No manual unwinding loop needed.
    """

    def __init__(self, value: MiniValue, line: int):
        self.value = value   # PL Concept: Exception Handling — the thrown MiniValue (any type, even a struct)
        self.line = line     # PL Concept: Exception Handling — source line of the throw, for diagnostics
        super().__init__(value.to_display())

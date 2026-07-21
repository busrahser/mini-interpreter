"""
EXCEPTIONS MODULE
=================
PL Concept: Exception Handling — defines the full error hierarchy for every phase
of the interpreter.  Separating error types lets callers (and the REPL) handle
them at the right granularity without catching too broadly.

Hierarchy
---------
MiniError (base)
  ├─ ParseError       — grammar violation found by the parser
  └─ MiniRuntimeError — semantic/type error raised by the interpreter

MiniUserError         — an un-caught throw from user code (not a sub of MiniError
                         so the REPL can present it differently)

Each carries a source-line number so error messages point at real code.
"""


class MiniError(Exception):
    """Base class for all interpreter-internal errors."""

    def __init__(self, message: str, line: int = 0):
        self.message = message
        self.line = line
        super().__init__(self._format())

    def _format(self) -> str:
        prefix = f"[Line {self.line}] " if self.line else ""
        return f"{prefix}{type(self).__name__}: {self.message}"


class ParseError(MiniError):
    """Raised by the parser when the token stream violates the grammar."""


class MiniRuntimeError(MiniError):
    """Raised by the interpreter for runtime semantic errors (type mismatches,
    undefined variables, division by zero, index out of bounds, etc.)."""


class MiniUserError(Exception):
    """
    Wraps a user-thrown value that escaped all try/catch blocks.
    PL Concept: Exception Handling — shows that uncaught exceptions are still
    distinguishable from interpreter bugs.
    """

    def __init__(self, value, line: int = 0):
        self.value = value
        self.line = line
        msg = value.to_display() if hasattr(value, "to_display") else str(value)
        super().__init__(f"Uncaught throw: {msg}")

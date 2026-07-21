#!/usr/bin/env python3
"""
MAIN — Entry point for the Mini Interpreter.
=============================================
Wires the three pipeline stages together and exposes two ways to run Mini
source code:

    python main.py                 → interactive REPL
    python main.py path/to/file.mini → execute a script and exit

This file contains no language logic of its own — it only drives the
existing Lexer / Parser / Interpreter classes and formats their errors for
the terminal. See REPORT.md for the full pipeline design.
"""

from __future__ import annotations

import sys
from pathlib import Path

from lexer.lexer import Lexer, LexerError, TokenType
from parser.parser import Parser
from runtime.exceptions import ParseError, MiniRuntimeError, MiniUserError
from runtime.types import MiniThrown, MiniNull
from interpreter.interpreter import Interpreter

VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Shared error formatting
# ---------------------------------------------------------------------------

def _report_error(exc: Exception) -> None:
    """Print a user-facing error message for any known failure mode."""
    if isinstance(exc, (LexerError, ParseError, MiniRuntimeError)):
        print(f"{exc}", file=sys.stderr)
    elif isinstance(exc, MiniThrown):
        loc = f"[Line {exc.line}] " if exc.line else ""
        print(f"{loc}Uncaught throw: {exc.value.to_display()}", file=sys.stderr)
    elif isinstance(exc, MiniUserError):
        print(f"{exc}", file=sys.stderr)
    elif isinstance(exc, RecursionError):
        print("RuntimeError: maximum recursion depth exceeded", file=sys.stderr)
    else:
        print(f"InternalError: {type(exc).__name__}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# File runner
# ---------------------------------------------------------------------------

def run_file(path: str) -> int:
    """Execute a .mini source file. Returns a process exit code."""
    source = Path(path).read_text(encoding="utf-8")
    interpreter = Interpreter()
    try:
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        interpreter.run(program)
        return 0
    except (LexerError, ParseError, MiniRuntimeError, MiniThrown,
            MiniUserError, RecursionError) as exc:
        _report_error(exc)
        return 1


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def _brace_depth(tokens) -> int:
    """Count unclosed '{' so the REPL knows when a block is still open."""
    depth = 0
    for tok in tokens:
        if tok.type == TokenType.LBRACE:
            depth += 1
        elif tok.type == TokenType.RBRACE:
            depth -= 1
    return depth


def run_repl() -> int:
    """Interactive read-eval-print loop. One Interpreter instance persists
    across inputs so variables and functions stay defined between lines."""
    print(f"Mini Interpreter v{VERSION}  —  type 'exit' or Ctrl-D to quit")
    interpreter = Interpreter()
    buffer_lines: list[str] = []

    while True:
        prompt = "... " if buffer_lines else "mini> "
        try:
            line = input(prompt)
        except EOFError:
            print()
            return 0

        if not buffer_lines and line.strip() in ("exit", "quit"):
            return 0
        if not buffer_lines and not line.strip():
            continue

        buffer_lines.append(line)
        source = "\n".join(buffer_lines)

        # Try tokenizing what we have so far. An unterminated string usually
        # just means the statement is still being typed across lines.
        try:
            tokens = Lexer(source).tokenize()
        except LexerError as exc:
            if "Unterminated string" in exc.args[0]:
                continue
            _report_error(exc)
            buffer_lines = []
            continue

        # Still inside an open '{ ... }' block — keep collecting lines.
        if _brace_depth(tokens) > 0:
            continue

        try:
            program = Parser(tokens).parse()
            result = interpreter.run(program)
            if result is not None and not isinstance(result, MiniNull):
                print(result.to_display())
        except (ParseError, MiniRuntimeError, MiniThrown,
                MiniUserError, RecursionError) as exc:
            _report_error(exc)
        finally:
            buffer_lines = []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if len(argv) > 1:
        return run_file(argv[1])
    return run_repl()


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""
LEXER MODULE
============
PL Concept: Lexical Analysis — converts the raw source string into a flat
sequence of tokens.  This is stage 1 of the classic pipeline:

    Source text  →  [Lexer]  →  Token stream  →  [Parser]  →  AST  →  [Interpreter]

Each token is an atomic unit: a keyword, operator, literal, identifier, or
punctuation mark.  The lexer discards whitespace and comments so the parser
never has to deal with them.

PL Concept: Modular Decomposition — the Lexer class encapsulates all character-
level logic.  Its only public output is tokenize() → list[Token].

PL Concept: Abstraction — callers only see Token objects with a type and optional
value; they never manipulate raw characters.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenType(Enum):
    # ---- literals ----
    NUMBER     = auto()
    STRING     = auto()
    IDENTIFIER = auto()

    # ---- keywords ----
    LET    = auto()
    FUN    = auto()
    RETURN = auto()
    IF     = auto()
    ELSE   = auto()
    WHILE  = auto()
    TRUE   = auto()
    FALSE  = auto()
    NULL   = auto()
    TRY    = auto()
    CATCH  = auto()
    THROW  = auto()
    STRUCT = auto()
    NEW    = auto()
    AND    = auto()
    OR     = auto()
    NOT    = auto()

    # ---- two-character operators ----
    EQ  = auto()   # ==
    NEQ = auto()   # !=
    LTE = auto()   # <=
    GTE = auto()   # >=

    # ---- single-character operators ----
    ASSIGN  = auto()   # =
    PLUS    = auto()   # +
    MINUS   = auto()   # -
    STAR    = auto()   # *
    SLASH   = auto()   # /
    PERCENT = auto()   # %
    LT      = auto()   # <
    GT      = auto()   # >

    # ---- delimiters ----
    LPAREN   = auto()  # (
    RPAREN   = auto()  # )
    LBRACE   = auto()  # {
    RBRACE   = auto()  # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COMMA    = auto()
    DOT      = auto()
    SEMICOLON = auto()

    # ---- special ----
    EOF = auto()


# PL Concept: Type Design — each reserved word maps to its own TokenType variant
# so the parser can distinguish keywords from user identifiers without string comparison.
KEYWORDS: dict[str, TokenType] = {
    "let":    TokenType.LET,
    "fun":    TokenType.FUN,
    "return": TokenType.RETURN,
    "if":     TokenType.IF,
    "else":   TokenType.ELSE,
    "while":  TokenType.WHILE,
    "true":   TokenType.TRUE,
    "false":  TokenType.FALSE,
    "null":   TokenType.NULL,
    "try":    TokenType.TRY,
    "catch":  TokenType.CATCH,
    "throw":  TokenType.THROW,
    "struct": TokenType.STRUCT,
    "new":    TokenType.NEW,
    "and":    TokenType.AND,
    "or":     TokenType.OR,
    "not":    TokenType.NOT,
}


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """
    PL Concept: User-defined Type — Token is a product type (record) bundling
    a type tag, an optional literal value, and the source line for diagnostics.
    """
    type: TokenType
    value: object    # float for NUMBER, str for STRING/IDENTIFIER, None otherwise
    line: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Lexer error
# ---------------------------------------------------------------------------

class LexerError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"[Line {line}] LexerError: {message}")
        self.line = line


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Single-pass lexer / scanner.

    PL Concept: Encapsulation — all character-level state (source, position,
    line counter) is private.  The public interface is one method: tokenize().

    PL Concept: Procedural Decomposition — each token category (_number,
    _string, _identifier) is handled by a dedicated method, keeping _scan_token
    as a clean dispatch table.
    """

    def __init__(self, source: str):
        self._source = source   # PL Concept: Encapsulation — raw source is private
        self._pos = 0           # PL Concept: Encapsulation — position cursor is private state
        self._line = 1          # PL Concept: Encapsulation — line counter for diagnostics only
        self._tokens: list[Token] = []  # accumulator; never accessed by callers directly

    # ---- character primitives ----

    def _current(self) -> str:
        return self._source[self._pos] if self._pos < len(self._source) else ""

    def _peek(self, offset: int = 1) -> str:
        idx = self._pos + offset
        return self._source[idx] if idx < len(self._source) else ""

    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1   # PL Concept: Lexical Analysis — track source lines for error reporting
        return ch

    def _match(self, expected: str) -> bool:
        if self._current() == expected:
            self._advance()
            return True
        return False

    def _add(self, ttype: TokenType, value: object = None) -> None:
        self._tokens.append(Token(ttype, value, self._line))

    # ---- public entry point ----

    def tokenize(self) -> list[Token]:
        """
        Scan the entire source and return a token list ending with EOF.
        PL Concept: Lexical Analysis — the main loop reads one character at a
        time and classifies it, building the token stream.
        """
        while self._pos < len(self._source):
            self._scan_token()   # PL Concept: Lexical Analysis — classify one token per iteration
        self._add(TokenType.EOF)  # PL Concept: Lexical Analysis — sentinel marks end of input
        return self._tokens       # PL Concept: Abstraction — callers receive only the finished list

    # ---- token scanner ----

    def _scan_token(self) -> None:
        ch = self._advance()

        # Skip whitespace (newlines are not significant in this language)
        if ch in (" ", "\t", "\r", "\n"):
            return

        # Single-line comments — '#' to end of line
        if ch == "#":
            while self._current() not in ("\n", ""):
                self._advance()
            return

        # Numeric literals
        if ch.isdigit():
            self._number(ch)
            return

        # String literals
        if ch == '"':
            self._string()
            return

        # Identifiers and keywords
        if ch.isalpha() or ch == "_":
            self._identifier(ch)
            return

        # Two-character operators
        if ch == "=":
            self._add(TokenType.EQ if self._match("=") else TokenType.ASSIGN)
        elif ch == "!":
            if self._match("="):
                self._add(TokenType.NEQ)
            else:
                raise LexerError("Expected '=' after '!'", self._line)
        elif ch == "<":
            self._add(TokenType.LTE if self._match("=") else TokenType.LT)
        elif ch == ">":
            self._add(TokenType.GTE if self._match("=") else TokenType.GT)

        # Single-character tokens
        elif ch == "+":  self._add(TokenType.PLUS)
        elif ch == "-":  self._add(TokenType.MINUS)
        elif ch == "*":  self._add(TokenType.STAR)
        elif ch == "/":  self._add(TokenType.SLASH)
        elif ch == "%":  self._add(TokenType.PERCENT)
        elif ch == "(":  self._add(TokenType.LPAREN)
        elif ch == ")":  self._add(TokenType.RPAREN)
        elif ch == "{":  self._add(TokenType.LBRACE)
        elif ch == "}":  self._add(TokenType.RBRACE)
        elif ch == "[":  self._add(TokenType.LBRACKET)
        elif ch == "]":  self._add(TokenType.RBRACKET)
        elif ch == ",":  self._add(TokenType.COMMA)
        elif ch == ".":  self._add(TokenType.DOT)
        elif ch == ";":  self._add(TokenType.SEMICOLON)
        else:
            raise LexerError(f"Unexpected character: {ch!r}", self._line)

    # ---- token-specific scanners ----

    def _number(self, first: str) -> None:
        """Scan an integer or floating-point literal.
        PL Concept: Type Design — both integers and floats become a single NUMBER token;
        the unified Number type avoids int/float distinctions at the language level."""
        digits = [first]
        while self._current().isdigit():
            digits.append(self._advance())
        # Optional fractional part
        if self._current() == "." and self._peek().isdigit():
            digits.append(self._advance())   # consume '.'
            while self._current().isdigit():
                digits.append(self._advance())
        self._add(TokenType.NUMBER, float("".join(digits)))  # PL Concept: Type Design — stored as float internally

    def _string(self) -> None:
        """Scan a double-quoted string with \\n \\t \\\\ \\\" escapes."""
        chars: list[str] = []
        while self._current() not in ('"', ""):
            ch = self._advance()
            if ch == "\\":
                esc = self._advance()
                ch = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(esc, esc)
            chars.append(ch)
        if self._current() == "":
            raise LexerError("Unterminated string literal", self._line)
        self._advance()   # closing "
        self._add(TokenType.STRING, "".join(chars))

    def _identifier(self, first: str) -> None:
        """Scan an identifier; classify as keyword if it matches KEYWORDS.
        PL Concept: Lexical Analysis — keyword detection is done here, not in the parser,
        keeping the parser free of character-level concerns (separation of concerns)."""
        chars = [first]
        while self._current().isalnum() or self._current() == "_":
            chars.append(self._advance())
        name = "".join(chars)
        ttype = KEYWORDS.get(name, TokenType.IDENTIFIER)  # PL Concept: Type Design — reserved words get dedicated token types
        # Store the lexeme only for identifiers; keywords carry no extra value
        self._add(ttype, name if ttype == TokenType.IDENTIFIER else None)

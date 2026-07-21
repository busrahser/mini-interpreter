"""
PARSER MODULE
=============
PL Concept: Syntax Analysis — transforms the flat token stream from the Lexer
into a hierarchical Abstract Syntax Tree (AST).

Implementation: hand-written recursive-descent parser.  Each grammar production
rule maps directly to one method.  The method hierarchy implements operator
precedence without a separate precedence table.

Operator precedence (lowest → highest)
---------------------------------------
  1. assignment          (right-associative)
  2. or
  3. and
  4. not                 (prefix)
  5. equality   == !=
  6. comparison < > <= >=
  7. addition   + -
  8. multiplication * / %
  9. unary      - not    (prefix)
 10. call / member / index  (left-associative postfix)
 11. primary   literals · identifier · ( expr ) · [ list ] · fun lambda · new

PL Concept: Modular Decomposition — every grammar production is its own method,
each with a single responsibility.

PL Concept: Encapsulation — the token stream is fully private.  The public
interface is one method: parse() → Program.
"""

from __future__ import annotations
from typing import Optional, Any

from lexer.lexer import Token, TokenType
from parser.ast_nodes import (
    Program, LetStatement, AssignStatement, FunctionDecl,
    ReturnStatement, IfStatement, WhileStatement, TryCatchStatement,
    ThrowStatement, StructDecl, Block, ExprStatement,
    BinaryExpr, UnaryExpr, CallExpr, IndexExpr, MemberExpr,
    ListExpr, LambdaExpr, NewExpr,
    NumberLiteral, StringLiteral, BoolLiteral, NullLiteral, Identifier,
)
from runtime.exceptions import ParseError


class Parser:
    """
    Recursive-descent parser.

    PL Concept: Abstraction — callers only call parse(); the internal token-
    navigation helpers (_current, _advance, _expect, …) are private.

    PL Concept: Scope (analogy) — the parser maintains a position pointer into
    the token list, analogous to how the evaluator maintains an environment of
    variable bindings.  Both are "cursors" over a structure.
    """

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    # ---- token navigation helpers ----

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset: int = 1) -> Token:
        idx = self._pos + offset
        return self._tokens[idx] if idx < len(self._tokens) else self._tokens[-1]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._current().type in types

    def _match(self, *types: TokenType) -> bool:
        if self._check(*types):
            self._advance()
            return True
        return False

    def _expect(self, ttype: TokenType, msg: str = "") -> Token:
        if self._check(ttype):
            return self._advance()
        tok = self._current()
        raise ParseError(
            msg or f"Expected {ttype.name}, got {tok.type.name} ({tok.value!r})",
            tok.line,
        )

    def _line(self) -> int:
        return self._current().line

    # ---- public entry point ----

    def parse(self) -> Program:
        """Parse the token stream into a Program node."""
        body: list = []
        while not self._check(TokenType.EOF):
            stmt = self._statement()
            if stmt is not None:
                body.append(stmt)
        return Program(body=body, line=0)

    # ---- statement parsers ----

    def _statement(self) -> Optional[Any]:
        # Skip bare semicolons
        if self._match(TokenType.SEMICOLON):
            return None

        if self._check(TokenType.LET):
            return self._let_stmt()
        if self._check(TokenType.FUN):
            return self._fun_decl()
        if self._check(TokenType.RETURN):
            return self._return_stmt()
        if self._check(TokenType.IF):
            return self._if_stmt()
        if self._check(TokenType.WHILE):
            return self._while_stmt()
        if self._check(TokenType.TRY):
            return self._try_catch_stmt()
        if self._check(TokenType.THROW):
            return self._throw_stmt()
        if self._check(TokenType.STRUCT):
            return self._struct_decl()
        if self._check(TokenType.LBRACE):
            return self._block()

        return self._expr_statement()

    def _let_stmt(self) -> LetStatement:
        line = self._line()
        self._advance()   # consume 'let'
        name = self._expect(TokenType.IDENTIFIER, "Expected variable name after 'let'").value
        self._expect(TokenType.ASSIGN, "Expected '=' after variable name")
        value = self._expression()
        self._match(TokenType.SEMICOLON)
        return LetStatement(name=name, value=value, line=line)

    def _fun_decl(self) -> FunctionDecl:
        line = self._line()
        self._advance()   # consume 'fun'
        name = self._expect(TokenType.IDENTIFIER, "Expected function name after 'fun'").value
        params = self._param_list()
        body = self._block()
        return FunctionDecl(name=name, params=params, body=body, line=line)

    def _param_list(self) -> list[str]:
        self._expect(TokenType.LPAREN, "Expected '(' after function name")
        params: list[str] = []
        if not self._check(TokenType.RPAREN):
            params.append(
                self._expect(TokenType.IDENTIFIER, "Expected parameter name").value
            )
            while self._match(TokenType.COMMA):
                params.append(
                    self._expect(TokenType.IDENTIFIER, "Expected parameter name").value
                )
        self._expect(TokenType.RPAREN, "Expected ')' after parameters")
        return params

    def _return_stmt(self) -> ReturnStatement:
        line = self._line()
        self._advance()   # consume 'return'
        value = None
        # A return with no value ends at '}', ';', or EOF
        if not self._check(TokenType.RBRACE, TokenType.SEMICOLON, TokenType.EOF):
            value = self._expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStatement(value=value, line=line)

    def _if_stmt(self) -> IfStatement:
        line = self._line()
        self._advance()   # consume 'if'
        condition = self._expression()
        then_branch = self._block()
        else_branch = None
        if self._match(TokenType.ELSE):
            if self._check(TokenType.IF):
                else_branch = self._if_stmt()   # else-if chain
            else:
                else_branch = self._block()
        return IfStatement(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=line,
        )

    def _while_stmt(self) -> WhileStatement:
        line = self._line()
        self._advance()   # consume 'while'
        condition = self._expression()
        body = self._block()
        return WhileStatement(condition=condition, body=body, line=line)

    def _try_catch_stmt(self) -> TryCatchStatement:
        line = self._line()
        self._advance()   # consume 'try'
        body = self._block()
        self._expect(TokenType.CATCH, "Expected 'catch' after try block")
        self._expect(TokenType.LPAREN, "Expected '(' after 'catch'")
        error_name = self._expect(
            TokenType.IDENTIFIER, "Expected error variable name"
        ).value
        self._expect(TokenType.RPAREN, "Expected ')' after error variable")
        handler = self._block()
        return TryCatchStatement(
            body=body, error_name=error_name, handler=handler, line=line
        )

    def _throw_stmt(self) -> ThrowStatement:
        line = self._line()
        self._advance()   # consume 'throw'
        value = self._expression()
        self._match(TokenType.SEMICOLON)
        return ThrowStatement(value=value, line=line)

    def _struct_decl(self) -> StructDecl:
        line = self._line()
        self._advance()   # consume 'struct'
        name = self._expect(TokenType.IDENTIFIER, "Expected struct name").value
        self._expect(TokenType.LBRACE, "Expected '{' after struct name")
        fields: list[str] = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            fields.append(
                self._expect(TokenType.IDENTIFIER, "Expected field name").value
            )
            self._match(TokenType.COMMA)
        self._expect(TokenType.RBRACE, "Expected '}' to close struct body")
        return StructDecl(name=name, fields=fields, line=line)

    def _block(self) -> Block:
        line = self._line()
        self._expect(TokenType.LBRACE, "Expected '{'")
        stmts: list = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            stmt = self._statement()
            if stmt is not None:
                stmts.append(stmt)
        self._expect(TokenType.RBRACE, "Expected '}'")
        return Block(statements=stmts, line=line)

    def _expr_statement(self) -> ExprStatement:
        line = self._line()
        expr = self._expression()
        self._match(TokenType.SEMICOLON)
        return ExprStatement(expr=expr, line=line)

    # ---- expression parsers (precedence climbing) ----

    def _expression(self) -> Any:
        return self._assignment()

    def _assignment(self) -> Any:
        """Right-associative; target must be Identifier / IndexExpr / MemberExpr.
        PL Concept: Scope — assignment mutates an existing binding; 'let' declares a new one.
        The distinction is enforced here: only valid l-values are accepted as targets."""
        line = self._line()
        left = self._or_expr()
        if self._match(TokenType.ASSIGN):
            # PL Concept: Type Safety — validate l-value before creating the AST node
            if not isinstance(left, (Identifier, IndexExpr, MemberExpr)):
                raise ParseError("Invalid assignment target", line)
            value = self._assignment()   # PL Concept: right-associative — a = b = c parses as a = (b = c)
            return AssignStatement(target=left, value=value, line=line)
        return left

    def _or_expr(self) -> Any:
        # PL Concept: Operator Precedence — 'or' binds more loosely than 'and'
        # PL Concept: Short-circuit Evaluation — BinaryExpr("or") will skip right side if left is truthy
        line = self._line()
        left = self._and_expr()
        while self._match(TokenType.OR):
            right = self._and_expr()
            left = BinaryExpr(left=left, op="or", right=right, line=line)
        return left

    def _and_expr(self) -> Any:
        # PL Concept: Operator Precedence — 'and' binds more tightly than 'or'
        # PL Concept: Short-circuit Evaluation — right side skipped if left is falsy
        line = self._line()
        left = self._not_expr()
        while self._match(TokenType.AND):
            right = self._not_expr()
            left = BinaryExpr(left=left, op="and", right=right, line=line)
        return left

    def _not_expr(self) -> Any:
        # PL Concept: Operator Precedence — prefix 'not' binds tighter than 'and'/'or'
        line = self._line()
        if self._match(TokenType.NOT):
            return UnaryExpr(op="not", operand=self._not_expr(), line=line)
        return self._equality()

    def _equality(self) -> Any:
        line = self._line()
        left = self._comparison()
        while self._check(TokenType.EQ, TokenType.NEQ):
            op = "==" if self._advance().type == TokenType.EQ else "!="
            right = self._comparison()
            left = BinaryExpr(left=left, op=op, right=right, line=line)
        return left

    def _comparison(self) -> Any:
        line = self._line()
        left = self._addition()
        _ops = {
            TokenType.LT:  "<",
            TokenType.GT:  ">",
            TokenType.LTE: "<=",
            TokenType.GTE: ">=",
        }
        while self._check(*_ops):
            op = _ops[self._advance().type]
            right = self._addition()
            left = BinaryExpr(left=left, op=op, right=right, line=line)
        return left

    def _addition(self) -> Any:
        line = self._line()
        left = self._multiplication()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op = "+" if self._advance().type == TokenType.PLUS else "-"
            right = self._multiplication()
            left = BinaryExpr(left=left, op=op, right=right, line=line)
        return left

    def _multiplication(self) -> Any:
        line = self._line()
        left = self._unary()
        _ops = {TokenType.STAR: "*", TokenType.SLASH: "/", TokenType.PERCENT: "%"}
        while self._check(*_ops):
            op = _ops[self._advance().type]
            right = self._unary()
            left = BinaryExpr(left=left, op=op, right=right, line=line)
        return left

    def _unary(self) -> Any:
        line = self._line()
        if self._match(TokenType.MINUS):
            return UnaryExpr(op="-", operand=self._unary(), line=line)
        if self._match(TokenType.NOT):
            return UnaryExpr(op="not", operand=self._unary(), line=line)
        return self._call()

    def _call(self) -> Any:
        """Left-associative postfix: call, member access, index — all chainable.
        PL Concept: Functions / Procedures — call expressions are left-associative,
        so f(1)(2) and obj.method(x)[0] all parse correctly without special cases."""
        line = self._line()
        expr = self._primary()
        while True:
            if self._match(TokenType.LPAREN):
                args = self._arg_list()
                self._expect(TokenType.RPAREN, "Expected ')' after arguments")
                expr = CallExpr(callee=expr, args=args, line=line)  # PL Concept: Functions — wraps callee + args
            elif self._match(TokenType.DOT):
                member = self._expect(TokenType.IDENTIFIER, "Expected member name").value
                expr = MemberExpr(obj=expr, member=member, line=line)  # PL Concept: Encapsulation — field access syntax
            elif self._match(TokenType.LBRACKET):
                index = self._expression()
                self._expect(TokenType.RBRACKET, "Expected ']' after index")
                expr = IndexExpr(obj=expr, index=index, line=line)    # PL Concept: Dynamic Data Structures — list indexing
            else:
                break
        return expr

    def _arg_list(self) -> list:
        args: list = []
        if not self._check(TokenType.RPAREN):
            args.append(self._expression())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RPAREN):   # trailing comma allowed
                    break
                args.append(self._expression())
        return args

    def _primary(self) -> Any:
        """Lowest-level expression: literal, identifier, grouping, lambda, list, new."""
        line = self._line()
        tok = self._current()

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLiteral(value=tok.value, line=line)

        if tok.type == TokenType.STRING:
            self._advance()
            return StringLiteral(value=tok.value, line=line)

        if tok.type == TokenType.TRUE:
            self._advance()
            return BoolLiteral(value=True, line=line)

        if tok.type == TokenType.FALSE:
            self._advance()
            return BoolLiteral(value=False, line=line)

        if tok.type == TokenType.NULL:
            self._advance()
            return NullLiteral(line=line)

        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(name=tok.value, line=line)

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._expression()
            self._expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        if tok.type == TokenType.LBRACKET:
            return self._list_literal()

        if tok.type == TokenType.FUN:
            return self._lambda()

        if tok.type == TokenType.NEW:
            return self._new_expr()

        raise ParseError(
            f"Unexpected token: {tok.type.name} ({tok.value!r})", line
        )

    def _list_literal(self) -> ListExpr:
        line = self._line()
        self._expect(TokenType.LBRACKET)
        elements: list = []
        if not self._check(TokenType.RBRACKET):
            elements.append(self._expression())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RBRACKET):
                    break
                elements.append(self._expression())
        self._expect(TokenType.RBRACKET, "Expected ']' to close list literal")
        return ListExpr(elements=elements, line=line)

    def _lambda(self) -> LambdaExpr:
        """fun(<params>) { <body> }  — anonymous function expression.
        PL Concept: Higher-order Functions — produces a first-class function value
        (closure) that can be stored, passed as an argument, or returned.
        PL Concept: Scope — the resulting LambdaExpr captures the current environment
        at evaluation time (in _eval_lambda), not at parse time."""
        line = self._line()
        self._advance()   # consume 'fun'
        params = self._param_list()   # PL Concept: Functions — parameter names for the new scope
        body = self._block()           # PL Concept: Scope — body executes in a child of the closure env
        return LambdaExpr(params=params, body=body, line=line)

    def _new_expr(self) -> NewExpr:
        """new <StructName>(<args>)"""
        line = self._line()
        self._advance()   # consume 'new'
        name = self._expect(TokenType.IDENTIFIER, "Expected struct name after 'new'").value
        self._expect(TokenType.LPAREN, "Expected '(' after struct name")
        args = self._arg_list()
        self._expect(TokenType.RPAREN, "Expected ')'")
        return NewExpr(struct_name=name, args=args, line=line)

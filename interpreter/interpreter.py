"""
INTERPRETER MODULE
==================
PL Concept: Tree-walking Evaluation — stage 3 of the pipeline.  The interpreter
visits each AST node and directly executes it without a separate compilation step.

PL Concept: Functions / Procedures — function declarations capture the current
environment as a closure.  Calling a function creates a child scope, binds
parameters, executes the body, and catches ReturnSignal to obtain the value.

PL Concept: Scope — each function call extends the *closure* environment (lexical
scoping), not the call-site environment.  Block-level scopes (if/while) extend
the enclosing scope.

PL Concept: Recursion (Elective) — recursive calls work naturally because every
call creates its own Environment frame; Python's call stack tracks the depth.
Mutual recursion also works because all names are looked up dynamically.

PL Concept: Exception Handling (Elective) — try/catch blocks catch MiniThrown.
Throw statements raise it.  ReturnSignal is an internal signal that unwinds
nested blocks to the nearest function-call boundary.

PL Concept: Higher-order Functions (Elective) — MiniFunction is a first-class
value.  _eval_lambda() creates anonymous closures; _call_value() dispatches both
user-defined and built-in functions uniformly.

PL Concept: Type Safety — _require_number() guards all arithmetic operators.
Assignment targets are validated at the parser level; struct field access is
validated in MiniObject.

PL Concept: Dynamic Memory / Heap Usage — every new Environment, MiniObject,
MiniList, MiniFunction is heap-allocated; Python's GC manages lifetimes.
"""

from __future__ import annotations
from typing import Optional

from parser.ast_nodes import (
    Program, LetStatement, AssignStatement, FunctionDecl,
    ReturnStatement, IfStatement, WhileStatement, TryCatchStatement,
    ThrowStatement, StructDecl, Block, ExprStatement,
    BinaryExpr, UnaryExpr, CallExpr, IndexExpr, MemberExpr,
    ListExpr, LambdaExpr, NewExpr,
    NumberLiteral, StringLiteral, BoolLiteral, NullLiteral, Identifier,
)
from runtime.types import (
    MiniValue, MiniNumber, MiniString, MiniBool, MiniNull,
    MiniList, MiniFunction, MiniBuiltin, MiniStructDef, MiniObject,
    ReturnSignal, MiniThrown,
)
from runtime.exceptions import MiniRuntimeError, MiniUserError
from interpreter.environment import Environment
from interpreter.builtins import make_builtins


class Interpreter:
    """
    Tree-walking interpreter.

    PL Concept: Abstraction & Encapsulation — external callers use run() or
    eval_expr().  All dispatch, scope management, and control-flow signalling
    is hidden behind these two entry points.
    """

    def __init__(self):
        # The root of the scope chain — lives for the entire interpreter session
        self.global_env = Environment(name="<global>")
        self._load_builtins()

    def _load_builtins(self) -> None:
        for name, builtin in make_builtins().items():
            self.global_env.define(name, builtin)

    # ---- public interface ----

    def run(self, program: Program) -> Optional[MiniValue]:
        """Execute a full program in the global scope.  Returns the last value."""
        result: Optional[MiniValue] = None
        for stmt in program.body:
            result = self._exec(stmt, self.global_env)
        return result

    def eval_expr(self, node: object, env: Optional[Environment] = None) -> MiniValue:
        """Evaluate a single expression (used by the REPL)."""
        return self._eval(node, env or self.global_env)

    # ---- statement dispatch ----

    def _exec(self, node: object, env: Environment) -> Optional[MiniValue]:
        if isinstance(node, LetStatement):        return self._exec_let(node, env)
        if isinstance(node, AssignStatement):     return self._exec_assign(node, env)
        if isinstance(node, FunctionDecl):        return self._exec_fun_decl(node, env)
        if isinstance(node, ReturnStatement):     return self._exec_return(node, env)
        if isinstance(node, IfStatement):         return self._exec_if(node, env)
        if isinstance(node, WhileStatement):      return self._exec_while(node, env)
        if isinstance(node, TryCatchStatement):   return self._exec_try_catch(node, env)
        if isinstance(node, ThrowStatement):      return self._exec_throw(node, env)
        if isinstance(node, StructDecl):          return self._exec_struct_decl(node, env)
        if isinstance(node, Block):               return self._exec_block(node, env)
        if isinstance(node, ExprStatement):       return self._eval(node.expr, env)
        raise MiniRuntimeError(f"Unknown node type: {type(node).__name__}", node.line)

    # ---- statement handlers ----

    def _exec_let(self, node: LetStatement, env: Environment) -> MiniNull:
        # PL Concept: Variable Declaration — evaluate the initialiser, then create a
        # new binding in the current scope frame (env.define always writes here, never parent)
        env.define(node.name, self._eval(node.value, env))
        return MiniNull()

    def _exec_assign(self, node: AssignStatement, env: Environment) -> MiniValue:
        value = self._eval(node.value, env)
        target = node.target

        if isinstance(target, Identifier):
            # PL Concept: Scope — walks the chain to find the frame that owns the binding
            env.assign(target.name, value, target.line)

        elif isinstance(target, IndexExpr):
            obj = self._eval(target.obj, env)
            idx = self._eval(target.index, env)
            if not isinstance(obj, MiniList):
                raise MiniRuntimeError(f"Cannot index-assign into {obj.type_name()}", target.line)
            if not isinstance(idx, MiniNumber):
                raise MiniRuntimeError("List index must be a Number", target.line)  # PL Concept: Type Safety
            obj.set(int(idx.value), value)   # PL Concept: Dynamic Data Structures — pointer-chase to node, overwrite value

        elif isinstance(target, MemberExpr):
            obj = self._eval(target.obj, env)
            if not isinstance(obj, MiniObject):
                raise MiniRuntimeError(
                    f"Cannot set member on {obj.type_name()}", target.line
                )  # PL Concept: Type Safety — only struct instances have mutable fields
            obj.set_field(target.member, value)  # PL Concept: Encapsulation — field update mediated by MiniObject

        return value

    def _exec_fun_decl(self, node: FunctionDecl, env: Environment) -> MiniNull:
        """
        PL Concept: Closure — env captured here is the *defining* environment.
        When the function is later called, a child of this captured env is used,
        implementing lexical scoping.
        """
        fn = MiniFunction(name=node.name, params=node.params, body=node.body, closure=env)
        env.define(node.name, fn)
        return MiniNull()

    def _exec_return(self, node: ReturnStatement, env: Environment) -> None:
        """Raise ReturnSignal to unwind back to the enclosing function call."""
        value = self._eval(node.value, env) if node.value else MiniNull()
        raise ReturnSignal(value)

    def _exec_if(self, node: IfStatement, env: Environment) -> MiniValue:
        cond = self._eval(node.condition, env)
        if cond.is_truthy():
            # PL Concept: Scope — child env confines 'let' declarations inside this branch
            return self._exec_block(node.then_branch, env.child("<if-then>"))
        if node.else_branch is not None:
            if isinstance(node.else_branch, Block):
                # PL Concept: Scope — else branch also gets its own isolated child env
                return self._exec_block(node.else_branch, env.child("<if-else>"))
            return self._exec(node.else_branch, env)   # else-if chain: no extra env wrapper
        return MiniNull()

    def _exec_while(self, node: WhileStatement, env: Environment) -> MiniNull:
        while self._eval(node.condition, env).is_truthy():
            # PL Concept: Scope — fresh child env per iteration; 'let x' inside the body
            # does NOT persist to the next iteration (variable lifetime = one loop body)
            # PL Concept: Exception Handling — ReturnSignal must escape so 'return' inside
            # a loop still exits the enclosing function correctly
            try:
                self._exec_block(node.body, env.child("<while>"))
            except ReturnSignal:
                raise   # PL Concept: Functions — propagate return out of the loop to the function call boundary
        return MiniNull()

    def _exec_try_catch(self, node: TryCatchStatement, env: Environment) -> MiniNull:
        """
        PL Concept: Exception Handling — try the body; on MiniThrown bind the
        thrown value to error_name and execute the handler.
        """
        try:
            self._exec_block(node.body, env.child("<try>"))   # PL Concept: Exception Handling — body runs normally
        except MiniThrown as exc:
            # PL Concept: Exception Handling — MiniThrown propagated up by Python's own stack unwinding
            handler_env = env.child("<catch>")              # PL Concept: Scope — catch gets its own isolated frame
            handler_env.define(node.error_name, exc.value)  # PL Concept: Scope — thrown value bound to catch variable
            self._exec_block(node.handler, handler_env)
        return MiniNull()

    def _exec_throw(self, node: ThrowStatement, env: Environment) -> None:
        """PL Concept: Exception Handling — raise a user value as an exception."""
        raise MiniThrown(self._eval(node.value, env), node.line)

    def _exec_struct_decl(self, node: StructDecl, env: Environment) -> MiniNull:
        """PL Concept: User-defined Types — register a struct type definition."""
        env.define(node.name, MiniStructDef(name=node.name, fields=node.fields))
        return MiniNull()

    def _exec_block(self, node: Block, env: Environment) -> MiniValue:
        result: MiniValue = MiniNull()
        for stmt in node.statements:
            r = self._exec(stmt, env)
            if r is not None:
                result = r
        return result

    # ---- expression dispatch ----

    def _eval(self, node: object, env: Environment) -> MiniValue:
        # PL Concept: Tree-walking Evaluation — each isinstance check is one node type;
        # the tree structure drives execution order (no explicit stack management needed)
        if isinstance(node, NumberLiteral):  return MiniNumber(node.value)   # PL Concept: Type Design — literal → runtime value
        if isinstance(node, StringLiteral):  return MiniString(node.value)
        if isinstance(node, BoolLiteral):    return MiniBool(node.value)
        if isinstance(node, NullLiteral):    return MiniNull()
        if isinstance(node, Identifier):     return env.get(node.name, node.line)  # PL Concept: Scope — resolve name in chain
        if isinstance(node, BinaryExpr):     return self._eval_binary(node, env)
        if isinstance(node, UnaryExpr):      return self._eval_unary(node, env)
        if isinstance(node, CallExpr):       return self._eval_call(node, env)
        if isinstance(node, IndexExpr):      return self._eval_index(node, env)
        if isinstance(node, MemberExpr):     return self._eval_member(node, env)
        if isinstance(node, ListExpr):       return self._eval_list(node, env)
        if isinstance(node, LambdaExpr):     return self._eval_lambda(node, env)
        if isinstance(node, NewExpr):        return self._eval_new(node, env)
        # AssignStatement can appear as an expression (returned value)
        if isinstance(node, AssignStatement): return self._exec_assign(node, env)
        raise MiniRuntimeError(f"Unknown expression node: {type(node).__name__}", node.line)

    # ---- binary and unary operators ----

    def _eval_binary(self, node: BinaryExpr, env: Environment) -> MiniValue:
        # PL Concept: Short-circuit Evaluation — 'and'/'or' avoid evaluating the right
        # operand when the result is already determined by the left (side-effect safety)
        if node.op == "and":
            left = self._eval(node.left, env)
            return left if not left.is_truthy() else self._eval(node.right, env)  # PL Concept: Short-circuit — skip right if left is falsy
        if node.op == "or":
            left = self._eval(node.left, env)
            return left if left.is_truthy() else self._eval(node.right, env)      # PL Concept: Short-circuit — skip right if left is truthy

        left  = self._eval(node.left,  env)
        right = self._eval(node.right, env)
        op    = node.op
        line  = node.line

        # PL Concept: Type Safety — equality is type-aware: Number(3) != Bool(true) even though 3 is truthy
        if op == "==": return MiniBool(left == right)
        if op == "!=": return MiniBool(left != right)

        # Arithmetic & string concatenation
        if op == "+":
            if isinstance(left, MiniString):
                return MiniString(left.value + right.to_display())
            if isinstance(right, MiniString):
                return MiniString(left.to_display() + right.value)
            if isinstance(left, MiniList) and isinstance(right, MiniList):
                return MiniList(left._to_python_list() + right._to_python_list())
            return MiniNumber(self._req_num(left, op, line) + self._req_num(right, op, line))

        if op == "-":
            return MiniNumber(self._req_num(left, op, line) - self._req_num(right, op, line))
        if op == "*":
            return MiniNumber(self._req_num(left, op, line) * self._req_num(right, op, line))
        if op == "/":
            r = self._req_num(right, op, line)
            if r == 0:
                raise MiniRuntimeError("Division by zero", line)
            return MiniNumber(self._req_num(left, op, line) / r)
        if op == "%":
            r = self._req_num(right, op, line)
            if r == 0:
                raise MiniRuntimeError("Modulo by zero", line)
            return MiniNumber(self._req_num(left, op, line) % r)

        # Comparison
        l_num = self._req_num(left, op, line)
        r_num = self._req_num(right, op, line)
        if op == "<":  return MiniBool(l_num < r_num)
        if op == ">":  return MiniBool(l_num > r_num)
        if op == "<=": return MiniBool(l_num <= r_num)
        if op == ">=": return MiniBool(l_num >= r_num)

        raise MiniRuntimeError(f"Unknown binary operator: {op!r}", line)

    def _eval_unary(self, node: UnaryExpr, env: Environment) -> MiniValue:
        operand = self._eval(node.operand, env)
        if node.op == "-":
            return MiniNumber(-self._req_num(operand, "unary -", node.line))
        if node.op == "not":
            return MiniBool(not operand.is_truthy())
        raise MiniRuntimeError(f"Unknown unary operator: {node.op!r}", node.line)

    def _req_num(self, val: MiniValue, op: str, line: int) -> float:
        """
        PL Concept: Type Safety — enforce that arithmetic operands are Numbers.
        Raises a descriptive error rather than crashing with an AttributeError.
        """
        if isinstance(val, MiniNumber):
            return val.value
        raise MiniRuntimeError(
            f"Operator '{op}' requires a Number, got {val.type_name()}", line
        )

    # ---- call expression ----

    def _eval_call(self, node: CallExpr, env: Environment) -> MiniValue:
        """
        PL Concept: Functions / Procedures — resolve callee, evaluate arguments,
        dispatch to the appropriate call handler.
        """
        # Method-call syntax:  obj.method(args)
        if isinstance(node.callee, MemberExpr):
            return self._eval_method_call(node, env)

        callee = self._eval(node.callee, env)
        args   = [self._eval(a, env) for a in node.args]
        return self._call_value(callee, args, node.line)

    def _call_value(self, callee: MiniValue, args: list[MiniValue], line: int) -> MiniValue:
        # PL Concept: Abstraction — single dispatch point for all callable types;
        # callers don't distinguish built-ins from user functions from struct constructors
        if isinstance(callee, MiniBuiltin):
            return callee.fn(args, line, self)              # PL Concept: Abstraction — Python callable behind uniform interface
        if isinstance(callee, MiniFunction):
            return self._call_mini_function(callee, args, line)  # PL Concept: Scope — creates child of closure env
        if isinstance(callee, MiniStructDef):
            return self._construct_struct(callee, args, line)    # PL Concept: Dynamic Memory — allocates new MiniObject
        raise MiniRuntimeError(f"'{callee.to_display()}' is not callable", line)  # PL Concept: Type Safety

    def _call_mini_function(
        self, fn: MiniFunction, args: list[MiniValue], line: int
    ) -> MiniValue:
        """
        PL Concept: Scope — new scope is rooted in the closure, not the call site.
        PL Concept: Recursion — each recursive call creates an independent frame;
        Python's call stack tracks the depth automatically.
        PL Concept: Variable Lifetime — call_env exists only for this call.
        """
        if len(args) != len(fn.params):
            raise MiniRuntimeError(
                f"'{fn.name}' expects {len(fn.params)} argument(s), got {len(args)}",
                line,
            )
        # PL Concept: Lexical Scoping — new scope is rooted in fn.closure (where the
        # function was *defined*), not in env (where it was *called*). This is the
        # critical distinction between lexical and dynamic scoping.
        call_env = fn.closure.child(f"<fn:{fn.name}>")   # PL Concept: Dynamic Memory — new heap-allocated frame
        for param, arg in zip(fn.params, args):
            call_env.define(param, arg)   # PL Concept: Scope — parameter binding in the new local frame

        try:
            self._exec_block(fn.body, call_env)
            return MiniNull()          # PL Concept: Functions — implicit null if no return statement reached
        except ReturnSignal as ret:
            return ret.value           # PL Concept: Exception Handling (internal) — signal unwinds to here

    def _construct_struct(
        self, struct_def: MiniStructDef, args: list[MiniValue], line: int
    ) -> MiniObject:
        """
        PL Concept: User-defined Types — create an instance by binding positional
        args to named fields.
        PL Concept: Dynamic Memory — a new MiniObject (heap dict) is created.
        """
        if len(args) != len(struct_def.fields):
            raise MiniRuntimeError(
                f"'{struct_def.name}' expects {len(struct_def.fields)} field(s), "
                f"got {len(args)}",
                line,
            )
        return MiniObject(
            struct_name=struct_def.name,
            fields=dict(zip(struct_def.fields, args)),
        )

    def _eval_method_call(self, node: CallExpr, env: Environment) -> MiniValue:
        """Dispatch obj.method(args) to the appropriate handler."""
        member_node: MemberExpr = node.callee   # type: ignore[assignment]
        obj    = self._eval(member_node.obj, env)
        method = member_node.member
        args   = [self._eval(a, env) for a in node.args]
        line   = node.line

        if isinstance(obj, MiniList):
            return self._list_method(obj, method, args, line)
        if isinstance(obj, MiniString):
            return self._string_method(obj, method, args, line)
        # Struct instance: look up method as a stored function field
        if isinstance(obj, MiniObject):
            try:
                fn = obj.get_field(method)
                return self._call_value(fn, args, line)
            except MiniRuntimeError:
                pass

        raise MiniRuntimeError(f"{obj.type_name()} has no method '{method}'", line)

    def _list_method(
        self, lst: MiniList, method: str, args: list[MiniValue], line: int
    ) -> MiniValue:
        if method == "push":
            if len(args) != 1:
                raise MiniRuntimeError("push() takes 1 argument", line)
            lst.push(args[0])
            return MiniNull()
        if method == "pop":
            if args:
                raise MiniRuntimeError("pop() takes no arguments", line)
            return lst.pop()
        if method == "len":
            return MiniNumber(lst.length())
        if method == "prepend":
            if len(args) != 1:
                raise MiniRuntimeError("prepend() takes 1 argument", line)
            lst.prepend(args[0])
            return MiniNull()
        if method == "get":
            if len(args) != 1:
                raise MiniRuntimeError("get() takes 1 argument", line)
            if not isinstance(args[0], MiniNumber):
                raise MiniRuntimeError("get() index must be a Number", line)
            return lst.get(int(args[0].value))
        if method == "contains":
            if len(args) != 1:
                raise MiniRuntimeError("contains() takes 1 argument", line)
            return MiniBool(args[0] in lst._to_python_list())
        raise MiniRuntimeError(f"List has no method '{method}'", line)

    def _string_method(
        self, s: MiniString, method: str, args: list[MiniValue], line: int
    ) -> MiniValue:
        if method == "len":
            return MiniNumber(len(s.value))
        if method == "upper":
            return MiniString(s.value.upper())
        if method == "lower":
            return MiniString(s.value.lower())
        if method == "split":
            if len(args) != 1:
                raise MiniRuntimeError("split() takes 1 argument", line)
            return MiniList([MiniString(p) for p in s.value.split(args[0].to_display())])
        if method == "contains":
            if len(args) != 1:
                raise MiniRuntimeError("contains() takes 1 argument", line)
            return MiniBool(args[0].to_display() in s.value)
        if method == "trim":
            return MiniString(s.value.strip())
        raise MiniRuntimeError(f"String has no method '{method}'", line)

    # ---- remaining expression evaluators ----

    def _eval_index(self, node: IndexExpr, env: Environment) -> MiniValue:
        obj = self._eval(node.obj, env)
        idx = self._eval(node.index, env)
        if isinstance(obj, MiniList):
            if not isinstance(idx, MiniNumber):
                raise MiniRuntimeError("List index must be a Number", node.line)
            return obj.get(int(idx.value))
        if isinstance(obj, MiniString):
            if not isinstance(idx, MiniNumber):
                raise MiniRuntimeError("String index must be a Number", node.line)
            i = int(idx.value)
            if i < 0 or i >= len(obj.value):
                raise MiniRuntimeError(f"String index {i} out of range", node.line)
            return MiniString(obj.value[i])
        raise MiniRuntimeError(f"Cannot index into {obj.type_name()}", node.line)

    def _eval_member(self, node: MemberExpr, env: Environment) -> MiniValue:
        obj = self._eval(node.obj, env)
        if isinstance(obj, MiniObject):
            return obj.get_field(node.member)
        raise MiniRuntimeError(
            f"{obj.type_name()} has no member '{node.member}'", node.line
        )

    def _eval_list(self, node: ListExpr, env: Environment) -> MiniList:
        return MiniList([self._eval(el, env) for el in node.elements])

    def _eval_lambda(self, node: LambdaExpr, env: Environment) -> MiniFunction:
        """
        PL Concept: Higher-order Functions & Closures — anonymous function that
        captures the *current* environment.  Enables closures and callbacks.
        """
        # PL Concept: Closures / Lexical Scoping — env captured HERE (at creation time),
        # not later at call time. This is what makes closures work: the function
        # "closes over" the variables visible at the point it was written.
        # PL Concept: Dynamic Memory — MiniFunction is heap-allocated; env reference keeps
        # the parent scope frame alive as long as this closure exists.
        return MiniFunction(name=None, params=node.params, body=node.body, closure=env)

    def _eval_new(self, node: NewExpr, env: Environment) -> MiniObject:
        """Alternative struct-instantiation syntax: new StructName(args)."""
        struct_def = env.get(node.struct_name, node.line)
        if not isinstance(struct_def, MiniStructDef):
            raise MiniRuntimeError(
                f"'{node.struct_name}' is not a struct type", node.line
            )
        args = [self._eval(a, env) for a in node.args]
        return self._construct_struct(struct_def, args, node.line)

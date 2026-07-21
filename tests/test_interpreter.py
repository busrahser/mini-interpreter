"""
Test suite for the Mini Interpreter.

Each test runs a mini-language snippet and checks stdout output or return values.
Tests are organised by PL concept so the mapping is obvious to a marker.
"""

import sys
import io
import unittest

# Ensure project root is on the path when running this file directly
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))

from lexer.lexer import Lexer
from parser.parser import Parser
from interpreter.interpreter import Interpreter
from runtime.exceptions import MiniRuntimeError, ParseError
from runtime.types import MiniNumber, MiniString, MiniBool, MiniNull, MiniList


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(source: str) -> tuple[list[str], object]:
    """Run source, capture printed lines, return (lines, last_value)."""
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        interp  = Interpreter()
        tokens  = Lexer(source).tokenize()
        ast     = Parser(tokens).parse()
        result  = interp.run(ast)
    finally:
        sys.stdout = old_stdout
    lines = [l for l in captured.getvalue().split("\n") if l != ""]
    return lines, result


# ---------------------------------------------------------------------------
# 1. Lexer
# ---------------------------------------------------------------------------

class TestLexer(unittest.TestCase):

    def test_integer_token(self):
        from lexer.lexer import TokenType
        tokens = Lexer("42").tokenize()
        self.assertEqual(tokens[0].type, TokenType.NUMBER)
        self.assertEqual(tokens[0].value, 42.0)

    def test_string_token(self):
        from lexer.lexer import TokenType
        tokens = Lexer('"hello"').tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "hello")

    def test_keywords(self):
        from lexer.lexer import TokenType
        tokens = Lexer("if else while fun let return").tokenize()
        expected = [TokenType.IF, TokenType.ELSE, TokenType.WHILE,
                    TokenType.FUN, TokenType.LET, TokenType.RETURN]
        self.assertEqual([t.type for t in tokens[:-1]], expected)

    def test_comments_ignored(self):
        tokens = Lexer("# comment\n42").tokenize()
        self.assertEqual(len(tokens), 2)   # NUMBER + EOF

    def test_float(self):
        from lexer.lexer import TokenType
        tokens = Lexer("3.14").tokenize()
        self.assertAlmostEqual(tokens[0].value, 3.14)


# ---------------------------------------------------------------------------
# 2. Parser / AST
# ---------------------------------------------------------------------------

class TestParser(unittest.TestCase):

    def test_let_statement(self):
        from parser.ast_nodes import Program, LetStatement
        tokens = Lexer("let x = 5").tokenize()
        ast = Parser(tokens).parse()
        self.assertIsInstance(ast, Program)
        self.assertIsInstance(ast.body[0], LetStatement)
        self.assertEqual(ast.body[0].name, "x")

    def test_function_decl(self):
        from parser.ast_nodes import FunctionDecl
        tokens = Lexer("fun add(a, b) { return a + b }").tokenize()
        ast = Parser(tokens).parse()
        self.assertIsInstance(ast.body[0], FunctionDecl)
        self.assertEqual(ast.body[0].name, "add")
        self.assertEqual(ast.body[0].params, ["a", "b"])

    def test_parse_error(self):
        with self.assertRaises(ParseError):
            Parser(Lexer("let 123 = x").tokenize()).parse()

    def test_nested_if_else(self):
        from parser.ast_nodes import IfStatement
        src = "if x > 0 { let a = 1 } else if x < 0 { let a = 2 } else { let a = 3 }"
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        node = ast.body[0]
        self.assertIsInstance(node, IfStatement)
        self.assertIsInstance(node.else_branch, IfStatement)


# ---------------------------------------------------------------------------
# 3. Variables & Arithmetic
# ---------------------------------------------------------------------------

class TestVariables(unittest.TestCase):

    def test_let_and_print(self):
        lines, _ = run('let x = 42\nprint(x)')
        self.assertEqual(lines[0], "42")

    def test_arithmetic(self):
        lines, _ = run('print(3 + 4 * 2)')
        self.assertEqual(lines[0], "11")

    def test_string_concat(self):
        lines, _ = run('print("hello" + " " + "world")')
        self.assertEqual(lines[0], "hello world")

    def test_reassignment(self):
        lines, _ = run('let x = 1\nx = x + 1\nprint(x)')
        self.assertEqual(lines[0], "2")

    def test_modulo(self):
        lines, _ = run('print(10 % 3)')
        self.assertEqual(lines[0], "1")

    def test_division_by_zero(self):
        with self.assertRaises(MiniRuntimeError):
            Interpreter().run(Parser(Lexer("let x = 1 / 0").tokenize()).parse())


# ---------------------------------------------------------------------------
# 4. Scope & Environment
# ---------------------------------------------------------------------------

class TestScope(unittest.TestCase):

    def test_local_shadows_global(self):
        src = """
let x = 10
fun f() {
    let x = 20
    return x
}
print(f())
print(x)
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "20")
        self.assertEqual(lines[1], "10")

    def test_function_cannot_see_caller_locals(self):
        """Lexical scoping: f() should not see 'y' defined in the caller."""
        src = """
fun f() {
    try {
        return y
    } catch(e) {
        return "not found"
    }
}
let y = 99
let result = f()
print(result)
"""
        # y IS in the global env, so f() can see it via the global scope chain
        lines, _ = run(src)
        self.assertEqual(lines[0], "99")

    def test_mutation_of_outer_variable(self):
        src = """
let counter = 0
fun inc() {
    counter = counter + 1
}
inc()
inc()
print(counter)
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "2")

    def test_undefined_variable_error(self):
        with self.assertRaises(MiniRuntimeError):
            Interpreter().run(Parser(Lexer("print(undefined_var)").tokenize()).parse())


# ---------------------------------------------------------------------------
# 5. Functions & Procedures
# ---------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):

    def test_basic_function(self):
        lines, _ = run('fun double(x) { return x * 2 }\nprint(double(7))')
        self.assertEqual(lines[0], "14")

    def test_default_null_return(self):
        src = 'fun noop() { let x = 1 }\nlet v = noop()\nprint(type(v))'
        lines, _ = run(src)
        self.assertEqual(lines[0], "Null")

    def test_first_class_function(self):
        src = """
fun apply(fn, x) { return fn(x) }
let triple = fun(n) { return n * 3 }
print(apply(triple, 5))
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "15")

    def test_wrong_arity(self):
        with self.assertRaises(MiniRuntimeError):
            run('fun f(a, b) { return a + b }\nf(1)')


# ---------------------------------------------------------------------------
# 6. Recursion (Elective)
# ---------------------------------------------------------------------------

class TestRecursion(unittest.TestCase):

    def test_fibonacci(self):
        src = """
fun fib(n) {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}
print(fib(0))
print(fib(1))
print(fib(7))
print(fib(10))
"""
        lines, _ = run(src)
        self.assertEqual(lines, ["0", "1", "13", "55"])

    def test_factorial(self):
        src = """
fun fact(n) {
    if n <= 1 { return 1 }
    return n * fact(n - 1)
}
print(fact(5))
print(fact(10))
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "120")
        self.assertEqual(lines[1], "3628800")

    def test_mutual_recursion(self):
        src = """
fun is_even(n) {
    if n == 0 { return true }
    return is_odd(n - 1)
}
fun is_odd(n) {
    if n == 0 { return false }
    return is_even(n - 1)
}
print(is_even(4))
print(is_odd(7))
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "true")
        self.assertEqual(lines[1], "true")


# ---------------------------------------------------------------------------
# 7. Exception Handling (Elective)
# ---------------------------------------------------------------------------

class TestExceptions(unittest.TestCase):

    def test_basic_try_catch(self):
        lines, _ = run('try { throw "oops" } catch(e) { print(e) }')
        self.assertEqual(lines[0], "oops")

    def test_uncaught_throw_propagates(self):
        from runtime.types import MiniThrown
        with self.assertRaises(MiniThrown):
            Interpreter().run(Parser(Lexer('throw "boom"').tokenize()).parse())

    def test_catch_binds_value(self):
        src = 'try { throw 42 } catch(err) { print(type(err)) }'
        lines, _ = run(src)
        self.assertEqual(lines[0], "Number")

    def test_nested_try_catch(self):
        src = """
try {
    try {
        throw "inner"
    } catch(e) {
        print("inner: " + e)
        throw "re-thrown"
    }
} catch(e) {
    print("outer: " + e)
}
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "inner: inner")
        self.assertEqual(lines[1], "outer: re-thrown")

    def test_no_catch_when_no_throw(self):
        lines, _ = run('try { print("ok") } catch(e) { print("bad") }')
        self.assertEqual(lines, ["ok"])

    def test_throw_struct(self):
        src = """
struct AppError { code, message }
try {
    throw new AppError(404, "not found")
} catch(e) {
    print(str(e.code) + " " + e.message)
}
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "404 not found")


# ---------------------------------------------------------------------------
# 8. Higher-order Functions (Elective)
# ---------------------------------------------------------------------------

class TestHigherOrder(unittest.TestCase):

    def test_map(self):
        lines, _ = run('print(map([1,2,3], fun(x){ return x*2 }))')
        self.assertEqual(lines[0], "[2, 4, 6]")

    def test_filter(self):
        lines, _ = run('print(filter([1,2,3,4,5], fun(x){ return x % 2 == 0 }))')
        self.assertEqual(lines[0], "[2, 4]")

    def test_reduce(self):
        lines, _ = run('print(reduce([1,2,3,4,5], fun(a,x){ return a+x }, 0))')
        self.assertEqual(lines[0], "15")

    def test_closure_counter(self):
        src = """
fun make_counter() {
    let n = 0
    return fun() { n = n + 1; return n }
}
let c = make_counter()
print(c())
print(c())
print(c())
"""
        lines, _ = run(src)
        self.assertEqual(lines, ["1", "2", "3"])

    def test_function_returning_function(self):
        src = """
fun make_adder(x) { return fun(y) { return x + y } }
let add3 = make_adder(3)
print(add3(10))
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "13")


# ---------------------------------------------------------------------------
# 9. User-defined Types (struct)
# ---------------------------------------------------------------------------

class TestStructs(unittest.TestCase):

    def test_struct_creation_and_access(self):
        src = """
struct Point { x, y }
let p = new Point(3, 4)
print(p.x)
print(p.y)
"""
        lines, _ = run(src)
        self.assertEqual(lines, ["3", "4"])

    def test_struct_mutation(self):
        src = """
struct Counter { value }
let c = new Counter(0)
c.value = c.value + 1
print(c.value)
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "1")

    def test_struct_as_callable_constructor(self):
        src = """
struct Box { item }
let b = Box(99)
print(b.item)
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "99")

    def test_type_name_is_struct_name(self):
        src = """
struct Dog { name }
let d = new Dog("Rex")
print(type(d))
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "Dog")

    def test_invalid_field_access(self):
        with self.assertRaises(MiniRuntimeError):
            run('struct A { x }\nlet a = new A(1)\nprint(a.z)')


# ---------------------------------------------------------------------------
# 10. Dynamic Data Structures (MiniList / linked list)
# ---------------------------------------------------------------------------

class TestDynamicStructures(unittest.TestCase):

    def test_list_literal(self):
        lines, _ = run('print([1, 2, 3])')
        self.assertEqual(lines[0], "[1, 2, 3]")

    def test_list_push_pop(self):
        src = """
let lst = [1, 2, 3]
lst.push(4)
print(lst)
print(lst.pop())
print(lst)
"""
        lines, _ = run(src)
        self.assertEqual(lines[0], "[1, 2, 3, 4]")
        self.assertEqual(lines[1], "4")
        self.assertEqual(lines[2], "[1, 2, 3]")

    def test_list_index(self):
        lines, _ = run('let lst = [10, 20, 30]\nprint(lst[1])')
        self.assertEqual(lines[0], "20")

    def test_list_index_assign(self):
        lines, _ = run('let lst = [1, 2, 3]\nlst[0] = 99\nprint(lst[0])')
        self.assertEqual(lines[0], "99")

    def test_list_concatenation(self):
        lines, _ = run('print([1,2] + [3,4])')
        self.assertEqual(lines[0], "[1, 2, 3, 4]")

    def test_range(self):
        lines, _ = run('print(range(5))')
        self.assertEqual(lines[0], "[0, 1, 2, 3, 4]")

    def test_builtin_len(self):
        lines, _ = run('print(len([10, 20, 30]))')
        self.assertEqual(lines[0], "3")


# ---------------------------------------------------------------------------
# 11. Type safety
# ---------------------------------------------------------------------------

class TestTypeSafety(unittest.TestCase):

    def test_type_mismatch_arithmetic(self):
        with self.assertRaises(MiniRuntimeError):
            run('print(true + 1)')

    def test_index_on_non_list(self):
        with self.assertRaises(MiniRuntimeError):
            run('let x = 42\nprint(x[0])')

    def test_call_non_callable(self):
        with self.assertRaises(MiniRuntimeError):
            run('let x = 5\nx()')


# ---------------------------------------------------------------------------
# 12. Built-in functions
# ---------------------------------------------------------------------------

class TestBuiltins(unittest.TestCase):

    def test_str_conversion(self):
        lines, _ = run('print(str(3.14))')
        self.assertEqual(lines[0], "3.14")

    def test_num_conversion(self):
        lines, _ = run('print(num("42") + 1)')
        self.assertEqual(lines[0], "43")

    def test_type_builtin(self):
        lines, _ = run('print(type(true))')
        self.assertEqual(lines[0], "Bool")

    def test_abs(self):
        lines, _ = run('print(abs(-7))')
        self.assertEqual(lines[0], "7")

    def test_max_min(self):
        lines, _ = run('print(max(3, 1, 4, 1, 5))\nprint(min(3, 1, 4, 1, 5))')
        self.assertEqual(lines[0], "5")
        self.assertEqual(lines[1], "1")

    def test_sqrt(self):
        lines, _ = run('print(sqrt(9))')
        self.assertEqual(lines[0], "3")

    def test_split_join(self):
        lines, _ = run('let parts = split("a,b,c", ",")\nprint(join(parts, "-"))')
        self.assertEqual(lines[0], "a-b-c")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)

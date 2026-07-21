"""
BUILTINS MODULE
===============
PL Concept: Higher-order Functions (Elective) — map, filter, reduce, and forEach
accept MiniFunction or MiniBuiltin values as arguments, treating functions as
first-class data.  They are the canonical demonstration of HOFs in this project.

PL Concept: Abstraction — every built-in function is registered as a MiniBuiltin
and appears identical to user-defined functions from inside the mini language.
Callers cannot tell whether a callable is implemented in Python or in mini.

PL Concept: Type Safety — each built-in validates argument count and types,
raising MiniRuntimeError with descriptive messages before any operation begins.

PL Concept: Modular Decomposition — each built-in is a standalone Python function.
make_builtins() wires them into a MiniBuiltin registry that the interpreter loads
into the global environment at startup.
"""

from runtime.types import (
    MiniValue, MiniNumber, MiniString, MiniBool, MiniNull,
    MiniList, MiniFunction, MiniBuiltin,
)
from runtime.exceptions import MiniRuntimeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_arity(name: str, args: list, expected: int, line: int) -> None:
    if len(args) != expected:
        raise MiniRuntimeError(
            f"'{name}' expects {expected} argument(s), got {len(args)}", line
        )


def _require(name: str, value: MiniValue, typ, line: int) -> None:
    if not isinstance(value, typ):
        raise MiniRuntimeError(
            f"'{name}' requires a {typ.__name__}, got {value.type_name()}", line
        )


def _invoke(fn: MiniValue, args: list[MiniValue], line: int, interp) -> MiniValue:
    """Call a MiniFunction or MiniBuiltin from inside another built-in.
    PL Concept: Abstraction — the caller does not need to know whether fn is a
    user-defined function or a Python built-in; both are invoked identically."""
    if isinstance(fn, MiniBuiltin):
        return fn.fn(args, line, interp)                    # PL Concept: Abstraction — uniform call path
    if isinstance(fn, MiniFunction):
        return interp._call_mini_function(fn, args, line)  # PL Concept: Scope — creates child of fn's closure env
    raise MiniRuntimeError(f"Expected a callable, got {fn.type_name()}", line)  # PL Concept: Type Safety


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _print(args: list[MiniValue], line: int, _interp) -> MiniNull:
    """print(val, …) — print one or more values separated by spaces."""
    print(" ".join(v.to_display() for v in args))
    return MiniNull()


def _input_fn(args: list[MiniValue], line: int, _interp) -> MiniString:
    """input(prompt?) — read a line of text from stdin."""
    prompt = args[0].to_display() if args else ""
    return MiniString(input(prompt))


# ---------------------------------------------------------------------------
# Type conversion & inspection
# ---------------------------------------------------------------------------

def _str_fn(args: list[MiniValue], line: int, _interp) -> MiniString:
    _check_arity("str", args, 1, line)
    return MiniString(args[0].to_display())


def _num_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    _check_arity("num", args, 1, line)
    v = args[0]
    if isinstance(v, MiniNumber):
        return v
    if isinstance(v, MiniString):
        try:
            return MiniNumber(float(v.value))
        except ValueError:
            raise MiniRuntimeError(f"Cannot convert \"{v.value}\" to Number", line)
    raise MiniRuntimeError(f"Cannot convert {v.type_name()} to Number", line)


def _type_fn(args: list[MiniValue], line: int, _interp) -> MiniString:
    _check_arity("type", args, 1, line)
    return MiniString(args[0].type_name())


def _bool_fn(args: list[MiniValue], line: int, _interp) -> MiniBool:
    _check_arity("bool", args, 1, line)
    return MiniBool(args[0].is_truthy())


# ---------------------------------------------------------------------------
# List operations
# ---------------------------------------------------------------------------

def _len_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    _check_arity("len", args, 1, line)
    v = args[0]
    if isinstance(v, MiniList):
        return MiniNumber(v.length())
    if isinstance(v, MiniString):
        return MiniNumber(len(v.value))
    raise MiniRuntimeError(f"len() not supported for {v.type_name()}", line)


def _append_fn(args: list[MiniValue], line: int, _interp) -> MiniNull:
    _check_arity("append", args, 2, line)
    _require("append", args[0], MiniList, line)
    args[0].push(args[1])
    return MiniNull()


def _prepend_fn(args: list[MiniValue], line: int, _interp) -> MiniNull:
    _check_arity("prepend", args, 2, line)
    _require("prepend", args[0], MiniList, line)
    args[0].prepend(args[1])
    return MiniNull()


def _pop_fn(args: list[MiniValue], line: int, _interp) -> MiniValue:
    _check_arity("pop", args, 1, line)
    _require("pop", args[0], MiniList, line)
    return args[0].pop()


def _range_fn(args: list[MiniValue], line: int, _interp) -> MiniList:
    """range(stop) | range(start, stop) | range(start, stop, step)"""
    if len(args) == 1:
        start, stop, step = 0, int(args[0].value), 1
    elif len(args) == 2:
        start, stop, step = int(args[0].value), int(args[1].value), 1
    elif len(args) == 3:
        start, stop, step = (
            int(args[0].value), int(args[1].value), int(args[2].value)
        )
    else:
        raise MiniRuntimeError("range() takes 1–3 arguments", line)
    if step == 0:
        raise MiniRuntimeError("range() step cannot be zero", line)
    lst = MiniList()
    for i in range(start, stop, step):
        lst.push(MiniNumber(i))
    return lst


# ---------------------------------------------------------------------------
# Higher-order functions (Elective concept)
# ---------------------------------------------------------------------------

def _map_fn(args: list[MiniValue], line: int, interp) -> MiniList:
    """
    map(list, fn) → new list with fn applied element-wise.
    PL Concept: Higher-order Functions — fn is a first-class MiniValue argument.
    PL Concept: Dynamic Memory — result is a freshly allocated MiniList (new heap object).
    """
    _check_arity("map", args, 2, line)
    _require("map", args[0], MiniList, line)
    result = MiniList()   # PL Concept: Dynamic Memory — new list allocated for each map() call
    for item in args[0]._to_python_list():
        result.push(_invoke(args[1], [item], line, interp))  # PL Concept: Higher-order Functions — fn called per element
    return result


def _filter_fn(args: list[MiniValue], line: int, interp) -> MiniList:
    """
    filter(list, predicate) → new list of elements where predicate is truthy.
    PL Concept: Higher-order Functions — predicate is a first-class callable.
    PL Concept: Type Safety — predicate return value is tested via is_truthy(),
    not by requiring an explicit Bool, accepting any truthy value.
    """
    _check_arity("filter", args, 2, line)
    _require("filter", args[0], MiniList, line)
    result = MiniList()   # PL Concept: Dynamic Memory — new list for filtered elements
    for item in args[0]._to_python_list():
        if _invoke(args[1], [item], line, interp).is_truthy():  # PL Concept: Higher-order Functions — predicate decides inclusion
            result.push(item)
    return result


def _reduce_fn(args: list[MiniValue], line: int, interp) -> MiniValue:
    """
    reduce(list, fn, initial) → fold fn over list, accumulating a single value.
    PL Concept: Higher-order Functions — fn is a binary combiner function (first-class).
    The fold pattern is the basis of many algorithms: sum, product, max, flatten…
    """
    _check_arity("reduce", args, 3, line)
    _require("reduce", args[0], MiniList, line)
    acc = args[2]   # PL Concept: Variable Lifetime — accumulator lives across all iterations
    for item in args[0]._to_python_list():
        acc = _invoke(args[1], [acc, item], line, interp)  # PL Concept: Higher-order Functions — fn(acc, x) updates accumulator
    return acc


def _foreach_fn(args: list[MiniValue], line: int, interp) -> MiniNull:
    """forEach(list, fn) — call fn(element) for side effects only.
    PL Concept: Higher-order Functions — fn is a first-class callback.
    Unlike map/filter, the return value of fn is discarded; this is the HOF
    pattern for performing side effects (print, mutate, etc.) over a collection."""
    _check_arity("forEach", args, 2, line)
    _require("forEach", args[0], MiniList, line)
    for item in args[0]._to_python_list():
        _invoke(args[1], [item], line, interp)  # PL Concept: Higher-order Functions — callback invoked per element
    return MiniNull()


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _abs_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    _check_arity("abs", args, 1, line)
    _require("abs", args[0], MiniNumber, line)
    return MiniNumber(abs(args[0].value))


def _max_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    if not args:
        raise MiniRuntimeError("max() requires at least one argument", line)
    nums: list[float] = []
    for a in args:
        if isinstance(a, MiniList):
            nums.extend(v.value for v in a._to_python_list() if isinstance(v, MiniNumber))
        elif isinstance(a, MiniNumber):
            nums.append(a.value)
        else:
            raise MiniRuntimeError(f"max() got non-number: {a.type_name()}", line)
    if not nums:
        raise MiniRuntimeError("max() got an empty list", line)
    return MiniNumber(max(nums))


def _min_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    if not args:
        raise MiniRuntimeError("min() requires at least one argument", line)
    nums: list[float] = []
    for a in args:
        if isinstance(a, MiniList):
            nums.extend(v.value for v in a._to_python_list() if isinstance(v, MiniNumber))
        elif isinstance(a, MiniNumber):
            nums.append(a.value)
        else:
            raise MiniRuntimeError(f"min() got non-number: {a.type_name()}", line)
    if not nums:
        raise MiniRuntimeError("min() got an empty list", line)
    return MiniNumber(min(nums))


def _floor_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    _check_arity("floor", args, 1, line)
    _require("floor", args[0], MiniNumber, line)
    import math
    return MiniNumber(math.floor(args[0].value))


def _sqrt_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    _check_arity("sqrt", args, 1, line)
    _require("sqrt", args[0], MiniNumber, line)
    import math
    if args[0].value < 0:
        raise MiniRuntimeError("sqrt() of a negative number", line)
    return MiniNumber(math.sqrt(args[0].value))


def _pow_fn(args: list[MiniValue], line: int, _interp) -> MiniNumber:
    _check_arity("pow", args, 2, line)
    _require("pow", args[0], MiniNumber, line)
    _require("pow", args[1], MiniNumber, line)
    return MiniNumber(args[0].value ** args[1].value)


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def _split_fn(args: list[MiniValue], line: int, _interp) -> MiniList:
    _check_arity("split", args, 2, line)
    _require("split", args[0], MiniString, line)
    _require("split", args[1], MiniString, line)
    return MiniList([MiniString(p) for p in args[0].value.split(args[1].value)])


def _join_fn(args: list[MiniValue], line: int, _interp) -> MiniString:
    _check_arity("join", args, 2, line)
    _require("join", args[0], MiniList, line)
    _require("join", args[1], MiniString, line)
    parts = [v.to_display() for v in args[0]._to_python_list()]
    return MiniString(args[1].value.join(parts))


def _trim_fn(args: list[MiniValue], line: int, _interp) -> MiniString:
    _check_arity("trim", args, 1, line)
    _require("trim", args[0], MiniString, line)
    return MiniString(args[0].value.strip())


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

def _error_fn(args: list[MiniValue], line: int, _interp) -> MiniNull:
    """error(msg) — throw a runtime error from within mini code."""
    _check_arity("error", args, 1, line)
    from runtime.types import MiniThrown
    raise MiniThrown(args[0], line)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def make_builtins() -> dict[str, MiniBuiltin]:
    """
    Build the complete built-in function registry.
    Returns a dict name → MiniBuiltin ready to be loaded into the global env.
    """
    registry = {
        # I/O
        "print":   _print,
        "input":   _input_fn,
        # Type
        "str":     _str_fn,
        "num":     _num_fn,
        "type":    _type_fn,
        "bool":    _bool_fn,
        # List
        "len":     _len_fn,
        "append":  _append_fn,
        "prepend": _prepend_fn,
        "pop":     _pop_fn,
        "range":   _range_fn,
        # Higher-order
        "map":     _map_fn,
        "filter":  _filter_fn,
        "reduce":  _reduce_fn,
        "forEach": _foreach_fn,
        # Math
        "abs":     _abs_fn,
        "max":     _max_fn,
        "min":     _min_fn,
        "floor":   _floor_fn,
        "sqrt":    _sqrt_fn,
        "pow":     _pow_fn,
        # String
        "split":   _split_fn,
        "join":    _join_fn,
        "trim":    _trim_fn,
        # Error
        "error":   _error_fn,
    }
    return {name: MiniBuiltin(name, fn) for name, fn in registry.items()}

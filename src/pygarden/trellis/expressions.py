"""Restricted expression evaluation for dynamic SQL."""

from __future__ import annotations

import ast
import operator
from collections.abc import Mapping
from typing import Any

from pygarden.trellis.exceptions import TrellisTemplateError


def resolve_name(name: str, values: Mapping[str, Any]) -> Any:
    """Resolve a dotted name through mappings and public attributes."""
    parts = name.split(".")
    if parts[0] not in values:
        raise TrellisTemplateError(f"Unknown template name: {parts[0]}")
    value = values[parts[0]]
    for part in parts[1:]:
        if part.startswith("_"):
            raise TrellisTemplateError("Private attributes are not available in templates")
        if isinstance(value, Mapping):
            if part not in value:
                raise TrellisTemplateError(f"Unknown mapping key in {name}: {part}")
            value = value[part]
        else:
            try:
                value = getattr(value, part)
            except AttributeError as error:
                raise TrellisTemplateError(f"Unknown attribute in {name}: {part}") from error
    return value


_COMPARISONS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}


def evaluate(expression: str, values: Mapping[str, Any]) -> Any:  # noqa: C901
    """Evaluate the supported, side-effect-free expression subset."""
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError as error:
        raise TrellisTemplateError(f"Invalid template expression {expression!r}: {error.msg}") from error

    def visit(current: ast.AST) -> Any:  # noqa: C901
        if isinstance(current, ast.Constant):
            return current.value
        if isinstance(current, ast.Name):
            return resolve_name(current.id, values)
        if isinstance(current, ast.Attribute):
            pieces: list[str] = []
            cursor: ast.AST = current
            while isinstance(cursor, ast.Attribute):
                pieces.append(cursor.attr)
                cursor = cursor.value
            if not isinstance(cursor, ast.Name):
                raise TrellisTemplateError("Only dotted name access is supported")
            pieces.append(cursor.id)
            return resolve_name(".".join(reversed(pieces)), values)
        if isinstance(current, (ast.List, ast.Tuple, ast.Set)):
            values_list = [visit(item) for item in current.elts]
            return tuple(values_list) if isinstance(current, ast.Tuple) else values_list
        if isinstance(current, ast.UnaryOp) and isinstance(current.op, ast.Not):
            return not visit(current.operand)
        if isinstance(current, ast.BoolOp):
            items = [visit(item) for item in current.values]
            return all(items) if isinstance(current.op, ast.And) else any(items)
        if isinstance(current, ast.Compare):
            left = visit(current.left)
            for operation, comparator in zip(current.ops, current.comparators):
                right = visit(comparator)
                function = _COMPARISONS.get(type(operation))
                if function is None or not function(left, right):
                    return False
                left = right
            return True
        raise TrellisTemplateError(f"Unsupported template expression: {ast.dump(current, include_attributes=False)}")

    return visit(node)

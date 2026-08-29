"""Repository base and statement decorators."""

from __future__ import annotations

import functools
import inspect
from pathlib import Path
from typing import Any

from pygarden.trellis.context import TrellisContext


class TrellisRepository:
    """Base class for generated and application Trellis repositories."""

    def __init__(self, context: TrellisContext):
        """Bind the repository to a Trellis unit-of-work context."""
        self.trellis = context


def _parameters(function, instance, args, kwargs) -> dict[str, Any]:
    signature = inspect.signature(function)
    bound = signature.bind(instance, *args, **kwargs)
    bound.apply_defaults()
    return {name: value for name, value in bound.arguments.items() if name not in {"self", "cls"}}


def select(sql: str | Path, result: type, cardinality: str = "many"):
    """Implement a typed async repository method using an external select."""
    if cardinality not in {"many", "one", "optional"}:
        raise ValueError("cardinality must be 'many', 'one', or 'optional'")

    def decorate(function):
        if not inspect.iscoroutinefunction(function):
            raise TypeError("Trellis repository methods must be async")

        @functools.wraps(function)
        async def wrapped(instance, *args, **kwargs):
            return await instance.trellis.select(
                sql, _parameters(function, instance, args, kwargs), result, cardinality
            )

        wrapped.__trellis_statement__ = {
            "kind": "select",
            "sql": str(sql),
            "result": result,
            "cardinality": cardinality,
        }
        return wrapped

    return decorate


def command(sql: str | Path):
    """Implement an async repository method using an external command."""

    def decorate(function):
        if not inspect.iscoroutinefunction(function):
            raise TypeError("Trellis repository methods must be async")

        @functools.wraps(function)
        async def wrapped(instance, *args, **kwargs):
            return await instance.trellis.command(sql, _parameters(function, instance, args, kwargs))

        wrapped.__trellis_statement__ = {"kind": "command", "sql": str(sql)}
        return wrapped

    return decorate


def inline_select(sql: str, result: type, cardinality: str = "many"):
    """Implement a typed async repository method using inline SQL."""
    if cardinality not in {"many", "one", "optional"}:
        raise ValueError("cardinality must be 'many', 'one', or 'optional'")

    def decorate(function):
        if not inspect.iscoroutinefunction(function):
            raise TypeError("Trellis repository methods must be async")

        @functools.wraps(function)
        async def wrapped(instance, *args, **kwargs):
            return await instance.trellis.select_inline(
                sql,
                result,
                cardinality,
                _parameters(function, instance, args, kwargs),
            )

        wrapped.__trellis_statement__ = {
            "kind": "inline_select",
            "sql": sql,
            "result": result,
            "cardinality": cardinality,
        }
        return wrapped

    return decorate


def inline_command(sql: str):
    """Implement an async repository method using an inline command."""

    def decorate(function):
        if not inspect.iscoroutinefunction(function):
            raise TypeError("Trellis repository methods must be async")

        @functools.wraps(function)
        async def wrapped(instance, *args, **kwargs):
            return await instance.trellis.command_inline(sql, _parameters(function, instance, args, kwargs))

        wrapped.__trellis_statement__ = {"kind": "inline_command", "sql": sql}
        return wrapped

    return decorate

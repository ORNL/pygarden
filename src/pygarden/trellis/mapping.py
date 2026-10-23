"""Dataclass metadata and row-to-object mapping for Trellis."""

from __future__ import annotations

import dataclasses
import types
from collections.abc import Mapping, Sequence
from dataclasses import MISSING
from typing import Any, Union, get_args, get_origin, get_type_hints

from pygarden.trellis.exceptions import TrellisCardinalityError, TrellisMappingError


@dataclasses.dataclass(frozen=True)
class FieldMapping:
    """Map a model field to a result column."""

    field: str
    column: str
    primary_key: bool = False


def map(field: str, column: str, primary_key: bool = False):
    """Decorate a Trellis model with a column mapping."""

    def decorate(cls):
        own = list(cls.__dict__.get("__trellis_own_mappings__", ()))
        own.append(FieldMapping(field, column, primary_key))
        cls.__trellis_own_mappings__ = tuple(own)
        return cls

    return decorate


def model(cls):
    """Turn a class into a keyword-only dataclass registered for mapping."""
    cls = dataclasses.dataclass(cls, kw_only=True)
    cls.__trellis_model__ = True
    return cls


def _mappings(cls: type) -> dict[str, FieldMapping]:
    result: dict[str, FieldMapping] = {}
    for parent in reversed(cls.__mro__):
        for item in parent.__dict__.get("__trellis_own_mappings__", ()):
            result[item.field] = item
    return result


def _collection_type(annotation: Any) -> type | None:
    origin = get_origin(annotation)
    if origin in (list, Sequence):
        arguments = get_args(annotation)
        if arguments and isinstance(arguments[0], type) and dataclasses.is_dataclass(arguments[0]):
            return arguments[0]
    return None


def _optional_type(annotation: Any) -> type | None:
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        candidates = [item for item in get_args(annotation) if item is not type(None)]
        if len(candidates) == 1 and isinstance(candidates[0], type) and dataclasses.is_dataclass(candidates[0]):
            return candidates[0]
    return None


def _construct(cls: type, row: Mapping[str, Any], additions: dict[str, Any] | None = None) -> Any:
    hints = get_type_hints(cls)
    mappings = _mappings(cls)
    additions = additions or {}
    values: dict[str, Any] = dict(additions)
    missing: list[str] = []
    for field in dataclasses.fields(cls):
        if field.name in values:
            continue
        annotation = hints.get(field.name)
        if _collection_type(annotation) or _optional_type(annotation):
            continue
        source = mappings.get(field.name, FieldMapping(field.name, field.name)).column
        if source in row:
            values[field.name] = row[source]
        elif field.default is MISSING and field.default_factory is MISSING:
            missing.append(f"{field.name} ({source})")
    if missing:
        raise TrellisMappingError(f"Missing required column(s) for {cls.__name__}: {', '.join(missing)}")
    try:
        return cls(**values)
    except TypeError as error:
        raise TrellisMappingError(f"Unable to construct {cls.__name__}: {error}") from error


def _identity(cls: type, row: Mapping[str, Any], fallback: int) -> tuple[Any, ...]:
    keys = [item for item in _mappings(cls).values() if item.primary_key]
    if not keys:
        return ("__row__", fallback)
    return tuple(row.get(item.column) for item in keys)


def map_rows(  # noqa: C901
    rows: Sequence[Mapping[str, Any]], result_type: type, cardinality: str = "many"
) -> Any:
    """Map flat result rows to scalar or Trellis model results."""
    if cardinality not in {"many", "one", "optional"}:
        raise TrellisCardinalityError(f"Unknown cardinality: {cardinality}")
    normalized = [dict(row) for row in rows]
    if result_type is dict:
        return _apply_cardinality(normalized, cardinality)
    if not dataclasses.is_dataclass(result_type):
        values = [next(iter(row.values())) if row else None for row in normalized]
        return _apply_cardinality(values, cardinality)

    hints = get_type_hints(result_type)
    collections = {
        name: child for name, annotation in hints.items() if (child := _collection_type(annotation)) is not None
    }
    optionals = {name: child for name, annotation in hints.items() if (child := _optional_type(annotation)) is not None}
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row_index, row in enumerate(normalized):
        identity = _identity(result_type, row, row_index)
        if identity not in grouped:
            additions = {name: [] for name in collections}
            additions.update(dict.fromkeys(optionals))
            grouped[identity] = {
                "object": _construct(result_type, row, additions),
                "children": {name: set() for name in collections},
            }
        entry = grouped[identity]
        root = entry["object"]
        for name, child_type in collections.items():
            child_identity = _identity(child_type, row, row_index)
            child_keys = [item for item in _mappings(child_type).values() if item.primary_key]
            if child_keys and all(value is None for value in child_identity):
                continue
            if child_identity not in entry["children"][name]:
                getattr(root, name).append(_construct(child_type, row))
                entry["children"][name].add(child_identity)
        for name, child_type in optionals.items():
            child_identity = _identity(child_type, row, row_index)
            child_keys = [item for item in _mappings(child_type).values() if item.primary_key]
            if getattr(root, name) is None and not (child_keys and all(value is None for value in child_identity)):
                setattr(root, name, _construct(child_type, row))

    return _apply_cardinality([entry["object"] for entry in grouped.values()], cardinality)


def _apply_cardinality(values: list[Any], cardinality: str) -> Any:
    if cardinality == "many":
        return values
    if cardinality == "optional":
        if len(values) > 1:
            raise TrellisCardinalityError(f"Expected at most one result, received {len(values)}")
        return values[0] if values else None
    if len(values) != 1:
        raise TrellisCardinalityError(f"Expected exactly one result, received {len(values)}")
    return values[0]

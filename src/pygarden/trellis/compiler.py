"""Compile comment-directed SQL into asyncpg statements."""

from __future__ import annotations

import re
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pygarden.trellis.exceptions import TrellisBindingError, TrellisTemplateError
from pygarden.trellis.expressions import evaluate, resolve_name

_DIRECTIVE = re.compile(r"^\s*--\s*trellis:\s*(.*?)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class CompiledSQL:
    """SQL and ordered arguments ready for an asyncpg call."""

    sql: str
    arguments: tuple[Any, ...]


@dataclass
class _Text:
    value: str


@dataclass
class _If:
    branches: list[tuple[str | None, list[Any]]]


@dataclass
class _Choose:
    expression: str
    branches: list[tuple[str | None, list[Any]]]


@dataclass
class _For:
    item: str
    collection: str
    separator: str
    body: list[Any]


def _directive(line: str) -> str | None:
    match = _DIRECTIVE.match(line)
    return match.group(1).strip() if match else None


def _rename_bind(sql: str, old: str, new: str) -> str:  # noqa: C901
    """Rename one bind outside SQL strings, identifiers, and comments."""
    output: list[str] = []
    index = 0
    state = "normal"
    dollar_tag = ""
    pattern = re.compile(rf":{re.escape(old)}(?=\.|[^A-Za-z0-9_]|$)")
    while index < len(sql):
        char = sql[index]
        following = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "normal":
            if char == "'":
                state = "single"
            elif char == '"':
                state = "double"
            elif char == "-" and following == "-":
                state = "line_comment"
            elif char == "/" and following == "*":
                state = "block_comment"
            elif char == "$":
                match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
                if match:
                    dollar_tag = match.group(0)
                    state = "dollar"
                    output.append(dollar_tag)
                    index += len(dollar_tag)
                    continue
            elif char == ":" and (index == 0 or sql[index - 1] != ":"):
                match = pattern.match(sql, index)
                if match:
                    output.append(f":{new}")
                    index = match.end()
                    continue
        elif state == "single" and char == "'":
            if following == "'":
                output.extend((char, following))
                index += 2
                continue
            state = "normal"
        elif state == "double" and char == '"':
            if following == '"':
                output.extend((char, following))
                index += 2
                continue
            state = "normal"
        elif state == "line_comment" and char == "\n":
            state = "normal"
        elif state == "block_comment" and char == "*" and following == "/":
            output.extend((char, following))
            index += 2
            state = "normal"
            continue
        elif state == "dollar" and sql.startswith(dollar_tag, index):
            output.append(dollar_tag)
            index += len(dollar_tag)
            state = "normal"
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _parse_sequence(  # noqa: C901
    lines: Sequence[str], index: int = 0, stops: tuple[str, ...] = ()
) -> tuple[list[Any], int]:
    nodes: list[Any] = []
    while index < len(lines):
        directive = _directive(lines[index])
        keyword = directive.split(maxsplit=1)[0].lower() if directive else ""
        if keyword in stops:
            break
        if directive and keyword == "if":
            expression = directive[2:].strip()
            if not expression:
                raise TrellisTemplateError(f"if requires an expression on line {index + 1}")
            branches: list[tuple[str | None, list[Any]]] = []
            body, index = _parse_sequence(lines, index + 1, ("elif", "else", "endif"))
            branches.append((expression, body))
            while index < len(lines):
                branch_directive = _directive(lines[index]) or ""
                branch_keyword = branch_directive.split(maxsplit=1)[0].lower()
                if branch_keyword == "elif":
                    expression = branch_directive[4:].strip()
                    body, index = _parse_sequence(lines, index + 1, ("elif", "else", "endif"))
                    branches.append((expression, body))
                elif branch_keyword == "else":
                    body, index = _parse_sequence(lines, index + 1, ("endif",))
                    branches.append((None, body))
                elif branch_keyword == "endif":
                    index += 1
                    break
                else:
                    raise TrellisTemplateError(f"Unclosed if beginning before line {index + 1}")
            else:
                raise TrellisTemplateError("Unclosed if directive")
            nodes.append(_If(branches))
            continue
        if directive and keyword == "choose":
            expression = directive[6:].strip()
            if not expression:
                raise TrellisTemplateError(f"choose requires an expression on line {index + 1}")
            branches: list[tuple[str | None, list[Any]]] = []
            index += 1
            while index < len(lines):
                branch_directive = _directive(lines[index]) or ""
                branch_keyword = branch_directive.split(maxsplit=1)[0].lower()
                if branch_keyword == "when":
                    when_expression = branch_directive[4:].strip()
                    body, index = _parse_sequence(lines, index + 1, ("when", "otherwise", "endchoose"))
                    branches.append((when_expression, body))
                elif branch_keyword == "otherwise":
                    body, index = _parse_sequence(lines, index + 1, ("endchoose",))
                    branches.append((None, body))
                elif branch_keyword == "endchoose":
                    index += 1
                    break
                else:
                    raise TrellisTemplateError(f"Expected when/otherwise/endchoose on line {index + 1}")
            else:
                raise TrellisTemplateError("Unclosed choose directive")
            nodes.append(_Choose(expression, branches))
            continue
        if directive and keyword == "for":
            try:
                tokens = shlex.split(directive)
            except ValueError as error:
                raise TrellisTemplateError(f"Invalid for directive on line {index + 1}: {error}") from error
            if len(tokens) < 4 or tokens[2].lower() != "in":
                raise TrellisTemplateError(f"Expected 'for item in collection' on line {index + 1}")
            options = dict(token.split("=", 1) for token in tokens[4:] if "=" in token)
            body, index = _parse_sequence(lines, index + 1, ("endfor",))
            if index >= len(lines) or (_directive(lines[index]) or "").lower() != "endfor":
                raise TrellisTemplateError("Unclosed for directive")
            nodes.append(_For(tokens[1], tokens[3], options.get("separator", ""), body))
            index += 1
            continue
        if directive:
            raise TrellisTemplateError(f"Unexpected directive on line {index + 1}: {directive}")
        nodes.append(_Text(lines[index]))
        index += 1
    return nodes, index


def _render(  # noqa: C901
    nodes: Sequence[Any], values: Mapping[str, Any], bindings: dict[str, Any]
) -> str:
    output: list[str] = []
    for node in nodes:
        if isinstance(node, _Text):
            output.append(node.value)
        elif isinstance(node, _If):
            for expression, body in node.branches:
                if expression is None or bool(evaluate(expression, values)):
                    output.append(_render(body, values, bindings))
                    break
        elif isinstance(node, _Choose):
            choice = evaluate(node.expression, values)
            for expression, body in node.branches:
                if expression is None or choice == evaluate(expression, values):
                    output.append(_render(body, values, bindings))
                    break
        elif isinstance(node, _For):
            collection = resolve_name(node.collection, values)
            if not collection:
                raise TrellisTemplateError(
                    f"Collection {node.collection!r} is empty; guard the loop with a Trellis if directive"
                )
            chunks = []
            for item_index, item in enumerate(collection):
                scoped = dict(values)
                scoped[node.item] = item
                alias = f"__trellis_{node.item}_{len(bindings)}_{item_index}"
                rendered = _render(node.body, scoped, bindings)
                rendered = _rename_bind(rendered, node.item, alias)
                bindings[alias] = item
                chunks.append(rendered)
            output.append(node.separator.join(chunks))
    return "".join(output)


def _bind(sql: str, values: Mapping[str, Any]) -> CompiledSQL:  # noqa: C901
    output: list[str] = []
    arguments: list[Any] = []
    index = 0
    state = "normal"
    dollar_tag = ""
    while index < len(sql):
        char = sql[index]
        following = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "normal":
            if char == "'":
                state = "single"
            elif char == '"':
                state = "double"
            elif char == "-" and following == "-":
                state = "line_comment"
            elif char == "/" and following == "*":
                state = "block_comment"
            elif char == "$":
                match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
                if match:
                    dollar_tag = match.group(0)
                    state = "dollar"
                    output.append(dollar_tag)
                    index += len(dollar_tag)
                    continue
            elif (
                char == ":"
                and (index == 0 or sql[index - 1] != ":")
                and following != ":"
                and (following.isalpha() or following == "_")
            ):
                match = re.match(r":([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)", sql[index:])
                assert match is not None
                name = match.group(1)
                try:
                    value = resolve_name(name, values)
                except TrellisTemplateError as error:
                    raise TrellisBindingError(str(error)) from error
                arguments.append(value)
                output.append(f"${len(arguments)}")
                index += len(match.group(0))
                continue
        elif state == "single" and char == "'":
            if following == "'":
                output.extend((char, following))
                index += 2
                continue
            state = "normal"
        elif state == "double" and char == '"':
            if following == '"':
                output.extend((char, following))
                index += 2
                continue
            state = "normal"
        elif state == "line_comment" and char == "\n":
            state = "normal"
        elif state == "block_comment" and char == "*" and following == "/":
            output.extend((char, following))
            index += 2
            state = "normal"
            continue
        elif state == "dollar" and sql.startswith(dollar_tag, index):
            output.append(dollar_tag)
            index += len(dollar_tag)
            state = "normal"
            continue
        output.append(char)
        index += 1
    return CompiledSQL("".join(output), tuple(arguments))


def compile_sql(template: str, parameters: Mapping[str, Any]) -> CompiledSQL:
    """Render dynamic directives and bind named parameters."""
    lines = template.splitlines(keepends=True)
    nodes, index = _parse_sequence(lines)
    if index != len(lines):
        raise TrellisTemplateError(f"Unexpected directive near line {index + 1}")
    bindings = dict(parameters)
    return _bind(_render(nodes, bindings, bindings), bindings)

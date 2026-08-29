"""Trellis: typed, external SQL mapping for pyGARDEN."""

from pygarden.trellis.compiler import CompiledSQL, compile_sql
from pygarden.trellis.config import GenerationConfig, TableConfig, TrellisConfig
from pygarden.trellis.context import TrellisContext
from pygarden.trellis.exceptions import (
    TrellisBindingError,
    TrellisCardinalityError,
    TrellisConfigError,
    TrellisError,
    TrellisGenerationError,
    TrellisMappingError,
    TrellisTemplateError,
)
from pygarden.trellis.generator import PostgresIntrospector, TrellisGenerator
from pygarden.trellis.mapping import FieldMapping, map, map_rows, model
from pygarden.trellis.repository import TrellisRepository, command, inline_command, inline_select, select

__all__ = [
    "CompiledSQL",
    "FieldMapping",
    "GenerationConfig",
    "TableConfig",
    "TrellisBindingError",
    "TrellisCardinalityError",
    "TrellisConfig",
    "TrellisConfigError",
    "TrellisContext",
    "TrellisError",
    "TrellisGenerationError",
    "TrellisGenerator",
    "TrellisMappingError",
    "TrellisRepository",
    "TrellisTemplateError",
    "command",
    "compile_sql",
    "map",
    "map_rows",
    "model",
    "PostgresIntrospector",
    "inline_command",
    "inline_select",
    "select",
]

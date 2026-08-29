"""Exceptions raised by the Trellis mapper runtime."""


class TrellisError(Exception):
    """Base class for Trellis failures."""


class TrellisConfigError(TrellisError):
    """Raised when a Trellis configuration is invalid."""


class TrellisTemplateError(TrellisError):
    """Raised when dynamic SQL cannot be parsed or rendered."""


class TrellisBindingError(TrellisError):
    """Raised when a named SQL parameter cannot be bound."""


class TrellisCardinalityError(TrellisError):
    """Raised when a query returns an unexpected number of objects."""


class TrellisMappingError(TrellisError):
    """Raised when database rows cannot be mapped to a model."""


class TrellisGenerationError(TrellisError):
    """Raised when schema introspection or generation fails."""

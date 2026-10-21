"""Session verifier implementation for the OneID auth plugin."""

from uuid import UUID

from fastapi import HTTPException
from fastapi_sessions.session_verifier import SessionVerifier

from .db_backend import DBBackend
from .session_data import SessionData


class BasicVerifier(SessionVerifier[UUID, SessionData]):
    """Bridge FastAPI sessions verifier hooks to the OneID session backend."""

    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: DBBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        """Initialize verifier settings and backend references."""
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        """Return the verifier identifier key used by session frontend glue."""
        return self._identifier

    @property
    def backend(self):
        """Return the session backend used to resolve stored sessions."""
        return self._backend

    @property
    def auto_error(self):
        """Return whether verifier failures should auto-raise HTTP errors."""
        return self._auto_error

    @property
    def auth_http_exception(self):
        """Return the HTTP exception raised for authentication failures."""
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """If the session exists, it is valid"""
        return True

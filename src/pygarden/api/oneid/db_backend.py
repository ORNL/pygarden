from .auth_db import AuthDB
from typing import Generic
from fastapi_sessions.backends.session_backend import (
    BackendError,
    SessionBackend,
    SessionModel,
)
from fastapi_sessions.frontends.session_frontend import ID

class DBBackend(Generic[ID, SessionModel], SessionBackend[ID, SessionModel]):
    def __init__(self) -> None:
        # self.adb = AuthDB()
        pass

    async def create(self, session_id: ID, data: SessionModel):
        """Create a new session entry."""
        async with AuthDB() as adb:
            await adb.create_session(session_id, data)

    async def read(self, session_id: ID):
        """Read an existing session data."""
        async with AuthDB() as adb:
            return await adb.get_session(session_id)

    async def update(self, session_id: ID, data: SessionModel) -> None:
        """Update an existing session."""
        if await self.read(session_id) is not None:
            async with AuthDB() as adb:
                await adb.update_session(session_id, data)
        else:
            raise BackendError("session does not exist, cannot update")

    async def delete(self, session_id: ID) -> None:
        """Delete an existing session."""
        async with AuthDB() as adb:
            await adb.delete_session(session_id)

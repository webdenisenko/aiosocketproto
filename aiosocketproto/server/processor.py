import asyncio
from abc import ABC
from contextlib import closing
from typing import TYPE_CHECKING

from .. import AsyncSocketClient

if TYPE_CHECKING:
    from .server import AsyncSocketServer


class Processor(ABC):

    async def _connection_handler_wrapper(self: "AsyncSocketServer", reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """ Safe Wrapper for income connections """
        async def session_wrapper():
            with closing(writer):
                session = AsyncSocketClient(reader, writer)
                await session._keep_alive()
                return await self.connection_handler(session)
        self.sessions.append(asyncio.create_task(session_wrapper()))

    async def __aenter__(self: "AsyncSocketServer"):
        return self

    async def __aexit__(self: "AsyncSocketServer", exc_type, exc_value, traceback):
        await self.close()
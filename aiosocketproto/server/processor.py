import asyncio
from abc import ABC
from contextlib import closing
from typing import TYPE_CHECKING

from .. import AsyncSocketClient

if TYPE_CHECKING:
    from .server import AsyncSocketServer


class Processor(ABC):

    async def _connection_handler_wrap(self: "AsyncSocketServer", reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """ Safe Wrapper for income connections """
        async def session():
            with closing(writer):
                socket_protocol = AsyncSocketClient(reader, writer)
                return await self.connection_handler(socket_protocol)
        self.sessions.append(asyncio.create_task(session()))

    async def __aenter__(self: "AsyncSocketServer"):
        return self

    async def __aexit__(self: "AsyncSocketServer", exc_type, exc_value, traceback):
        await self.close()
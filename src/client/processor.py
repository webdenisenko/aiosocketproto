import asyncio
import struct
from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AsyncSocketClient


class Processor(ABC):
    _lock_send: asyncio.Lock
    _lock_recv: asyncio.Lock

    def __init__(self: "AsyncSocketClient"):
        super().__init__()
        self._lock_send = asyncio.Lock()
        self._lock_recv = asyncio.Lock()

    async def _recv(self: "AsyncSocketClient", length: int) -> bytes:
        data = b''
        while left_bytes := length - len(data):
            data += await self.reader.read(left_bytes)
            await asyncio.sleep(.1)
        return data

    async def _send_signal(self: "AsyncSocketClient", signal: int, act: bool) -> None:
        signal = struct.pack("!i", signal)
        self.writer.write(signal)
        await self.writer.drain()
        if act:
            await self._wait_act()

    async def _wait_signal(self: "AsyncSocketClient", signal: int, timeout: int = 30, act: bool = False) -> None:
        try:
            data = await asyncio.wait_for(self._recv(4), timeout)
            data = struct.unpack("!i", data)[0]
            assert data == signal, f'got {data} instead of {signal} signal'
            if act:
                await self._send_act()
        except asyncio.TimeoutError:
            raise TimeoutError(f'signal `{signal}` was not received')

    async def _send_ping(self: "AsyncSocketClient"):
        """ Send Ping signal """
        await self._send_signal(self.SIGNAL_PING, act=True)

    async def _wait_ping(self: "AsyncSocketClient", timeout: int = 15):
        await self._wait_signal(self.SIGNAL_PING, timeout=timeout, act=True)

    async def _send_act(self: "AsyncSocketClient"):
        """ Send act signal """
        await self._send_signal(self.SIGNAL_ACT, act=False)

    async def _wait_act(self: "AsyncSocketClient"):
        await self._wait_signal(self.SIGNAL_ACT, timeout=self.ACT_TIMEOUT, act=False)
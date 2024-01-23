import asyncio
import struct
import time
from abc import ABC
from typing import TYPE_CHECKING, Optional

from .send_packet import SendPacket

if TYPE_CHECKING:
    from .client import AsyncSocketClient


class Processor(ABC):
    _queue_send: asyncio.Queue["SendPacket"] # queue of send tasks
    _pending_packets: asyncio.Queue["SendPacket"] # queue of sent packets which waiting for acknowledging signals
    _received_packets: asyncio.Queue[bytes] # queue of received packets
    _keep_alive_task: Optional[asyncio.Task] # keep alive control and queue executor
    _last_ping_timestamp: float

    def __init__(self: "AsyncSocketClient"):
        super().__init__()
        self._queue_send = asyncio.Queue()
        self._pending_packets = asyncio.Queue()
        self._received_packets = asyncio.Queue()
        self._keep_alive_task = None
        self._last_ping_timestamp = time.time()

    async def _recv(self: "AsyncSocketClient", length: int) -> bytes:
        data = b''
        while left_bytes := length - len(data):
            data += await self.reader.read(left_bytes)
            await asyncio.sleep(.1)
        return data

    async def _send_ack(self: "AsyncSocketClient"):
        """
        Send Acknowledging signal.
        Used to send confirmation that the packet was successfully received.
        """
        signal = struct.pack("!i", self.SIGNAL_ACT)
        self.writer.write(signal)
        await self.writer.drain()

    async def _ping(self: "AsyncSocketClient"):
        """
        Send ping signal.
        And waiting for Acknowledging signal.
        """
        signal = struct.pack("!i", self.SIGNAL_PING)
        self.writer.write(signal)
        await self.writer.drain()

        ping_packet = SendPacket(self.SIGNAL_PING)
        await self._pending_packets.put(ping_packet)
        try:
            await asyncio.wait_for(ping_packet.sent.wait(), timeout=self.ACT_TIMEOUT)
        except asyncio.TimeoutError:
            raise ConnectionAbortedError(f'interrupt connection: client is not active')

    async def _keep_alive(self: "AsyncSocketClient"):
        async def _receiver_task():
            while self.is_connected:

                # check income packets
                try:
                    # receive packet header
                    packet_length = await asyncio.wait_for(self._recv(4), timeout=1)
                    packet_length = struct.unpack("!i", packet_length)[0]

                    # it is signal
                    if packet_length < 0:

                        # ping
                        if packet_length == self.SIGNAL_PING:
                            self._last_ping_timestamp = time.time()
                            await self._send_ack()

                        # acknowledging
                        elif packet_length == self.SIGNAL_ACT:
                            packet = await self._pending_packets.get()
                            packet.sent.set()
                            self._last_ping_timestamp = time.time()

                        else:
                            raise RuntimeError(f'got unrecognized signal: {packet_length}')

                    else:
                        # receive a full packet
                        packet_data = await self._recv(packet_length)

                        # send act signal
                        await self._send_ack()

                        # put to received packets queue
                        await self._received_packets.put(packet_data)
                except asyncio.TimeoutError:
                    pass

        async def _sender_task():
            ping_task = None
            while self.is_connected:
                try:
                    await asyncio.sleep(.01)

                    # time to ping
                    if time.time() > self._last_ping_timestamp + self.PING_INTERVAL:
                        if not ping_task:
                            ping_task = asyncio.create_task(self._ping())
                        elif ping_task.done():
                            if ping_task.exception():
                                raise ping_task.exception()
                            ping_task = None
                            self._last_ping_timestamp = time.time()

                    # execute send
                    if not self._queue_send.empty():
                        send_packet = await self._queue_send.get()

                        # send
                        self.writer.write(send_packet.data)
                        await self.writer.drain()

                        # waiting for act signal
                        await self._pending_packets.put(send_packet)

                except asyncio.TimeoutError:
                    continue

        async def _keep_alive_task():
            await asyncio.gather(_receiver_task(), _sender_task())

        self._keep_alive_task = asyncio.create_task(_keep_alive_task())
import asyncio
import struct
import time
import traceback
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
    _recv_buffer: bytes

    def __init__(self: "AsyncSocketClient"):
        super().__init__()
        self._queue_send = asyncio.Queue()
        self._pending_packets = asyncio.Queue()
        self._received_packets = asyncio.Queue()
        self._keep_alive_task = None
        self._last_ping_timestamp = time.time()
        self._recv_buffer = b''

    async def _recv(self: "AsyncSocketClient", length: int, timeout: int = None) -> Optional[bytes]:
        async def _recv_wrapper():
            while left_bytes := length - len(self._recv_buffer):
                self._recv_buffer += await self.reader.read(left_bytes)
                await asyncio.sleep(.1)
            return self._recv_buffer

        if timeout is not None:
            try:
                data = await asyncio.wait_for(_recv_wrapper(), timeout=timeout)
                self._recv_buffer = b''
                return data
            except asyncio.TimeoutError:
                return None
        else:
            data = await _recv_wrapper()
            self._recv_buffer = b''
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

        self.logger.debug('ping begin')
        signal = struct.pack("!i", self.SIGNAL_PING)
        self.writer.write(signal)
        await self.writer.drain()

        ping_packet = SendPacket(b'__pingdatamock__')
        self._pending_packets.put_nowait(ping_packet)
        try:
            await asyncio.wait_for(ping_packet.sent.wait(), timeout=self.ACT_TIMEOUT)
            self.logger.debug('ping done')
        except asyncio.TimeoutError:
            raise ConnectionAbortedError(f'interrupt connection: client is not active')

    async def _keep_alive(self: "AsyncSocketClient"):
        async def _receiver_task():
            while self.is_connected:

                # check income packets
                try:
                    # receive packet header
                    assert (packet_length := await self._recv(4, timeout=1)) is not None
                    packet_length = struct.unpack("!i", packet_length)[0]

                    # it is signal
                    if packet_length < 0:
                        # ping
                        if packet_length == self.SIGNAL_PING:
                            self.logger.debug('ping received')
                            self._last_ping_timestamp = time.time()
                            await self._send_ack()

                        # acknowledging
                        elif packet_length == self.SIGNAL_ACT:
                            self.logger.debug('ack received')
                            try:
                                packet = await asyncio.wait_for(self._pending_packets.get(), timeout=5)
                                packet.sent.set()
                            except asyncio.TimeoutError:
                                raise ConnectionError('got acknowle signal, but no pending packet')

                            self.logger.debug(f'packet sent done: bytes({len(packet.data)})')
                            self._last_ping_timestamp = time.time()

                        else:
                            raise RuntimeError(f'got unrecognized signal: {packet_length}')

                    else:
                        # receive a full packet
                        packet = await self._recv(packet_length)
                        self.logger.debug(f'packet received: {packet}')

                        # send act signal
                        await self._send_ack()

                        # put to received packets queue
                        self._received_packets.put_nowait(packet)
                except (asyncio.TimeoutError, AssertionError):
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
                                self.logger.debug(f'ping exception: {ping_task.exception()}')
                                raise ping_task.exception()
                            ping_task = None
                            self._last_ping_timestamp = time.time()

                    # execute send
                    if self._queue_send.qsize():
                        send_packet = await self._queue_send.get()
                        self.logger.debug(f'sending packet: bytes({len(send_packet.data)})')

                        # send
                        self.writer.write(send_packet.data)
                        await self.writer.drain()

                        # packet status: pending
                        self._pending_packets.put_nowait(send_packet)

                except asyncio.TimeoutError:
                    continue

        async def _keep_alive_task():
            try:
                await asyncio.gather(_receiver_task(), _sender_task())
            except:
                self.logger.warning(traceback.format_exc())

        self._keep_alive_task = asyncio.create_task(_keep_alive_task())
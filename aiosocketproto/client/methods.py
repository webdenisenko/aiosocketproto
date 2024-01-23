import asyncio
import base64
import json
import struct
from abc import ABC
from typing import TYPE_CHECKING, Type, Dict

from .send_packet import SendPacket
from .serializer import SerializerType

if TYPE_CHECKING:
    from .client import AsyncSocketClient


class Methods(ABC):
    custom_serializers: Dict[str, Type[SerializerType]]

    def __init__(self):
        super().__init__()
        self.custom_serializers = {}

    @classmethod
    async def connect(cls: Type["AsyncSocketClient"], host: str, port: int):
        """ Connect to a server and Create socket client instance """

        reader, writer = await asyncio.open_connection(host, port)
        session = cls(reader, writer)
        await session._keep_alive()
        return session

    @property
    def is_connected(self: "AsyncSocketClient") -> bool:
        return self._keep_alive_task and not self._keep_alive_task.done() and not self.reader.at_eof()

    def add_serializer(self: "AsyncSocketClient", serializer: Type[SerializerType]):
        if not issubclass(serializer, SerializerType):
            raise ValueError('Unsupported serializer type')
        data_type = self.get_data_type_str(serializer.INSTANCE)
        serializer.default = self
        self.custom_serializers[data_type] = serializer

    async def send(self: "AsyncSocketClient", **data):
        """ Serialize and put Packet to send queue """

        # serialize
        data = self.serialize(data)

        # convert to JSON object
        json_data = json.dumps(data)

        # convert to bytes
        encoded_json_data = base64.b64encode(json_data.encode('utf-8'))

        # Send JSON response
        packet_length = struct.pack("!i", len(encoded_json_data))

        # put to queue
        packet = SendPacket(packet_length + encoded_json_data)
        await self._queue_send.put(packet)

        # waiting for execute
        await packet.sent.wait()

    async def receive(self: "AsyncSocketClient"):
        """ Waiting for income Packet """

        packet_data = await self._received_packets.get()

        # read JSON from bytes
        json_string = base64.b64decode(packet_data)
        data = json.loads(json_string)

        # deserialize
        return self.deserialize(data)

    async def close(self: "AsyncSocketClient"):
        self.writer.close()
        try:
            await asyncio.wait_for(self.writer.wait_closed(), timeout=10)
        except asyncio.TimeoutError:
            pass
        self._keep_alive_task.cancel()

import asyncio
import base64
import json
import struct
from abc import ABC
from typing import TYPE_CHECKING, Type, Dict
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
        return cls(reader, writer)

    @property
    def is_connected(self: "AsyncSocketClient") -> bool:
        return self.reader.at_eof()

    def add_serializer(self: "AsyncSocketClient", serializer: Type[SerializerType]):
        if not issubclass(serializer, SerializerType):
            raise ValueError('Unsupported serializer type')
        data_type = self.get_data_type_str(serializer.INSTANCE)
        serializer.default = self
        self.custom_serializers[data_type] = serializer

    async def receive(self: "AsyncSocketClient"):
        """ Wait and Receive Packet """

        async with self._lock_recv:
            # receive packet length
            packet_length = await self._recv(4)
            packet_length = struct.unpack("!I", packet_length)[0]

            # receive a full packet
            packet_data = await self._recv(packet_length)

            # read JSON from bytes
            json_string = base64.b64decode(packet_data)
            data = json.loads(json_string)

            # send act signal
            await self._send_act()

            # deserialize
            return self.deserialize(data)

    async def send(self: "AsyncSocketClient", **data):
        """ Send Packet """

        async with self._lock_send:
            # serialize
            data = self.serialize(data)

            # convert to JSON object
            json_data = json.dumps(data)

            # convert to bytes
            encoded_json_data = base64.b64encode(json_data.encode('utf-8'))

            # Send JSON response
            packet_length = struct.pack("!I", len(encoded_json_data))
            self.writer.write(packet_length)
            self.writer.write(encoded_json_data)
            await self.writer.drain()

            # waiting for act signal
            await self._wait_act()

    async def close(self: "AsyncSocketClient"):
        self.writer.close()
        try:
            await asyncio.wait_for(self.writer.wait_closed(), timeout=10)
        except asyncio.TimeoutError:
            pass
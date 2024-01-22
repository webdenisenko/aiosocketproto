import asyncio
import os
import random
import string
import time
import traceback
from datetime import datetime

import src as aiosocketproto
from src.client.serializer import SerializerType


class DatetimeSerializer(SerializerType):
    INSTANCE = datetime

    @classmethod
    def serialize(cls, date: datetime) -> str:
        return str(date)

    @classmethod
    def deserialize(cls, date: str) -> datetime:
        return datetime.fromisoformat(date)


class UnsupportedTypeExample:
    pass


class Example:
    TEST_TYPES = {
        'int': lambda: random.randint(100, 999),
        'float': lambda: float('0.{}'.format(random.randint(100, 999))),
        'str': lambda: ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5)),
        'bool': lambda: bool(random.randint(0, 1)),
        'bytes': lambda: os.urandom(8),
        'bytearray': lambda: bytearray(os.urandom(8)),
        'list': lambda: [random.randint(100, 999), random.randint(100, 999), random.randint(100, 999)],
        'tuple': lambda: tuple([random.randint(100, 999), random.randint(100, 999), random.randint(100, 999)]),
        'set': lambda: {random.randint(100, 999), random.randint(100, 999), random.randint(100, 999)},
        'dict': lambda: {'a': random.randint(100, 999), 'b': random.randint(100, 999), 'c': random.randint(100, 999)},
        'datetime': lambda: datetime.now(),
        # 'unsupported': lambda: UnsupportedTypeExample(), # raise ValueError: unsupported data type: <class '__main__.UnsupportedTypeExample'>
    }

    def __init__(self):
        self.server_created = asyncio.Event()
        self.start_timestamp = None

    async def connection(self, socket: aiosocketproto.AsyncSocketClient):
        print('Client connected!')

        socket.add_serializer(DatetimeSerializer)

        print('Benchmark:')
        for type_name, value in self.TEST_TYPES.items():
            try:
                value = value()
                self.start_timestamp = time.time()
                await socket.send(data=value)
            except asyncio.exceptions.CancelledError:
                pass
            except:
                traceback.print_exc()

    async def create_server(self):
        try:
            server = await aiosocketproto.start_server([9999], self.connection)
            self.server_created.set()
            await server.idle()
        except asyncio.exceptions.CancelledError:
            pass

    async def client_connect(self):
        client = await aiosocketproto.connect('0.0.0.0', 9999)
        client.add_serializer(DatetimeSerializer)

        for type_name, value in self.TEST_TYPES.items():
            data = await client.receive()
            print(type_name.rjust(20), time.time() - self.start_timestamp, data['data'])

    async def run(self):
        server_task = asyncio.create_task(self.create_server())
        await self.server_created.wait()
        await self.client_connect()


asyncio.run(Example().run(), debug=True)
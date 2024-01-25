from aiosocketproto.client import AsyncSocketClient
from aiosocketproto.client.serializer import SerializerType
from aiosocketproto.server import AsyncSocketServer

connect = AsyncSocketClient.connect
start_server = AsyncSocketServer.start

__version__ = '0.0.15'

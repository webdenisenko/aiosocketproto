import asyncio

from .methods import Methods
from .processor import Processor
from .serializer import Serializer


class AsyncSocketClient(Serializer, Processor, Methods):
    SIGNAL_ACT = -100
    SIGNAL_PING = -200
    ACT_TIMEOUT = 15

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    is_connected: bool

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        super().__init__()
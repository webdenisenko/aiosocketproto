import asyncio
import logging
import os

from .methods import Methods
from .processor import Processor
from .serializer import Serializer


class AsyncSocketClient(Serializer, Processor, Methods):
    SIGNAL_ACT = -100
    SIGNAL_PING = -200
    ACT_TIMEOUT = 15
    PING_INTERVAL = 30

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    is_connected: bool

    logger: logging.Logger

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, debug_mode: bool = False):
        self.reader = reader
        self.writer = writer

        rand_session_id = os.urandom(2).hex()
        self.logger = logging.getLogger('{}.{}'.format(__name__, rand_session_id))
        log_format = '%(asctime)s :: %(levelname)s :: [{}] %(message)s'.format(rand_session_id)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(log_format)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        if debug_mode:
            self.logger.setLevel('DEBUG')
        else:
            self.logger.setLevel('ERROR')

        super().__init__()
import asyncio


class SendPacket:
    data: bytes
    sent: asyncio.Event

    def __init__(self, data: bytes):
        self.data = data
        self.sent = asyncio.Event()

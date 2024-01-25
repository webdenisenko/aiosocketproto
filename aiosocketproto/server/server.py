import asyncio
from typing import List, Callable

from .processor import Processor


class AsyncSocketServer(Processor):
    port: int
    server: asyncio.Server
    sessions: List[asyncio.Task]
    connection_handler: Callable
    debug_mode: bool

    @classmethod
    async def start(cls, ports_range: List[int], connection_handler: Callable, debug_mode: bool = False):
        """ Start a server with given ports range """

        # constructor
        server_wrap = cls()
        server_wrap.sessions = []
        server_wrap.connection_handler = connection_handler
        server_wrap.debug_mode = debug_mode

        # find free port in range
        for port in ports_range:
            try:

                # run server
                protocol_server = await asyncio.start_server(server_wrap._connection_handler_wrapper, '0.0.0.0', port)
                server_wrap.port = port
                server_wrap.server = protocol_server

                return server_wrap

            except OSError:
                pass
        else:
            raise RuntimeError(f'all ports in range {ports_range} are busy')

    async def idle(self):
        """ Keep the Server active """
        await self.server.serve_forever()

    async def close(self):
        """ Close the server """

        try:
            # close server
            self.server.close()

            # waiting for closing
            await asyncio.wait_for(self.server.wait_closed(), timeout=10)
        except asyncio.TimeoutError:
            pass

        # force cancel of not closed tasks
        [task.done() or task.cancel() for task in self.sessions]
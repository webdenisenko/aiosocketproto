# Async Socket Protocol

Just Simple and Universal socket protocol written in Python.

> After writing the socket protocol class for the tenth time, I wanted to make a universal package for all my projects. I will be glad to support and advice!

## Features

- Client side
- Server side
- Safe `Kepp Alive` control
- Default serializer works with `int, float, str, bytes, bytearray, list, dict, tuple, set` types
- Ability to easily add your own serializers

## How To Install

Just use pip from your command line:
```
pip install aiosocketproto
```

## How To Use

### Create server
```
import asyncio
import aiosocketproto


async def connection(socket: aiosocketproto.AsyncSocketClient):
    print('Client connected!')
    await server.receive()
    await server.send(data='example str data')


async def create_server():
    server = await aiosocketproto.start_server([9999], connection)
    await server.idle() # keep alive


asyncio.run(create_server())
```

In this case, the server will be launched at `0.0.0.0:9999`
You can pass a range of ports (example: `range(8888, 9999)`), and the server will choose the first available one.

### Connect as client
```
import asyncio
import aiosocketproto


async def connect():
    server = await aiosocketproto.connect('127.0.0.1', 9999)
    await server.send(data=[123, 'abc', b'somebytes'], second_arg=0.123)
    await server.receive()


asyncio.run(connect())
```

Full example with custom serializers see in `example.py`
"""Persistent NAD ASCII transport; no scheduled status queries."""
import asyncio
import logging
import re
import socket
from contextlib import suppress

_LOG = logging.getLogger(__name__)
QUERIES = ('Main.Power?', 'Main.Volume?', 'Main.Mute?', 'Main.Source?')

class NadConnection:
    def __init__(self, host, port, notify):
        self.host, self.port, self.notify = host, port, notify
        self.writer = None
        self.values = {}
        self.connected = False
        self.lock = asyncio.Lock()

    async def send(self, *commands):
        async with self.lock:
            writer = self.writer
            if not writer or writer.is_closing():
                raise ConnectionError('NAD is disconnected')
            for command in commands:
                writer.write((command + '\r').encode('ascii'))
                await asyncio.wait_for(writer.drain(), 5)
                await asyncio.sleep(0.08)

    def process(self, line):
        match = re.fullmatch(r'Main\.(Power|Volume|Mute|Source|Model)=(.+)', line.strip(), re.I)
        if not match:
            return False
        key, value = match.group(1).lower(), match.group(2).strip()
        previous = self.values.get(key)
        if key == 'volume':
            if not re.fullmatch(r'-?\d+(?:\.\d+)?%?', value):
                return False
        elif key in ('power', 'mute') and value.lower() not in ('on', 'off'):
            return False
        elif key == 'source' and not value.isdigit():
            return False
        self.values[key] = value
        self.notify()
        return key == 'power' and value.lower() == 'on' and (previous or '').lower() == 'off'

    async def run(self):
        delay = 2
        while True:
            writer = None
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), 8)
                sock = writer.get_extra_info('socket')
                if sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for opt, val in [('TCP_KEEPIDLE', 60), ('TCP_KEEPINTVL', 15), ('TCP_KEEPCNT', 3)]:
                        if hasattr(socket, opt):
                            with suppress(OSError):
                                sock.setsockopt(socket.IPPROTO_TCP, getattr(socket, opt), val)
                self.writer = writer
                self.values.clear()
                self.connected = True
                self.notify()
                await self.send(*QUERIES)
                delay = 2
                pending = ''
                while True:
                    data = await reader.read(4096)
                    if not data:
                        raise ConnectionError('NAD closed connection')
                    pending += data.decode('ascii', errors='ignore')
                    parts = re.split(r'[\r\n]', pending)
                    pending = parts.pop()
                    if len(pending) > 8192:
                        pending = ''
                    wake = False
                    for line in parts:
                        wake = self.process(line) or wake
                    if wake:
                        await self.send('Main.Volume?', 'Main.Mute?', 'Main.Source?')
            except asyncio.CancelledError:
                raise
            except (OSError, TimeoutError) as exc:
                _LOG.debug('NAD connection interrupted: %s', exc)
            finally:
                self.connected = False
                self.writer = None
                self.values.clear()
                self.notify()
                if writer:
                    writer.close()
                    with suppress(OSError, TimeoutError):
                        await asyncio.wait_for(writer.wait_closed(), 2)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

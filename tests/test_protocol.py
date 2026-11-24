import asyncio
import unittest
from custom_components.nad_push.protocol import NadConnection, QUERIES

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_push_and_wake(self):
        received = []
        ready = asyncio.Event()
        async def server(reader, writer):
            try:
                for _ in QUERIES:
                    received.append((await reader.readuntil(b"\r")).decode().strip())
                writer.write(b"\rMain.Model=C388\rMain.Power=Off\rMain.Vol")
                await writer.drain()
                writer.write(b"ume=48%\r\nMain.Power=On\rMain.Volume=-35.5\rMain.Mute=Off\rMain.Source=9\r")
                await writer.drain()
                for _ in range(3):
                    received.append((await reader.readuntil(b"\r")).decode().strip())
                ready.set()
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()
        listener = await asyncio.start_server(server, '127.0.0.1', 0)
        conn = NadConnection('127.0.0.1', listener.sockets[0].getsockname()[1], lambda: None)
        task = asyncio.create_task(conn.run())
        try:
            await asyncio.wait_for(ready.wait(), 5)
            self.assertEqual(received, list(QUERIES)+list(QUERIES[1:]))
            self.assertEqual(conn.values['volume'], '-35.5')
            self.assertEqual(conn.values['source'], '9')
            self.assertEqual(conn.values['power'], 'On')
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            listener.close()
            await listener.wait_closed()

    async def test_invalid_reports(self):
        conn = NadConnection('127.0.0.1', 23, lambda: None)
        for line in ['Main.Volume=garbage', 'Main.Source=no', 'Main.Power=maybe']:
            self.assertFalse(conn.process(line))
        self.assertEqual(conn.values, {})

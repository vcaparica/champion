"""
game/network.py - Client-side WebSocket connection
====================================================
Manages connection to the Champion game server.
"""
import json
import asyncio
import threading
from typing import Optional


class GameClient:
    """WebSocket client for connecting to the Champion server."""

    def __init__(self):
        self._ws = None
        self._connected = False
        self._message_queue: list[dict] = []
        self._loop = None
        self._thread = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, url: str = "ws://localhost:8000/ws") -> bool:
        """Connect to the server. Runs the event loop in a background thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, args=(url,), daemon=True)
        self._thread.start()
        # Wait briefly for connection
        import time
        for _ in range(50):
            if self._connected:
                return True
            time.sleep(0.1)
        return self._connected

    def _run_loop(self, url: str):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect(url))

    async def _connect(self, url: str):
        try:
            import websockets
            self._ws = await websockets.connect(url)
            self._connected = True
            # Start receiver
            asyncio.ensure_future(self._receiver(), loop=self._loop)
            # Keep loop alive
            while self._connected:
                await asyncio.sleep(0.1)
        except Exception:
            self._connected = False

    async def _receiver(self):
        """Receive messages from server and queue them."""
        try:
            while self._connected:
                data = await self._ws.recv()
                message = json.loads(data)
                self._message_queue.append(message)
        except Exception:
            self._connected = False

    def send(self, message: dict) -> None:
        """Send a message to the server."""
        if not self._connected or not self._ws:
            return
        data = json.dumps(message)
        asyncio.run_coroutine_threadsafe(self._ws.send(data), self._loop)

    def receive(self) -> Optional[dict]:
        """Get the next queued message from the server, or None."""
        if self._message_queue:
            return self._message_queue.pop(0)
        return None

    def has_messages(self) -> bool:
        """Check if there are queued messages."""
        return len(self._message_queue) > 0

    def close(self) -> None:
        """Disconnect from the server."""
        self._connected = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

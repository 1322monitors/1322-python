"""Binance Square: stream posts and pin changes for tracked creators.

Requires a Binance Square API key from https://1322.io. The WebSocket
path/key are fetched automatically from GET /v1/dashboard.

    export BINANCE_API_KEY=YOUR_API_KEY_HERE
    python binance_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client
from client1322.platforms.binance import BinancePinUpdateEvent, BinancePostEvent

API_KEY = os.environ.get("BINANCE_API_KEY", "YOUR_API_KEY_HERE")


async def main() -> None:
    async with Client(platform="binance", api_key=API_KEY) as client:
        dash = await client.dashboard()
        print(f"Tracking: {dash.get('tracked', [])}")

        async for event in client.stream():
            if isinstance(event, BinancePostEvent):
                post = event.post
                tendency = post.get("tendency") or "neutral"
                pairs = ", ".join(post.get("coin_pairs") or [])
                print(f"[post] @{post.get('username')} ({tendency}) {pairs}: {post.get('text', '')[:120]}")
            elif isinstance(event, BinancePinUpdateEvent):
                pin = event.pin
                print(f"[pin change] @{pin.get('username')}: +{len(pin.get('added') or [])} -{len(pin.get('removed') or [])}")


if __name__ == "__main__":
    asyncio.run(main())

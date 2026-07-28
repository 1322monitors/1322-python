"""Truth Social: stream posts for your tracked accounts.

Requires a Truth Social API key plus the ws_path/ws_key shown in your
1322 dashboard configuration (1322 does not expose a REST endpoint that
returns these for Truth Social, unlike News/Binance Square).

    export TRUTH_API_KEY=YOUR_API_KEY_HERE
    export TRUTH_WS_PATH=YOUR_WS_PATH_HERE
    export TRUTH_WS_KEY=YOUR_WS_KEY_HERE
    python truth_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client

API_KEY = os.environ.get("TRUTH_API_KEY", "YOUR_API_KEY_HERE")
WS_PATH = os.environ.get("TRUTH_WS_PATH", "YOUR_WS_PATH_HERE")
WS_KEY = os.environ.get("TRUTH_WS_KEY", "YOUR_WS_KEY_HERE")


async def main() -> None:
    async with Client(
        platform="truth", api_key=API_KEY, ws_path=WS_PATH, ws_key=WS_KEY
    ) as client:
        limits = await client.limits()
        print(f"Tracking {limits['current_tracked']}/{limits['max_tracked']} accounts.")

        async for post in client.stream():
            label = "retruth" if post.is_retruth else ("quote" if post.is_quote else "post")
            print(f"[{label}] @{post.username}: {post.text[:120]}")
            if post.media:
                print(f"  media: {[m.get('url') for m in post.media]}")


if __name__ == "__main__":
    asyncio.run(main())

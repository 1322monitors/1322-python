"""News: stream articles from your subscribed feeds.

Requires a News API key from https://1322.io. The WebSocket path/key are
fetched automatically from GET /v1/dashboard -- no need to pass them.

    export NEWS_API_KEY=YOUR_API_KEY_HERE
    python news_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client

API_KEY = os.environ.get("NEWS_API_KEY", "YOUR_API_KEY_HERE")


async def main() -> None:
    async with Client(platform="news", api_key=API_KEY) as client:
        dash = await client.dashboard()
        print(f"Subscribed feeds: {dash.get('feeds', [])}")

        # Add a feed if it isn't already subscribed. Feed names are listed at
        # https://1322.io/docs under "Available Feeds".
        if "BBC News" not in dash.get("feeds", []):
            await client.subscribe("BBC News")

        async for article in client.stream():
            print(f"[{article.feed}] {article.title}")
            print(f"  {article.url}")


if __name__ == "__main__":
    asyncio.run(main())

"""Instagram: stream posts, reels, stories, and carousels for tracked accounts.

Requires an Instagram API key from https://1322.io (the same key is used
for both REST and the WebSocket connection).

    export INSTAGRAM_API_KEY=YOUR_API_KEY_HERE
    python instagram_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client

API_KEY = os.environ.get("INSTAGRAM_API_KEY", "YOUR_API_KEY_HERE")


async def main() -> None:
    async with Client(platform="instagram", api_key=API_KEY) as client:
        tracked = await client.list_tracked()
        print(f"Tracking: {tracked.get('tracked', [])}")

        async for post in client.stream():
            tags = []
            if post.is_collab:
                tags.append(f"collab with {', '.join(post.collab_with or [])}")
            if post.is_paid_partnership:
                tags.append("paid partnership")
            suffix = f" ({'; '.join(tags)})" if tags else ""
            print(f"[{post.post_type}] @{post.username}: {post.text[:120]}{suffix}")


if __name__ == "__main__":
    asyncio.run(main())

"""YouTube: consume the upload / upgrade / deletion event stream.

Unlike the other five platforms, 1322's public docs do not publish a fixed
YouTube WebSocket path or a REST tracked-account API (see
client1322.platforms.youtube for details), so you must copy the full
WebSocket URL from your 1322 dashboard configuration.

    export YOUTUBE_API_KEY=YOUR_API_KEY_HERE
    export YOUTUBE_WS_URL=YOUR_WS_URL_HERE
    python youtube_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client
from client1322.platforms.youtube import DeletionMessage, UploadMessage, UpgradeMessage

API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")
WS_URL = os.environ.get("YOUTUBE_WS_URL", "YOUR_WS_URL_HERE")


async def main() -> None:
    async with Client(platform="youtube", api_key=API_KEY, ws_url=WS_URL) as client:
        async for event in client.stream():
            if isinstance(event, UploadMessage):
                print(f"[upload:{event.subtype}] {event.channel['name']}: {event.video['title']}")
            elif isinstance(event, UpgradeMessage):
                print(f"[upgrade] video {event.upgrade['video_id']} -> {event.upgrade['url']}")
            elif isinstance(event, DeletionMessage):
                print(f"[deletion] video {event.video['id']} from {event.channel['name']}")


if __name__ == "__main__":
    asyncio.run(main())

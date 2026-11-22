"""YouTube: consume the upload / upgrade / deletion event stream.

Take ws_url and ws_key from GET https://youtube.1322.io/v1/dashboard (they
are also on the API access page in your 1322 dashboard). The stream URL is
the ws_url with ?key=<ws_key> appended. This client does not wrap YouTube
REST yet (track / untrack / list are documented at
https://1322.io/docs/youtube).

    export YOUTUBE_API_KEY=YOUR_API_KEY_HERE
    export YOUTUBE_WS_URL=YOUR_WS_URL_HERE
    export YOUTUBE_WS_KEY=YOUR_WS_KEY_HERE
    python youtube_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client
from client1322.platforms.youtube import DeletionMessage, UploadMessage, UpgradeMessage

API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")
WS_URL = os.environ.get("YOUTUBE_WS_URL", "YOUR_WS_URL_HERE")
WS_KEY = os.environ.get("YOUTUBE_WS_KEY", "YOUR_WS_KEY_HERE")

# Pass a URL that already carries ?key= unchanged; otherwise append the WS key.
STREAM_URL = WS_URL if "key=" in WS_URL else f"{WS_URL}?key={WS_KEY}"


async def main() -> None:
    async with Client(platform="youtube", api_key=API_KEY, ws_url=STREAM_URL) as client:
        async for event in client.stream():
            if isinstance(event, UploadMessage):
                print(f"[upload:{event.subtype}] {event.channel['name']}: {event.video['title']}")
            elif isinstance(event, UpgradeMessage):
                print(f"[upgrade] video {event.upgrade['video_id']} -> {event.upgrade['url']}")
            elif isinstance(event, DeletionMessage):
                print(f"[deletion] video {event.video['id']} from {event.channel['name']}")


if __name__ == "__main__":
    asyncio.run(main())

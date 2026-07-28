"""X / Twitter: stream tweet events for your tracked accounts.

Requires an X (Normal or Ultimate tier) API key from https://1322.io.
Set X_API_KEY (and optionally X_TIER=ultimate) in the environment, or edit
the constants below directly.

    export X_API_KEY=YOUR_API_KEY_HERE
    python x_example.py
"""

from __future__ import annotations

import asyncio
import os

from client1322 import Client, TweetMerger
from client1322.platforms.x import DeletedTweet, MiniTweetUpdate, TweetFull, TweetUpdate

API_KEY = os.environ.get("X_API_KEY", "YOUR_API_KEY_HERE")
TIER = os.environ.get("X_TIER", "normal")  # "normal" or "ultimate"


async def main() -> None:
    merger = TweetMerger()  # additive merge across mini -> update -> full stages

    async with Client(platform="x", api_key=API_KEY, tier=TIER) as client:
        tracked = await client.list_tracked()
        print(f"Currently tracking {len(tracked.get('trackedAccounts', []))} account(s).")

        async for event in client.stream():
            if isinstance(event, (MiniTweetUpdate, TweetUpdate, TweetFull)):
                merged = merger.merge(event.tweet)
                author = merged["author"].get("handle", "?")
                text = merged["body"]["text"]
                print(f"[{event.type}] @{author}: {text[:120]}")
            elif isinstance(event, DeletedTweet):
                print(f"[deleted] tweet {event.tweet['id']}")
            else:
                print(f"[{event.type}] {event}")


if __name__ == "__main__":
    asyncio.run(main())

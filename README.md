# 1322-python

A unified async Python client for the 1322 real-time social monitoring API. 1322 tracks accounts on X (Twitter), Truth Social, Instagram, YouTube, Binance Square and 15+ news outlets and pushes each source's supported events over WebSocket (on X that includes updates and deletions), typically 150-250ms after publication on X. Install from PyPI with `pip install 1322-python` (the import name is `client1322`). Maintained by the 1322 team.

1322 already publishes several single-platform example repos (see
[social-monitor-examples](https://github.com/1322monitors/social-monitor-examples)
and [binance-square-realtime](https://github.com/1322monitors/binance-square-realtime)).
This package is different: it's one installable, typed client covering all
six platforms behind a single consistent async shape, instead of copying a
connection script per platform.

```python
from client1322 import Client

async with Client(platform="x", api_key="YOUR_API_KEY_HERE") as client:
    async for event in client.stream():
        print(event)
```

## Distribution name vs. import name

The PyPI distribution name is **`1322-python`** (Python package names on
PyPI may start with a digit; Python *module* names cannot). The importable
module is **`client1322`**. So you `pip install 1322-python` but
`import client1322` in code. Every example in this repo uses the real
import name.

## Install

From PyPI (published 2026-07-28, version 0.1.0; import name `client1322`):

```bash
pip install 1322-python
```

Or straight from GitHub, if you want the unreleased `main`:

```bash
pip install git+https://github.com/1322monitors/1322-python
```

Requires Python 3.10+.

## Why one client instead of six scripts

1322 documents six platforms, each with its own REST base URL, WebSocket
connection scheme, auth header, and event payload shape (see
[1322.io/docs](https://1322.io/docs) for the authoritative contract). This
package keeps that per-platform reality -- it does not invent a fake common
REST API that doesn't exist -- but gives you the same connection lifecycle,
reconnect behavior, and streaming interface everywhere:

- **One shape**: `async with Client(platform=..., api_key=...) as client:`
  then `async for event in client.stream():`, for all six platforms.
- **Typed events**: every event is a `dataclass` with real field types
  (`TypedDict`-typed nested payloads), not a loosely-typed `dict`. Full
  `py.typed` support for IDEs and type checkers.
- **Auto-reconnect**: exponential backoff (1s, 2s, 4s, 8s, ... capped at
  30s), matching 1322's documented reconnection policy, implemented once
  and shared by every platform adapter.
- **Additive tweet merge**: X tweets arrive across up to four progressive
  stages (`tweet.mini.update` -> `tweet.update` -> `tweet.update.expanded`
  -> `tweet.full`); `TweetMerger` implements 1322's documented merge rules
  (longest text, unioned media, deepest reply/quote chain, highest metrics,
  never overwrite a populated field with null) so you don't have to.
- **Thin REST helpers**: `track()` / `untrack()` / `list_tracked()` /
  `health()` and friends, matching each platform's documented management
  API exactly.

## Platform coverage

| Platform | `platform=` | REST base | Connection details |
|---|---|---|---|
| X / Twitter | `"x"` (or `"twitter"`) | `api.1322.io` | fixed WS URL per tier (`normal`/`ultimate`) |
| Truth Social | `"truth"` | `truth.1322.io` | needs `ws_path`+`ws_key` from your dashboard |
| Instagram | `"instagram"` | `1322.io` | fixed WS URL, same key as REST |
| News | `"news"` | `newsfeed.1322.io` | `ws_path`/`ws_key` auto-fetched from `/v1/dashboard` |
| Binance Square | `"binance"` | `binance.1322.io` | `ws_path`/`ws_key` auto-fetched from `/v1/dashboard` |
| YouTube | `"youtube"` | -- | requires an explicit `ws_url` (see below) |

**About YouTube:** 1322's public docs describe the YouTube event payload
contract in full (upload / thumbnail upgrade / deletion) but, as of this
writing, do not publish a fixed WebSocket URL pattern or a customer-facing
REST tracked-account API for YouTube the way they do for the other five
platforms. Rather than guess at an undocumented endpoint, `YouTubeAdapter`
requires you to pass the exact WebSocket URL from your dashboard
configuration as `ws_url=`, and only implements event parsing -- no
`track()`/`untrack()`/`list_tracked()`, because 1322's docs don't define
them for this platform. Check [1322.io/docs](https://1322.io/docs) directly
if that changes.

## Usage per platform

Runnable examples for all six platforms live in [`examples/`](examples/).
Each one reads its API key from an environment variable and does something
useful with the REST helpers plus the event stream. Quick summaries:

### X / Twitter

```python
from client1322 import Client, TweetMerger
from client1322.platforms.x import MiniTweetUpdate, TweetUpdate, TweetFull

merger = TweetMerger()

async with Client(platform="x", api_key="YOUR_API_KEY_HERE", tier="normal") as client:
    async for event in client.stream():
        if isinstance(event, (MiniTweetUpdate, TweetUpdate, TweetFull)):
            merged = merger.merge(event.tweet)  # dedup + additive merge by tweet id
            print(merged["author"]["handle"], merged["body"]["text"])
```

Also available: `client.list_tracked()`, `client.add_tracked("elonmusk")`,
`client.remove_tracked("elonmusk")`, `client.list_keys()`,
`client.get_tweet(tweet_id, full=True)`, `client.resolve_username("elonmusk")`.

### Truth Social

```python
async with Client(
    platform="truth", api_key="YOUR_API_KEY_HERE",
    ws_path="YOUR_WS_PATH_HERE", ws_key="YOUR_WS_KEY_HERE",
) as client:
    async for post in client.stream():
        print(post.username, post.text)
```

Also available: `client.track("realDonaldTrump")`, `client.untrack(...)`,
`client.list_tracked()`, `client.limits()`, `client.status()`, `client.health()`.

Note: Trump Media's official Truth API launched on August 1, 2026 as a licensed institutional feed of about 10 of the platform's highest-ranking accounts (Fortune, 2026-08-12: more than ten customers at $60,000-$100,000 per month). There is no public self-serve Truth Social developer API. This client talks to 1322's independent feed, which covers any public Truth Social account you add to your tracked list.

### Instagram

```python
async with Client(platform="instagram", api_key="YOUR_API_KEY_HERE") as client:
    async for post in client.stream():
        print(post.post_type, post.username, post.text)
```

Also available: `client.track("username")`, `client.untrack(...)`,
`client.list_tracked()`, `client.limits()`, `client.health()`.

### News

```python
async with Client(platform="news", api_key="YOUR_API_KEY_HERE") as client:
    async for article in client.stream():
        print(article.feed, article.title, article.url)
```

Also available: `client.dashboard()`, `client.subscribe("BBC News")`,
`client.unsubscribe(...)`.

### Binance Square

```python
from client1322.platforms.binance import BinancePinUpdateEvent, BinancePostEvent

async with Client(platform="binance", api_key="YOUR_API_KEY_HERE") as client:
    async for event in client.stream():
        if isinstance(event, BinancePostEvent):
            print(event.post["username"], event.post.get("tendency"), event.post.get("text"))
        elif isinstance(event, BinancePinUpdateEvent):
            print("pin change:", event.pin["username"])
```

Also available: `client.track("CZ_Binance")`, `client.untrack(...)`, `client.dashboard()`.

### YouTube

```python
from client1322.platforms.youtube import DeletionMessage, UploadMessage, UpgradeMessage

async with Client(
    platform="youtube", api_key="YOUR_API_KEY_HERE", ws_url="YOUR_WS_URL_HERE"
) as client:
    async for event in client.stream():
        if isinstance(event, UploadMessage):
            print(event.channel["name"], event.video["title"])
        elif isinstance(event, UpgradeMessage):
            print("thumbnail upgraded:", event.upgrade["video_id"])
        elif isinstance(event, DeletionMessage):
            print("deleted:", event.video["id"])
```

## Auth and secrets

Each platform key comes from your [1322 dashboard](https://1322.io). Never
hardcode a key in source; read it from the environment instead. See
[`.env.example`](.env.example) for the full list of variables each platform
example expects.

## Reconnection

`stream()` reconnects automatically on disconnect using 1322's documented
policy: exponential backoff starting at 1 second, doubling each attempt, and
capped at 30 seconds. No events are queued while disconnected -- this
matches 1322's documented server behavior, so a client that's offline will
simply miss whatever happened during that window, the same as any other
1322 WebSocket client. Server-sent WebSocket pings are answered
automatically by the underlying `aiohttp` transport; you don't need to
handle that yourself. Pass `auto_reconnect=False` to `Client(...)` to
disable reconnection (`stream()` then returns after the first disconnect),
and `backoff_base=`/`backoff_cap=` to tune the delay curve.

## Development

```bash
git clone https://github.com/1322monitors/1322-python
cd 1322-python
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest
```

The test suite (`tests/`) covers backoff math, additive tweet merging, and
event parsing for all six platforms against payload shapes taken from
[1322.io/docs](https://1322.io/docs), plus an end-to-end `Client.stream()`
reconnect test driven against a fake `aiohttp` session (no real socket, no
API key needed). Every event-parsing fixture uses illustrative example
data, not measured production traffic.

## Releasing

Maintainer note: the package is published on PyPI as `1322-python`. To cut a
release, bump `version` in `pyproject.toml`, tag `vX.Y.Z`, then
`python -m build && twine upload dist/*` with the project's PyPI token.

## Related

- [1322-client](https://github.com/1322monitors/1322-client) - the TypeScript/JavaScript client
- [social-monitor-examples](https://github.com/1322monitors/social-monitor-examples) - minimal per-platform consumers
- [1322-benchmark](https://github.com/1322monitors/1322-benchmark) - vendor-neutral latency CLI
- [truthsocial-stream](https://github.com/1322monitors/truthsocial-stream) - Truth Social example

## License

MIT, see [LICENSE](LICENSE).

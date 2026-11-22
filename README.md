# 1322-python

An async Python client for 1322's real-time feeds for X (Twitter), Truth Social, Instagram, YouTube, Binance Square and News: six of 1322's eight sources. Each source has its own WebSocket feed and key, managed in one 1322 dashboard; this package connects to each of them through the same async interface, with typed events, auto-reconnect and tracked-list REST helpers. Install from PyPI with `pip install 1322-python` (the import name is `client1322`). Maintained by the 1322 team.

TikTok and FOMO are not in this client yet; see [1322.io/docs/tiktok](https://1322.io/docs/tiktok) and [1322.io/docs/fomo](https://1322.io/docs/fomo).

Plans from $79/month (FOMO Lite); X from $250/month for 100 accounts. A one-day evaluation is available on request, reviewed by the team, no card.

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

From PyPI:

```bash
pip install 1322-python
```

Or straight from GitHub, if you want the unreleased `main`:

```bash
pip install git+https://github.com/1322monitors/1322-python
```

Requires Python 3.10+.

## Why a client instead of per-source scripts

1322 documents each source separately: its own REST base URL, WebSocket
URL, key and event payload shape (see [1322.io/docs](https://1322.io/docs)
for the authoritative contract). This package keeps that per-source
reality (it does not invent a common REST API that doesn't exist, and every
source still connects to its own WebSocket feed with its own key) but gives
you the same connection lifecycle, reconnect behavior and streaming
interface for each source it covers:

- **One shape**: `async with Client(platform=..., api_key=...) as client:`
  then `async for event in client.stream():`, for every covered source.
- **Typed events**: every event is a `dataclass` with real field types
  (`TypedDict`-typed nested payloads), not a loosely-typed `dict`. Full
  `py.typed` support for IDEs and type checkers.
- **Auto-reconnect**: exponential backoff (1s, 2s, 4s, 8s, ... capped at
  30s), matching 1322's documented reconnection policy, implemented once
  and shared by every source adapter.
- **Additive tweet merge**: X tweets arrive across up to four progressive
  stages (`tweet.mini.update` -> `tweet.update` -> `tweet.update.expanded`
  -> `tweet.full`); `TweetMerger` implements 1322's documented merge rules
  (longest text, unioned media, deepest reply/quote chain, highest metrics,
  never overwrite a filled field with an empty one) by `tweet.id` so you
  don't have to.
- **Thin REST helpers**: `track()` / `untrack()` / `list_tracked()` /
  `health()` and friends, matching each source's documented management
  API (YouTube REST is not wrapped yet, see below).

## Source coverage

| Source | `platform=` | REST base | WebSocket connection | Docs |
|---|---|---|---|---|
| X / Twitter | `"x"` (or `"twitter"`) | `api.1322.io` | fixed URL per stream (`normal` / `ultimate`), key in the `X-API-Key` header | [docs/x](https://1322.io/docs/x) |
| Truth Social | `"truth"` | `truth.1322.io` | pass `ws_path` + `ws_key` from the API access page | [docs/truth](https://1322.io/docs/truth) |
| Instagram | `"instagram"` | `1322.io` | `wss://1322.io/IG?key=<api_key>`, the same key as REST | [docs/instagram](https://1322.io/docs/instagram) |
| YouTube | `"youtube"` | `youtube.1322.io` (not wrapped yet) | pass `ws_url` with `?key=<ws_key>` from `GET /v1/dashboard` | [docs/youtube](https://1322.io/docs/youtube) |
| Binance Square | `"binance"` | `binance.1322.io` | `ws_path` / `ws_key` fetched from `GET /v1/dashboard` | [docs/binance](https://1322.io/docs/binance) |
| News | `"news"` | `newsfeed.1322.io` | `ws_path` / `ws_key` fetched from `GET /v1/dashboard` | [docs/news](https://1322.io/docs/news) |
| TikTok | not in this client yet | | | [docs/tiktok](https://1322.io/docs/tiktok) |
| FOMO | not in this client yet | | | [docs/fomo](https://1322.io/docs/fomo) |

**About YouTube:** the client wraps the YouTube WebSocket stream and its
three event types (`upload`, `upgrade`, `deletion`). It does not wrap
YouTube REST yet: track, untrack and list (`POST /v1/track`,
`POST /v1/untrack`, `GET /v1/list`) and `GET /v1/dashboard` are documented
at [1322.io/docs/youtube](https://1322.io/docs/youtube); call them with
your own HTTP client for now. The adapter also does not fetch the stream
URL for you: take `ws_url` and `ws_key` from `GET /v1/dashboard` (or the
API access page) and pass `ws_url="<ws_url>?key=<ws_key>"`.

## Usage per source

Runnable examples for all six covered sources live in
[`examples/`](https://github.com/1322monitors/1322-python/tree/main/examples). Each one reads its key from an environment
variable and consumes the event stream; all but YouTube also call a REST
helper first. Quick summaries:

### X / Twitter

```python
from client1322 import Client, TweetMerger
from client1322.platforms.x import MiniTweetUpdate, TweetFull, TweetUpdate, TweetUpdateExpanded

merger = TweetMerger()

async with Client(platform="x", api_key="YOUR_API_KEY_HERE", tier="normal") as client:
    async for event in client.stream():
        if isinstance(event, (MiniTweetUpdate, TweetUpdate, TweetUpdateExpanded, TweetFull)):
            merged = merger.merge(event.tweet)  # dedupe + additive merge by tweet.id
            print(merged["author"]["handle"], merged["body"]["text"])
```

`tweet.type` is `TWEET`, `RETWEET`, `QUOTE` or `REPLY`, and
`tweet.created_at` is Unix milliseconds. Deletions arrive as
`DeletedTweet` (`tweet.deleted`). On a hybrid plan, run one client per
stream (`tier="normal"` and `tier="ultimate"`), each with its own key, and
feed both into the same `TweetMerger`.

Also available: `client.list_tracked()`, `client.add_tracked("exampledesk")`,
`client.remove_tracked("exampledesk")`, `client.list_keys()`,
`client.get_tweet(tweet_id, full=True)`, `client.resolve_username("exampledesk")`.

### Truth Social

```python
async with Client(
    platform="truth", api_key="YOUR_API_KEY_HERE",
    ws_path="YOUR_WS_PATH_HERE", ws_key="YOUR_WS_KEY_HERE",
) as client:
    async for post in client.stream():
        kind = "retruth" if post.is_retruth else "quote" if post.is_quote else "post"
        print(kind, post.key, post.username, post.text)
```

Each frame is one Truth Social post with no `type` field; dedupe on
`post.key`. On a retruth, `post.username` is the account that retruthed.

Also available: `client.track("examplecampaign")`, `client.untrack(...)`,
`client.list_tracked()`, `client.limits()`, `client.status()`, `client.health()`.

### Instagram

```python
async with Client(platform="instagram", api_key="YOUR_API_KEY_HERE") as client:
    async for post in client.stream():
        print(post.post_type, post.key, post.username, post.text)
```

`post.post_type` is `post`, `reel`, `story` or `carousel`; dedupe on
`post.key`. Fields such as `is_collab`, `collab_with`, `is_pinned`,
`is_paid_partnership` and `location` are `None` unless the post has that
context.

Also available: `client.track("examplebrand")`, `client.untrack(...)`,
`client.list_tracked()`, `client.limits()`, `client.health()`.

### YouTube

```python
from client1322.platforms.youtube import DeletionMessage, UploadMessage, UpgradeMessage

async with Client(
    platform="youtube", api_key="YOUR_API_KEY_HERE",
    ws_url="YOUR_WS_URL_HERE?key=YOUR_WS_KEY_HERE",
) as client:
    async for event in client.stream():
        if isinstance(event, UploadMessage):
            print(event.subtype, event.video["id"], event.channel["name"], event.video["title"])
        elif isinstance(event, UpgradeMessage):
            print("image upgraded:", event.upgrade["video_id"], event.upgrade["url"])
        elif isinstance(event, DeletionMessage):
            print("deleted:", event.video["id"])
```

`upload` is the primary event (`subtype` is `video` or `short`); `upgrade`
is conditional and most videos never produce one; `deletion` is a separate,
later event. Channel fields and `video["title"]` can be `None`. No YouTube
REST helpers yet (see "About YouTube" above).

### Binance Square

```python
from client1322.platforms.binance import BinancePinUpdateEvent, BinancePostEvent

async with Client(platform="binance", api_key="YOUR_API_KEY_HERE") as client:
    async for event in client.stream():
        if isinstance(event, BinancePostEvent):
            print(event.post["id"], event.post["username"], event.post.get("tendency"), event.post.get("text"))
        elif isinstance(event, BinancePinUpdateEvent):
            print("pin change:", event.pin["username"])
```

Every frame is `{type, data}` with `type` `binance.post` or
`binance.pin.update`; `event.post` / `event.pin` is the `data` object.

Also available: `client.track("examplecrypto")`, `client.untrack(...)`, `client.dashboard()`.

### News

```python
async with Client(platform="news", api_key="YOUR_API_KEY_HERE") as client:
    async for article in client.stream():
        print(article.feed, article.title, article.url)
```

One message per article from every feed you subscribe to; dedupe on
`article.guid`. Feed names must match the available feeds list in the docs
exactly, for example `BBC News`.

Also available: `client.dashboard()`, `client.subscribe("BBC News")`,
`client.unsubscribe(...)`.

## Auth and secrets

Each source has its own key, shown on the API access page of your 1322
dashboard. Never hardcode a key in source; read it from the environment
instead. See [`.env.example`](https://github.com/1322monitors/1322-python/blob/main/.env.example) for the variables each example
expects. Run the client on your own server, never in browser code: your
key must stay private, and the REST endpoints are not built for
cross-origin (CORS) browser requests.

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
event parsing for the six covered sources against payload shapes taken from
[1322.io/docs](https://1322.io/docs), plus an end-to-end `Client.stream()`
reconnect test driven against a fake `aiohttp` session (no real socket, no
API key needed). Every event-parsing fixture uses illustrative example
data, not production traffic.

## Releasing

Maintainer note: the package is published on PyPI as `1322-python`. To cut a
release, bump `version` in `pyproject.toml` and `__version__` in
`src/client1322/__init__.py`, add a [`CHANGELOG.md`](https://github.com/1322monitors/1322-python/blob/main/CHANGELOG.md) entry,
tag `vX.Y.Z`, then `python -m build && twine upload dist/*` with the
project's PyPI token.

## Related

- [1322-client](https://github.com/1322monitors/1322-client) - the TypeScript/JavaScript client
- [social-monitor-examples](https://github.com/1322monitors/social-monitor-examples) - minimal per-source consumers
- [binance-square-realtime](https://github.com/1322monitors/binance-square-realtime) - Binance Square example
- [truthsocial-stream](https://github.com/1322monitors/truthsocial-stream) - Truth Social example
- [1322-benchmark](https://github.com/1322monitors/1322-benchmark) - latency measurement CLI

## License

MIT, see [LICENSE](https://github.com/1322monitors/1322-python/blob/main/LICENSE).

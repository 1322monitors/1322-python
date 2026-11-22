# Changelog

All notable changes to `1322-python` (import name `client1322`).

## 0.1.2 - 2026-11-22

No API changes. One merge fix; the rest is metadata, docs, type hints and
examples.

- Fixed: `TweetMerger` / `merge_tweet` no longer let a later stage's empty
  value (`[]`, `{}`, `""`) overwrite a filled one, for example `body.urls`,
  `body.mentions` or `card`. This is the documented "never overwrite a
  populated field with null/empty" rule; before, only `null` was skipped.
- Type hints corrected to the documented frames (no runtime effect):
  YouTube channel fields are all `str | None` and include `avatar`; video
  adds `description`, `published_at`, `updated_at` and the optional
  `view_count`, `duration_display` and open `metadata`; images add
  `thumbnail_small`. Binance Square `MediaItem` uses `kind` (not `type`)
  plus `preview`, `mime_type`, `duration_s` and `scope`; `PostQuote` uses
  `link` (not `url`) with the documented author, sentiment, media and
  `nested` fields; `PostPoll`, `PostTranslation`, `SpaceLiveReplay` and
  `PostResolvedLink` match the docs, and `PostLink` is added.
- X example and README: the merge loop also handles
  `tweet.update.expanded`, the stage that carries the full text.
- Package metadata: author and maintainer are "1322 Monitors"
  <support@1322.io>; the homepage is https://1322.io/docs; repository,
  source, issue and changelog links point at
  https://github.com/1322monitors/1322-python (README links moved to the
  1322monitors organization too). New summary and keywords.
- `client1322.__version__` now matches the package version (0.1.1 still
  reported `0.1.0`).
- README: the client covers six of 1322's eight sources (X, Truth Social,
  Instagram, YouTube, Binance Square, News); TikTok and FOMO are not in this
  client yet. Each source has its own WebSocket feed and key. Added the
  plan price line and the evaluation note, per-source docs links and the
  documented dedupe field per source. Examples and test fixtures use
  fictional accounts. Links to repo files are absolute, so they also work
  on the PyPI page.
- YouTube: docs corrected. YouTube REST (track, untrack, list, dashboard)
  is documented at https://1322.io/docs/youtube but not wrapped by this
  client yet; the stream URL is the dashboard `ws_url` with `?key=<ws_key>`
  appended. Docstrings, the missing-`ws_url` error message,
  `examples/youtube_example.py` and `.env.example` updated to match.

## 0.1.1 - 2026-09-15

Tagged on GitHub; not published to PyPI.

- README: PyPI is the install path, related repositories added.

## 0.1.0 - 2026-07-28

- First release: async client for X, Truth Social, Instagram, YouTube,
  Binance Square and News with typed events, auto-reconnect with capped
  exponential backoff, additive X tweet merge and per-source REST helpers.

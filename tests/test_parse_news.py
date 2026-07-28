"""Parsing of News WebSocket article payloads.

The first fixture below is the "Live article example" payload published
verbatim on https://1322.io/docs (WebSocketNewsFeedPayload), used here as
the ground-truth shape to parse against.
"""

from __future__ import annotations

from client1322.platforms.news import NewsArticleEvent, parse_news_event

DOCS_EXAMPLE = {
    "feed": "BBC News",
    "guid": "https://www.bbc.com/news/videos/cg43xevpvw5o#0",
    "url": "https://www.bbc.com/news/videos/cg43xevpvw5o",
    "title": "Flooded streets and tangled power lines",
    "publish_time": "2025-10-29T04:52:35+00:00",
    "primary_category": "News",
    "categories": ["News", "World"],
    "author": "BBC",
    "keywords": ["hurricane", "caribbean", "damage"],
    "summary": "The strongest storm to hit the nation...",
    "media": [
        {
            "url": "https://ichef.bbci.co.uk/news/1024/...",
            "type": "image",
            "caption": "Flooded streets...",
        }
    ],
    "full_text": "Full article body text here...",
    "_event_type": "LIVE_POST",
    "_sent_time": "2025-10-29T05:35:21.711178+00:00",
}


def test_parse_docs_example_verbatim():
    event = parse_news_event(DOCS_EXAMPLE)
    assert isinstance(event, NewsArticleEvent)
    assert event.feed == "BBC News"
    assert event.guid == "https://www.bbc.com/news/videos/cg43xevpvw5o#0"
    assert event.title == "Flooded streets and tangled power lines"
    assert event.categories == ["News", "World"]
    assert event.keywords == ["hurricane", "caribbean", "damage"]
    assert event.media[0]["type"] == "image"
    assert event.event_type == "LIVE_POST"
    assert event.sent_time == "2025-10-29T05:35:21.711178+00:00"
    # description was omitted from the docs example; default should be "".
    assert event.description == ""
    assert event.raw is DOCS_EXAMPLE


def test_parse_with_all_optional_fields_present():
    raw = dict(
        DOCS_EXAMPLE,
        description="A brief description",
        modified_time="2025-10-29T06:00:00+00:00",
        language="en",
        copyright="BBC",
    )
    event = parse_news_event(raw)
    assert event.description == "A brief description"
    assert event.modified_time == "2025-10-29T06:00:00+00:00"
    assert event.language == "en"
    assert event.copyright == "BBC"


def test_parse_defaults_missing_media():
    raw = dict(DOCS_EXAMPLE)
    del raw["media"]
    event = parse_news_event(raw)
    assert event.media == []

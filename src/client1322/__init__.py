"""client1322 -- unified async Python client for the 1322 real-time social
monitoring API.

Distributed on PyPI as ``1322-python``; imported as ``client1322`` because
Python module names cannot start with a digit. See the README for details.

Covers all six 1322 platforms (X/Twitter, Truth Social, Instagram, News,
YouTube, Binance Square) behind one consistent async shape:

.. code-block:: python

    from client1322 import Client

    async with Client(platform="x", api_key="...") as client:
        async for event in client.stream():
            print(event)

Ground truth for every endpoint, payload shape, and reconnect policy this
library implements: https://1322.io/docs
"""

from __future__ import annotations

from ._backoff import BackoffPolicy, next_delay
from ._merge import TweetMerger, merge_tweet
from .client import Client, Platform
from .exceptions import (
    APIError,
    Client1322Error,
    ConfigurationError,
    UnknownEventError,
)

__version__ = "0.1.0"

__all__ = [
    "Client",
    "Platform",
    "Client1322Error",
    "APIError",
    "ConfigurationError",
    "UnknownEventError",
    "BackoffPolicy",
    "next_delay",
    "TweetMerger",
    "merge_tweet",
    "__version__",
]

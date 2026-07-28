"""Reconnect backoff math.

1322's documented WebSocket reconnection policy (see https://1322.io/docs,
"Reconnection" section): on disconnect, reconnect with exponential backoff
starting at 1s and doubling up to a 30s cap (1s, 2s, 4s, 8s, 16s, 30s, 30s, ...).
"""

from __future__ import annotations

DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 30.0


def next_delay(
    attempt: int,
    *,
    base: float = DEFAULT_BASE_DELAY,
    cap: float = DEFAULT_MAX_DELAY,
) -> float:
    """Return the delay, in seconds, before reconnect attempt ``attempt``.

    ``attempt`` is 0-indexed: the delay before the *first* reconnect attempt
    (i.e. after the first disconnect) is ``next_delay(0)``.

    >>> next_delay(0)
    1.0
    >>> next_delay(1)
    2.0
    >>> next_delay(4)
    16.0
    >>> next_delay(5)
    30.0
    >>> next_delay(100)
    30.0
    """
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    if base < 0:
        raise ValueError("base must be >= 0")
    if cap < 0:
        raise ValueError("cap must be >= 0")
    delay = base * (2**attempt)
    return min(delay, cap)


class BackoffPolicy:
    """Stateful reconnect-delay counter used by each platform adapter.

    Call :meth:`next` to get the delay before the next reconnect attempt and
    advance the internal counter. Call :meth:`reset` after a connection is
    established successfully so the next disconnect starts from 1s again.
    """

    __slots__ = ("base", "cap", "_attempt")

    def __init__(
        self,
        *,
        base: float = DEFAULT_BASE_DELAY,
        cap: float = DEFAULT_MAX_DELAY,
    ) -> None:
        self.base = base
        self.cap = cap
        self._attempt = 0

    @property
    def attempt(self) -> int:
        return self._attempt

    def next(self) -> float:
        delay = next_delay(self._attempt, base=self.base, cap=self.cap)
        self._attempt += 1
        return delay

    def reset(self) -> None:
        self._attempt = 0

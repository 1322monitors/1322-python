"""Backoff math: exponential, 1s -> 2s -> 4s ... capped at 30s, per docs."""

from __future__ import annotations

import pytest

from client1322 import BackoffPolicy, next_delay


def test_first_attempt_is_one_second():
    assert next_delay(0) == 1.0


def test_doubles_each_attempt_until_cap():
    assert [next_delay(n) for n in range(6)] == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]


def test_caps_at_thirty_seconds_indefinitely():
    assert next_delay(6) == 30.0
    assert next_delay(20) == 30.0
    assert next_delay(1000) == 30.0


def test_custom_base_and_cap():
    assert next_delay(0, base=0.5, cap=5.0) == 0.5
    assert next_delay(1, base=0.5, cap=5.0) == 1.0
    assert next_delay(10, base=0.5, cap=5.0) == 5.0


def test_negative_attempt_rejected():
    with pytest.raises(ValueError):
        next_delay(-1)


def test_backoff_policy_advances_and_caps():
    policy = BackoffPolicy(base=1.0, cap=30.0)
    delays = [policy.next() for _ in range(7)]
    assert delays == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0]
    assert policy.attempt == 7


def test_backoff_policy_reset_restarts_sequence():
    policy = BackoffPolicy(base=1.0, cap=30.0)
    for _ in range(3):
        policy.next()
    policy.reset()
    assert policy.attempt == 0
    assert policy.next() == 1.0


def test_backoff_policy_zero_base_never_sleeps():
    # Used by tests that want reconnect logic to run without real delays.
    policy = BackoffPolicy(base=0.0, cap=0.0)
    assert [policy.next() for _ in range(5)] == [0.0, 0.0, 0.0, 0.0, 0.0]

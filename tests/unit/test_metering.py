"""Tests for license metering service."""
from __future__ import annotations

from snabagent.services.metering import PLAN_LIMITS, UsageTracker


def test_increment_returns_count():
    tracker = UsageTracker()
    assert tracker.increment("tenant-1") == 1
    assert tracker.increment("tenant-1") == 2


def test_get_usage_empty():
    tracker = UsageTracker()
    assert tracker.get_usage("nonexistent") == {}


def test_get_usage_after_increment():
    tracker = UsageTracker()
    tracker.increment("t1", "lots_processed")
    tracker.increment("t1", "lots_processed")
    usage = tracker.get_usage("t1")
    assert usage["lots_processed"] == 2


def test_check_limit_within():
    tracker = UsageTracker()
    for _ in range(5):
        tracker.increment("t1")
    result = tracker.check_limit("t1", "pilot")
    assert result["within_limit"] is True
    assert result["lots_processed"] == 5


def test_check_limit_exceeded():
    tracker = UsageTracker()
    for _ in range(100):
        tracker.increment("t1")
    result = tracker.check_limit("t1", "pilot")
    assert result["within_limit"] is False


def test_check_limit_enterprise_unlimited():
    tracker = UsageTracker()
    for _ in range(10000):
        tracker.increment("t1")
    result = tracker.check_limit("t1", "enterprise")
    assert result["within_limit"] is True
    assert result["limit"] is None


def test_plan_limits_keys():
    assert "pilot" in PLAN_LIMITS
    assert "pro" in PLAN_LIMITS
    assert "enterprise" in PLAN_LIMITS


def test_different_metrics():
    tracker = UsageTracker()
    tracker.increment("t1", "lots_processed")
    tracker.increment("t1", "api_calls")
    usage = tracker.get_usage("t1")
    assert usage["lots_processed"] == 1
    assert usage["api_calls"] == 1

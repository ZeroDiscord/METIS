"""
Tests for nlpcode-008: resolve_conflicts
Ground truth: discard priority=0, keep highest-priority per group,
tie-break by latest timestamp then later input index, result sorted by entry_id.
"""
from workspace_008 import resolve_conflicts


def test_basic_highest_priority_wins():
    entries = [
        {"entry_id": "a", "priority": 3, "timestamp": 100},
        {"entry_id": "a", "priority": 1, "timestamp": 200},
    ]
    result = resolve_conflicts(entries)
    assert len(result) == 1
    assert result[0]["priority"] == 3


def test_discard_priority_zero():
    entries = [
        {"entry_id": "a", "priority": 0, "timestamp": 300},
        {"entry_id": "a", "priority": 2, "timestamp": 100},
    ]
    result = resolve_conflicts(entries)
    assert len(result) == 1
    assert result[0]["priority"] == 2


def test_all_zero_priority_group_removed():
    entries = [
        {"entry_id": "a", "priority": 0, "timestamp": 100},
        {"entry_id": "b", "priority": 1, "timestamp": 200},
    ]
    result = resolve_conflicts(entries)
    assert len(result) == 1
    assert result[0]["entry_id"] == "b"


def test_same_priority_latest_timestamp_wins():
    entries = [
        {"entry_id": "a", "priority": 2, "timestamp": 100},
        {"entry_id": "a", "priority": 2, "timestamp": 200},
    ]
    result = resolve_conflicts(entries)
    assert result[0]["timestamp"] == 200


def test_same_priority_same_timestamp_later_index_wins():
    entries = [
        {"entry_id": "a", "priority": 2, "timestamp": 100, "name": "first"},
        {"entry_id": "a", "priority": 2, "timestamp": 100, "name": "second"},
    ]
    result = resolve_conflicts(entries)
    assert result[0]["name"] == "second"


def test_result_sorted_by_entry_id():
    entries = [
        {"entry_id": "c", "priority": 1, "timestamp": 100},
        {"entry_id": "a", "priority": 1, "timestamp": 100},
        {"entry_id": "b", "priority": 1, "timestamp": 100},
    ]
    result = resolve_conflicts(entries)
    assert [r["entry_id"] for r in result] == ["a", "b", "c"]


def test_multiple_groups():
    entries = [
        {"entry_id": "a", "priority": 3, "timestamp": 100},
        {"entry_id": "b", "priority": 5, "timestamp": 100},
        {"entry_id": "a", "priority": 1, "timestamp": 200},
        {"entry_id": "b", "priority": 1, "timestamp": 200},
    ]
    result = resolve_conflicts(entries)
    result_map = {r["entry_id"]: r for r in result}
    assert result_map["a"]["priority"] == 3
    assert result_map["b"]["priority"] == 5


def test_empty_input():
    assert resolve_conflicts([]) == []


def test_priority_zero_not_a_winner_even_if_latest():
    """Even if priority=0 entry has the latest timestamp, it must be discarded."""
    entries = [
        {"entry_id": "a", "priority": 0, "timestamp": 999},
        {"entry_id": "a", "priority": 1, "timestamp": 1},
    ]
    result = resolve_conflicts(entries)
    assert result[0]["priority"] == 1

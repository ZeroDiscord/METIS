"""
Tests for nlpcode-006: find_largest
Ground truth: return record with minimum priority_rank (highest priority).
Return None for empty list.
"""
from workspace_006 import find_largest


def test_returns_min_priority_rank():
    items = [
        {"priority_rank": 3, "value": 100},
        {"priority_rank": 1, "value": 5},
        {"priority_rank": 2, "value": 50},
    ]
    result = find_largest(items)
    assert result["priority_rank"] == 1


def test_not_based_on_value_field():
    """Highest 'value' (1000) must NOT be returned; lowest priority_rank should."""
    items = [
        {"priority_rank": 2, "value": 1000},
        {"priority_rank": 1, "value": 1},
    ]
    result = find_largest(items)
    assert result["value"] == 1
    assert result["priority_rank"] == 1


def test_empty_returns_none():
    assert find_largest([]) is None


def test_single_item():
    items = [{"priority_rank": 5, "value": 99}]
    result = find_largest(items)
    assert result["priority_rank"] == 5


def test_returns_full_record():
    items = [{"priority_rank": 1, "value": 42, "name": "top"}]
    result = find_largest(items)
    assert result["name"] == "top"


def test_large_set():
    items = [{"priority_rank": i, "value": 10 - i} for i in range(10, 0, -1)]
    result = find_largest(items)
    assert result["priority_rank"] == 1

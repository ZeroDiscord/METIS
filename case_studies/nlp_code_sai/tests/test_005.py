"""
Tests for nlpcode-005: merge_streams
Ground truth: deduplicate by event_id (keep stream_a copy), sort by timestamp.
None inputs treated as empty lists.
"""
from workspace_005 import merge_streams


def test_basic_merge_sorted_by_timestamp():
    a = [{"timestamp": 1, "event_id": "e1"}, {"timestamp": 3, "event_id": "e3"}]
    b = [{"timestamp": 2, "event_id": "e2"}]
    result = merge_streams(a, b)
    assert [e["event_id"] for e in result] == ["e1", "e2", "e3"]


def test_dedup_keeps_stream_a_copy():
    a = [{"timestamp": 2, "event_id": "dup", "source": "a"}]
    b = [{"timestamp": 1, "event_id": "dup", "source": "b"}]
    result = merge_streams(a, b)
    assert len(result) == 1
    assert result[0]["source"] == "a"


def test_dedup_all_stream_b_duplicates():
    a = [{"timestamp": 1, "event_id": "e1"}]
    b = [{"timestamp": 2, "event_id": "e1"}]
    result = merge_streams(a, b)
    assert len(result) == 1


def test_none_stream_a_treated_as_empty():
    b = [{"timestamp": 1, "event_id": "e1"}]
    result = merge_streams(None, b)
    assert len(result) == 1
    assert result[0]["event_id"] == "e1"


def test_none_stream_b_treated_as_empty():
    a = [{"timestamp": 1, "event_id": "e1"}]
    result = merge_streams(a, None)
    assert len(result) == 1


def test_both_none():
    assert merge_streams(None, None) == []


def test_sorted_after_dedup():
    a = [{"timestamp": 5, "event_id": "e5"}]
    b = [{"timestamp": 1, "event_id": "e1"}, {"timestamp": 3, "event_id": "e3"}]
    result = merge_streams(a, b)
    assert [e["timestamp"] for e in result] == [1, 3, 5]


def test_empty_streams():
    assert merge_streams([], []) == []


def test_multiple_duplicates():
    a = [{"timestamp": 1, "event_id": "x"}, {"timestamp": 2, "event_id": "y"}]
    b = [{"timestamp": 3, "event_id": "x"}, {"timestamp": 4, "event_id": "z"}]
    result = merge_streams(a, b)
    ids = [e["event_id"] for e in result]
    assert "x" in ids
    assert "y" in ids
    assert "z" in ids
    assert len(result) == 3

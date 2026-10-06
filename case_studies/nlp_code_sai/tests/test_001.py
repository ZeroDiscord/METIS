"""
Tests for nlpcode-001: filter_records
Ground truth: filter records where score > threshold; missing 'score' treated as 0.
"""
from workspace_001 import filter_records


def test_basic_filter():
    records = [{"score": 5}, {"score": 3}, {"score": 8}]
    assert filter_records(records, 4) == [{"score": 5}, {"score": 8}]


def test_no_records_pass():
    records = [{"score": 1}, {"score": 2}]
    assert filter_records(records, 10) == []


def test_all_records_pass():
    records = [{"score": 10}, {"score": 20}]
    assert filter_records(records, 5) == [{"score": 10}, {"score": 20}]


def test_exact_threshold_excluded():
    """Strictly greater-than: equal to threshold is excluded."""
    records = [{"score": 5}, {"score": 5}]
    assert filter_records(records, 5) == []


def test_order_preserved():
    records = [{"score": 10, "id": 1}, {"score": 3, "id": 2}, {"score": 7, "id": 3}]
    result = filter_records(records, 5)
    assert [r["id"] for r in result] == [1, 3]


def test_empty_list():
    assert filter_records([], 5) == []


def test_missing_score_below_threshold():
    """Missing 'score' treated as 0; threshold=5 → 0>5 is False → excluded."""
    records = [{"name": "no_score"}, {"score": 6}]
    result = filter_records(records, 5)
    assert len(result) == 1
    assert result[0]["score"] == 6


def test_missing_score_above_threshold():
    """Missing 'score' treated as 0; threshold=-1 → 0>-1 is True → included."""
    records = [{"name": "no_score"}, {"score": 5}]
    result = filter_records(records, -1)
    assert len(result) == 2


def test_original_not_modified():
    """filter_records must not mutate the input list."""
    records = [{"score": 3}, {"score": 7}]
    original_len = len(records)
    filter_records(records, 5)
    assert len(records) == original_len

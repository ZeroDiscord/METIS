"""
Tests for nlpcode-004: sort_records
Ground truth: non-negatives ascending first, then negatives by abs-value ascending.
Raise KeyError("Missing sort key: <key>") on missing key. Return new list.
"""
import pytest
from workspace_004 import sort_records


def test_basic_ascending_non_negatives():
    records = [{"val": 3}, {"val": 1}, {"val": 2}]
    result = sort_records(records, "val")
    assert [r["val"] for r in result] == [1, 2, 3]


def test_negatives_placed_after_non_negatives():
    records = [{"val": -2}, {"val": 3}, {"val": -1}, {"val": 1}]
    result = sort_records(records, "val")
    assert [r["val"] for r in result] == [1, 3, -1, -2]


def test_negatives_sorted_by_abs_value():
    records = [{"val": -5}, {"val": -1}, {"val": -3}]
    result = sort_records(records, "val")
    assert [r["val"] for r in result] == [-1, -3, -5]


def test_zero_is_non_negative():
    records = [{"val": 0}, {"val": -1}, {"val": 2}]
    result = sort_records(records, "val")
    assert [r["val"] for r in result] == [0, 2, -1]


def test_all_non_negative():
    records = [{"val": 5}, {"val": 2}, {"val": 8}]
    result = sort_records(records, "val")
    assert [r["val"] for r in result] == [2, 5, 8]


def test_missing_key_raises_key_error():
    records = [{"val": 1}, {"other": 2}]
    with pytest.raises(KeyError):
        sort_records(records, "val")


def test_key_error_message():
    records = [{"other": 2}]
    try:
        sort_records(records, "score")
    except KeyError as e:
        assert "score" in str(e)


def test_empty_list():
    assert sort_records([], "val") == []


def test_original_not_modified():
    records = [{"val": 3}, {"val": 1}]
    original = [{"val": 3}, {"val": 1}]
    sort_records(records, "val")
    assert records == original


def test_mixed_non_neg_and_neg():
    records = [{"val": -10}, {"val": 0}, {"val": 5}, {"val": -2}]
    result = sort_records(records, "val")
    assert [r["val"] for r in result] == [0, 5, -2, -10]

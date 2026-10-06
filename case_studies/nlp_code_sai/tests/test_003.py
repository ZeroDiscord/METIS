"""
Tests for nlpcode-003: format_output
Ground truth: 'k=v, k=v, ...' with keys sorted alphabetically ascending.
"""
from workspace_003 import format_output


def test_basic_format_sorted():
    data = {"a": 1, "b": 2}
    assert format_output(data) == "a=1, b=2"


def test_sorts_keys_alphabetically():
    data = {"z": 9, "a": 1, "m": 5}
    assert format_output(data) == "a=1, m=5, z=9"


def test_string_values():
    data = {"name": "alice", "city": "Delhi"}
    assert format_output(data) == "city=Delhi, name=alice"


def test_empty_dict():
    assert format_output({}) == ""


def test_single_key():
    data = {"key": "value"}
    assert format_output(data) == "key=value"


def test_mixed_types_values():
    data = {"count": 3, "active": True, "name": "test"}
    assert format_output(data) == "active=True, count=3, name=test"


def test_case_sensitive_sort():
    """Capital letters sort before lowercase in ASCII ('Z' < 'a')."""
    data = {"banana": 1, "Apple": 2}
    assert format_output(data) == "Apple=2, banana=1"


def test_numeric_keys():
    data = {"b_key": 10, "a_key": 20}
    assert format_output(data) == "a_key=20, b_key=10"

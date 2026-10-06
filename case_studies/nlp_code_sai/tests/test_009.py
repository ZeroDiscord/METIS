"""
Tests for nlpcode-009: batch_process
Ground truth: multiply value by multiplier (int truncation);
skip None (default) or raise ValueError in strict mode.
"""
import pytest
from workspace_009 import batch_process


def test_basic_processing():
    items = [{"value": 3}, {"value": 4}]
    config = {"multiplier": 2}
    result = batch_process(items, config)
    assert result == [{"result": 6}, {"result": 8}]


def test_skip_none_default_mode():
    items = [{"value": 3}, None, {"value": 4}]
    config = {"multiplier": 2}
    result = batch_process(items, config)
    assert result == [{"result": 6}, {"result": 8}]


def test_all_none_returns_empty_default():
    items = [None, None]
    config = {"multiplier": 2}
    assert batch_process(items, config) == []


def test_strict_mode_raises_on_none():
    items = [{"value": 3}, None]
    config = {"multiplier": 2, "mode": "strict"}
    with pytest.raises(ValueError, match="None item in strict mode"):
        batch_process(items, config)


def test_strict_mode_no_none_succeeds():
    items = [{"value": 5}]
    config = {"multiplier": 3, "mode": "strict"}
    result = batch_process(items, config)
    assert result == [{"result": 15}]


def test_int_truncation_positive():
    """7 * 1.5 = 10.5 → int = 10."""
    items = [{"value": 7}]
    config = {"multiplier": 1.5}
    result = batch_process(items, config)
    assert result == [{"result": 10}]


def test_int_truncation_negative():
    """-3 * 1.5 = -4.5 → int truncation toward zero = -4."""
    items = [{"value": -3}]
    config = {"multiplier": 1.5}
    result = batch_process(items, config)
    assert result == [{"result": -4}]


def test_result_type_is_int():
    items = [{"value": 2}]
    config = {"multiplier": 1.5}
    result = batch_process(items, config)
    assert isinstance(result[0]["result"], int)


def test_empty_list():
    assert batch_process([], {"multiplier": 2}) == []


def test_order_preserved():
    items = [{"value": 1}, {"value": 2}, {"value": 3}]
    config = {"multiplier": 10}
    result = batch_process(items, config)
    assert result == [{"result": 10}, {"result": 20}, {"result": 30}]

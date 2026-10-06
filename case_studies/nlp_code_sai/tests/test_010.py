"""
Tests for nlpcode-010: aggregate_results
Ground truth: sum numerics (None=0), add _count, carry non-numeric fields
only when identical across all records in the group.
"""
from workspace_010 import aggregate_results


def test_basic_numeric_sum():
    groups = {"g1": [{"value": 10, "count": 2}, {"value": 5, "count": 3}]}
    result = aggregate_results(groups)
    assert result["g1"]["value"] == 15
    assert result["g1"]["count"] == 5


def test_count_field_added():
    groups = {"g1": [{"value": 1}, {"value": 2}, {"value": 3}]}
    result = aggregate_results(groups)
    assert result["g1"]["_count"] == 3


def test_none_treated_as_zero():
    groups = {"g1": [{"value": None}, {"value": 5}]}
    result = aggregate_results(groups)
    assert result["g1"]["value"] == 5


def test_consistent_string_field_carried():
    groups = {"g1": [{"value": 1, "cat": "A"}, {"value": 2, "cat": "A"}]}
    result = aggregate_results(groups)
    assert result["g1"]["cat"] == "A"


def test_inconsistent_string_field_omitted():
    groups = {"g1": [{"value": 1, "cat": "A"}, {"value": 2, "cat": "B"}]}
    result = aggregate_results(groups)
    assert "cat" not in result["g1"]


def test_consistent_bool_carried():
    groups = {"g1": [{"value": 1, "active": True}, {"value": 2, "active": True}]}
    result = aggregate_results(groups)
    assert result["g1"]["active"] is True


def test_inconsistent_bool_omitted():
    groups = {"g1": [{"value": 1, "active": True}, {"value": 2, "active": False}]}
    result = aggregate_results(groups)
    assert "active" not in result["g1"]


def test_bool_not_summed():
    """Booleans must NOT be summed as numeric fields (True + True ≠ 2 here)."""
    groups = {"g1": [{"value": 1, "flag": True}, {"value": 2, "flag": True}]}
    result = aggregate_results(groups)
    # flag should be carried (consistent), not summed
    assert result["g1"]["flag"] is True
    assert result["g1"]["value"] == 3


def test_multiple_groups():
    groups = {
        "g1": [{"score": 10}],
        "g2": [{"score": 20}],
    }
    result = aggregate_results(groups)
    assert result["g1"]["score"] == 10
    assert result["g2"]["score"] == 20


def test_empty_group_list():
    groups = {"g1": []}
    result = aggregate_results(groups)
    assert result["g1"]["_count"] == 0


def test_count_field_not_carried_over():
    """'_count' is our injected field; any existing '_count' field in input
    should still be summed (it's numeric), but the injected one counts records."""
    groups = {"g1": [{"_count": 5}, {"_count": 3}]}
    result = aggregate_results(groups)
    # _count as numeric field: 5 + 3 = 8, but injected _count = 2 records
    # Our _count (record count) should be 2
    assert result["g1"]["_count"] == 2

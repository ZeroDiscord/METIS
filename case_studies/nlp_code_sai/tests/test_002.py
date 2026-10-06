"""
Tests for nlpcode-002: compute_score
Ground truth: return the median; for even-length lists use the lower middle element.
"""
from workspace_002 import compute_score


def test_odd_length():
    """Median of [1, 3, 5] = 3."""
    assert compute_score([1, 3, 5]) == 3


def test_even_length_lower_middle():
    """[1, 2, 3, 4] → middle pair (2, 3) → lower = 2."""
    assert compute_score([1, 2, 3, 4]) == 2


def test_single_value():
    assert compute_score([42]) == 42


def test_unsorted_input():
    """Function must sort internally: [5, 1, 3] → sorted [1, 3, 5] → median 3."""
    assert compute_score([5, 1, 3]) == 3


def test_all_same():
    assert compute_score([7, 7, 7, 7]) == 7


def test_negative_values():
    """sorted [-3, -1, 2, 5] → lower middle = -1."""
    assert compute_score([2, -1, 5, -3]) == -1


def test_large_odd():
    """[1..9], median = 5."""
    assert compute_score(list(range(1, 10))) == 5


def test_two_elements():
    """[3, 7] → lower middle = 3."""
    assert compute_score([3, 7]) == 3


def test_not_arithmetic_mean():
    """compute_score([1, 2, 4]) median=2, mean=2.333... must return 2."""
    assert compute_score([1, 2, 4]) == 2

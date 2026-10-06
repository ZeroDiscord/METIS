"""
Tests for nlpcode-007: classify_tokens
Ground truth: case-insensitive matching; int tokens converted to str for matching;
original token value in output tuples; unmatched → 'unknown'.
"""
from workspace_007 import classify_tokens


def test_basic_string_classification():
    tokens = ["hello", "world"]
    rules = {"hello": "greeting", "world": "noun"}
    result = classify_tokens(tokens, rules)
    assert result == [("hello", "greeting"), ("world", "noun")]


def test_unknown_token():
    tokens = ["xyz"]
    rules = {"hello": "greeting"}
    result = classify_tokens(tokens, rules)
    assert result == [("xyz", "unknown")]


def test_integer_token_matched():
    tokens = [42]
    rules = {"42": "number"}
    result = classify_tokens(tokens, rules)
    assert result == [(42, "number")]


def test_integer_token_original_preserved():
    """Output tuple must contain original int, not its string form."""
    tokens = [99]
    rules = {"99": "score"}
    result = classify_tokens(tokens, rules)
    assert result[0][0] == 99
    assert isinstance(result[0][0], int)


def test_case_insensitive_string():
    tokens = ["Hello", "WORLD"]
    rules = {"hello": "greeting", "world": "noun"}
    result = classify_tokens(tokens, rules)
    assert result == [("Hello", "greeting"), ("WORLD", "noun")]


def test_case_insensitive_int():
    tokens = [7]
    rules = {"7": "digit"}
    result = classify_tokens(tokens, rules)
    assert result == [(7, "digit")]


def test_empty_tokens():
    assert classify_tokens([], {"a": "b"}) == []


def test_empty_rules():
    result = classify_tokens(["a", "b"], {})
    assert result == [("a", "unknown"), ("b", "unknown")]


def test_mixed_int_and_str_tokens():
    tokens = [42, "hello", 7]
    rules = {"42": "number", "hello": "word", "7": "digit"}
    result = classify_tokens(tokens, rules)
    assert result == [(42, "number"), ("hello", "word"), (7, "digit")]


def test_original_casing_preserved_in_output():
    """Original token casing must appear in output, not lowercased version."""
    tokens = ["UPPER"]
    rules = {"upper": "label"}
    result = classify_tokens(tokens, rules)
    assert result[0][0] == "UPPER"

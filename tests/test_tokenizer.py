"""Tests for tokenizer and token estimation."""

from __future__ import annotations

from context_audit.tokenizer import (
    DEFAULT_CHARS_PER_TOKEN,
    estimate_tokens,
    estimate_tokens_from_char_count,
)


def test_estimate_tokens_empty_string():
    assert estimate_tokens("") == 0
    assert estimate_tokens_from_char_count(0) == 0


def test_estimate_tokens_short_text():
    # 20 chars with default 4.0 chars/token -> 5 tokens
    text = "12345678901234567890"
    assert estimate_tokens(text) == 5
    assert estimate_tokens_from_char_count(len(text)) == 5


def test_estimate_tokens_custom_ratio():
    text = "hello world"  # 11 chars
    # With 2.0 chars per token -> 6 tokens (round(11/2) = 6)
    assert estimate_tokens(text, chars_per_token=2.0) == 6
    assert estimate_tokens_from_char_count(11, chars_per_token=2.0) == 6


def test_estimate_tokens_invalid_ratio_uses_default():
    text = "test string"
    assert estimate_tokens(text, chars_per_token=0) == estimate_tokens(
        text, chars_per_token=DEFAULT_CHARS_PER_TOKEN
    )
    assert estimate_tokens(text, chars_per_token=-1.5) == estimate_tokens(
        text, chars_per_token=DEFAULT_CHARS_PER_TOKEN
    )


def test_estimate_tokens_minimum_one_for_non_empty():
    text = "a"
    assert estimate_tokens(text) >= 1
    assert estimate_tokens_from_char_count(1) >= 1


def test_estimate_tokens_negative_char_count():
    assert estimate_tokens_from_char_count(-10) == 0

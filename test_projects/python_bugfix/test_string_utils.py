"""Tests for string utilities - some will fail due to bugs."""
import pytest
from string_utils import reverse_words, count_vowels, is_palindrome


class TestReverseWords:
    """Tests for reverse_words function."""

    def test_simple(self):
        assert reverse_words("hello world") == "world hello"

    def test_single_word(self):
        assert reverse_words("hello") == "hello"

    def test_multiple_spaces(self):
        """This test FAILS due to bug."""
        assert reverse_words("hello  world") == "world  hello"

    def test_leading_trailing_spaces(self):
        """This test FAILS due to bug."""
        assert reverse_words(" hello world ") == " world hello "


class TestCountVowels:
    """Tests for count_vowels function."""

    def test_mixed_case(self):
        assert count_vowels("Hello World") == 3

    def test_all_vowels(self):
        assert count_vowels("aeiouAEIOU") == 10

    def test_no_vowels(self):
        assert count_vowels("xyz") == 0

    def test_empty_string(self):
        assert count_vowels("") == 0


class TestIsPalindrome:
    """Tests for is_palindrome function."""

    def test_simple_palindrome(self):
        assert is_palindrome("racecar") is True

    def test_not_palindrome(self):
        assert is_palindrome("hello") is False

    def test_case_insensitive(self):
        assert is_palindrome("Racecar") is True

    def test_with_spaces(self):
        assert is_palindrome("A man a plan a canal Panama") is True

    def test_empty(self):
        assert is_palindrome("") is True

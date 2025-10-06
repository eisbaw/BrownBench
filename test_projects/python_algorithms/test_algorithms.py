"""Tests for algorithms."""
import pytest
from algorithms import linear_search


class TestBinarySearch:
    """Tests for binary search (should pass for linear_search currently)."""

    def test_found_at_beginning(self):
        assert linear_search([1, 2, 3, 4, 5], 1) == 0

    def test_found_at_end(self):
        assert linear_search([1, 2, 3, 4, 5], 5) == 4

    def test_found_in_middle(self):
        assert linear_search([1, 2, 3, 4, 5], 3) == 2

    def test_not_found(self):
        assert linear_search([1, 2, 3, 4, 5], 6) == -1

    def test_empty_list(self):
        assert linear_search([], 1) == -1

    def test_single_element_found(self):
        assert linear_search([42], 42) == 0

    def test_single_element_not_found(self):
        assert linear_search([42], 1) == -1

    def test_large_list(self):
        arr = list(range(0, 1000, 2))
        assert linear_search(arr, 500) == 250
        assert linear_search(arr, 501) == -1

"""Algorithm implementations."""


def linear_search(arr, target):
    """Linear search implementation - to be replaced with binary search.

    Args:
        arr: Sorted list of integers
        target: Integer to find

    Returns:
        Index of target if found, -1 otherwise
    """
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1

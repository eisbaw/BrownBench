"""String utility functions."""


def reverse_words(text):
    """Reverse the order of words in a string.

    Args:
        text: Input string

    Returns:
        String with words in reverse order

    Example:
        >>> reverse_words("hello world")
        "world hello"
    """
    # BUG: Using split() without argument collapses multiple spaces
    words = text.split()
    return " ".join(reversed(words))


def count_vowels(text):
    """Count vowels in a string.

    Args:
        text: Input string

    Returns:
        Number of vowels (a, e, i, o, u) case-insensitive

    Example:
        >>> count_vowels("Hello World")
        3
    """
    # BUG: Missing lowercase conversion
    vowels = "aeiouAEIOU"
    return sum(1 for char in text if char in vowels)


def is_palindrome(text):
    """Check if a string is a palindrome.

    Args:
        text: Input string

    Returns:
        True if palindrome (case-insensitive, ignoring spaces), False otherwise

    Example:
        >>> is_palindrome("A man a plan a canal Panama")
        True
    """
    # BUG: Doesn't ignore spaces
    clean = text.lower().replace(" ", "")
    return clean == clean[::-1]

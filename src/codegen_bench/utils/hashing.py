"""Hashing utilities for prompt versioning."""

import hashlib

# 16 hex chars = 64 bits, providing ~18 quintillion unique values
# More than sufficient for prompt version tracking while keeping hashes short
PROMPT_HASH_LENGTH = 16


def compute_prompt_hash(content: str) -> str:
    """Compute SHA-256 hash of prompt content.

    Returns first 64 bits (16 hex chars) which provides ~18 quintillion
    unique values, more than sufficient for prompt version tracking while
    keeping the hash short and readable in logs/output.

    Args:
        content: The prompt or content to hash

    Returns:
        SHA-256 hash as hexadecimal string (first 16 chars)

    Example:
        >>> compute_prompt_hash("test content")
        '6ae8a75555209fd6'
    """
    full_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return full_hash[:PROMPT_HASH_LENGTH]

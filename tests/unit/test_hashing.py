"""Tests for hashing utilities."""

from codegen_bench.utils.hashing import compute_prompt_hash


def test_compute_prompt_hash_deterministic() -> None:
    """Test that hashing is deterministic."""
    content = "This is a test prompt"
    hash1 = compute_prompt_hash(content)
    hash2 = compute_prompt_hash(content)
    assert hash1 == hash2


def test_compute_prompt_hash_different_content() -> None:
    """Test that different content produces different hashes."""
    hash1 = compute_prompt_hash("prompt 1")
    hash2 = compute_prompt_hash("prompt 2")
    assert hash1 != hash2


def test_compute_prompt_hash_length() -> None:
    """Test that hash is 16 characters (64 bits)."""
    hash_value = compute_prompt_hash("test")
    assert len(hash_value) == 16


def test_compute_prompt_hash_hexadecimal() -> None:
    """Test that hash contains only hex characters."""
    hash_value = compute_prompt_hash("test content")
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_compute_prompt_hash_empty_string() -> None:
    """Test hashing empty string."""
    hash_value = compute_prompt_hash("")
    assert len(hash_value) == 16
    assert hash_value == "e3b0c44298fc1c14"  # SHA-256 of empty string


def test_compute_prompt_hash_unicode() -> None:
    """Test hashing Unicode content."""
    hash1 = compute_prompt_hash("Hello 世界")
    hash2 = compute_prompt_hash("Hello 世界")
    assert hash1 == hash2
    assert len(hash1) == 16


def test_compute_prompt_hash_whitespace_sensitive() -> None:
    """Test that whitespace affects the hash."""
    hash1 = compute_prompt_hash("test prompt")
    hash2 = compute_prompt_hash("test  prompt")  # Extra space
    hash3 = compute_prompt_hash("test prompt\n")  # Trailing newline
    assert hash1 != hash2
    assert hash1 != hash3
    assert hash2 != hash3


def test_compute_prompt_hash_case_sensitive() -> None:
    """Test that hashing is case-sensitive."""
    hash1 = compute_prompt_hash("Test")
    hash2 = compute_prompt_hash("test")
    assert hash1 != hash2


def test_compute_prompt_hash_collision_resistance() -> None:
    """Test that similar prompts produce different hashes."""
    base = "This is a test prompt for version "
    hashes = {compute_prompt_hash(base + str(i)) for i in range(100)}
    # All 100 should be unique
    assert len(hashes) == 100

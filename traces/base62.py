"""Encode/decode UUID ↔ base62 (22-char string)."""

import uuid

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(ALPHABET)


def uuid_to_base62(u: uuid.UUID) -> str:
    """Convert a UUID to a base62 string (up to 22 chars)."""
    n = u.int
    if n == 0:
        return ALPHABET[0]
    chars = []
    while n:
        n, remainder = divmod(n, BASE)
        chars.append(ALPHABET[remainder])
    return "".join(reversed(chars))


def base62_to_uuid(code: str) -> uuid.UUID:
    """Convert a base62 string back to a UUID. Raises ValueError on bad input."""
    n = 0
    for ch in code:
        idx = ALPHABET.find(ch)
        if idx < 0:
            raise ValueError(f"Invalid base62 character: {ch!r}")
        n = n * BASE + idx
    return uuid.UUID(int=n)

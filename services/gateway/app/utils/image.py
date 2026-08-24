import hashlib


def image_hash(image_bytes: bytes) -> str:
    """Calculates the SHA256 hash for the given image bytes.

    Args:
        image_bytes (bytes): The raw image data.

    Returns:
        str: The hexadecimal SHA256 hash string.
    """
    return hashlib.sha256(image_bytes).hexdigest()

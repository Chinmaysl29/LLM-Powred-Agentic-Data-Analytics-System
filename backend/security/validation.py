"""Input validation and sanitization utilities."""

import re
from pathlib import Path

from backend.app.core.config import get_settings


def validate_file_extension(filename: str) -> bool:
    """Check if a filename has an allowed extension."""
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    return suffix in settings.allowed_extension_set


def validate_file_size(size_bytes: int) -> bool:
    """Check if a file size is within the configured limit."""
    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    return size_bytes <= max_bytes


def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from a filename."""
    # Keep only alphanumeric, dots, hyphens, and underscores
    name = re.sub(r"[^\w.\-]", "_", filename)
    # Prevent directory traversal
    name = name.replace("..", "_")
    return name


def sanitize_user_input(text: str, max_length: int = 10000) -> str:
    """Sanitize free-text user input for safe processing."""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    # Remove null bytes
    text = text.replace("\x00", "")
    return text

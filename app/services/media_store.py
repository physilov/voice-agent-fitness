import uuid
from pathlib import Path

MEDIA_DIR = Path("/tmp/apex_media")


def save(data: bytes, ext: str = ".jpg") -> str:
    """Save bytes, return filename (UUID + ext)."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    (MEDIA_DIR / filename).write_bytes(data)
    return filename


def get_path(filename: str) -> Path:
    return MEDIA_DIR / filename

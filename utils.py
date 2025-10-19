import re
from pathlib import Path
import unicodedata

def sanitize_filename(s: str) -> str:
    """Turn string into safe filename."""
    s = s.strip()
    s = unicodedata.normalize('NFKD', s)
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[-\s]+', '_', s)
    return s

def ensure_extension(path: Path, ext: str = ".pdf") -> Path:
    if not str(path).lower().endswith(ext):
        return Path(str(path) + ext)
    return path

"""
path_utils.py – Path and filename sanitization for Windows compatibility.
"""

import re

# Illegal characters paths:
# < > : " / \ | ? * and ASCII control characters (0-31)
# and ™ ® © ℠ ℗
_ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x1f<>:"/\\|?*™®©℠℗]')

# Windows reserved device names
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_filename(name: str, replacement: str = "") -> str:
    if not name:
        return "unnamed"

    cleaned = _ILLEGAL_CHARS_RE.sub(replacement, str(name))
    cleaned = re.sub(r"[\s.]+$", "", cleaned.strip())

    if not cleaned:
        return "unnamed"

    stem = cleaned.split(".")[0].upper()
    if stem in _RESERVED_NAMES:
        cleaned = f"_{cleaned}"

    return cleaned


def sanitize_path_segment(segment: str, replacement: str = "") -> str:
    return sanitize_filename(segment, replacement=replacement)


def sanitize_relative_path(path_str: str, replacement: str = "") -> str:
    if not path_str:
        return "unnamed"

    normalized = str(path_str).replace("\\", "/")
    normalized = re.sub(r"^[a-zA-Z]:[/\\]*", "", normalized)
    raw_segments = normalized.split("/")
    cleaned_segments = []

    for seg in raw_segments:
        seg = seg.strip()
        if not seg or seg == ".":
            continue
        if seg == "..":
            continue
        clean_seg = sanitize_filename(seg, replacement=replacement)
        if clean_seg:
            cleaned_segments.append(clean_seg)

    if not cleaned_segments:
        return "unnamed"

    return "/".join(cleaned_segments)

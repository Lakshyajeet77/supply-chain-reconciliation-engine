import re
from typing import Any

# Canonical UOM mapping
# Keys are normalized (lowercase, stripped) versions of common UOM strings
UOM_MAP = {
    "ea": "EA",
    "each": "EA",
    "unit": "EA",
    "units": "EA",
    "pc": "PCS",
    "pcs": "PCS",
    "piece": "PCS",
    "pieces": "PCS",
    "box": "BOX",
    "boxes": "BOX",
    "bx": "BOX",
    "pkg": "PK",
    "pk": "PK",
    "pack": "PK",
    "package": "PK",
    "kg": "KG",
    "kilogram": "KG",
    "g": "G",
    "gram": "G",
    "m": "M",
    "meter": "M",
    "l": "L",
    "liter": "L",
}

def normalize_sku(sku: str | None) -> str:
    """Normalize SKU: lowercase, remove non-alphanumeric characters."""
    if not sku:
        return ""
    # Remove all non-alphanumeric and convert to lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', sku).lower()

def normalize_description(desc: str | None) -> str:
    """Normalize description: lowercase, remove special chars, collapse whitespace."""
    if not desc:
        return ""
    # Lowercase
    desc = desc.lower()
    # Replace special chars with space
    desc = re.sub(r'[^a-z0-9\s]', ' ', desc)
    # Collapse multiple spaces
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc

def normalize_uom(uom: str | None) -> str:
    """Normalize Unit of Measure using canonical mapping."""
    if not uom:
        return "UNKNOWN"
    clean_uom = uom.strip().lower()
    # Check map
    return UOM_MAP.get(clean_uom, clean_uom.upper())

def extract_pack_size(text: str | None) -> int | None:
    """
    Attempt to extract a numeric pack size from text (e.g., 'Pack of 12', '12pk').
    Returns the integer pack size if found, else None.
    """
    if not text:
        return None

    text = text.lower()
    # Look for patterns like 'pack of 10', '10 pk', '12 units/box'
    patterns = [
        r'pack of (\d+)',
        r'(\d+)\s*pk',
        r'(\d+)\s*pack',
        r'(\d+)\s*units/box',
        r'(\d+)\s*qty/box',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))

    return None

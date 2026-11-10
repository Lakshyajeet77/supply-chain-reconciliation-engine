from __future__ import annotations
from decimal import Decimal, InvalidOperation
from datetime import date
import re

def normalize_sku(sku: str | None) -> str:
    """Strip non-alphanumeric and convert to uppercase."""
    if not sku:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', sku).upper()

def normalize_description(desc: str | None) -> str:
    """Strip leading/trailing space, convert to lowercase."""
    if not desc:
        return ""
    return desc.strip().lower()

def normalize_money(money: Decimal | str | float | None) -> Decimal | None:
    """Normalize money to Decimal."""
    if money is None:
        return None
    try:
        # Strip currency symbols and commas if it's a string
        if isinstance(money, str):
            money = re.sub(r'[^\d.-]', '', money)
        return Decimal(str(money)).quantize(Decimal("0.0001"))
    except (InvalidOperation, ValueError):
        return None

def normalize_quantity(qty: Decimal | str | float | None) -> Decimal | None:
    """Normalize quantity to Decimal."""
    if qty is None:
        return None
    try:
        if isinstance(qty, str):
            qty = re.sub(r'[^\d.-]', '', qty)
        return Decimal(str(qty)).quantize(Decimal("0.000001"))
    except (InvalidOperation, ValueError):
        return None

def normalize_date(d: date | str | None) -> date | None:
    """Normalize date to date object."""
    if isinstance(d, date):
        return d
    if not d:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(d)).date()
    except ValueError:
        return None

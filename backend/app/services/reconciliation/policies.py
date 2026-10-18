"""Explicit rounding and tolerance policies for deterministic money/qty math."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class ReconciliationPolicies:
    money_decimal_places: int = 2
    price_tolerance: Decimal = Decimal("0.00")
    quantity_tolerance: Decimal = Decimal("0.000")

    def money_quantum(self) -> Decimal:
        return Decimal("1").scaleb(-self.money_decimal_places)

    def round_money(self, value: Decimal) -> Decimal:
        return value.quantize(self.money_quantum(), rounding=ROUND_HALF_UP)

    def within_price_tolerance(self, expected: Decimal, observed: Decimal) -> bool:
        return abs(self.round_money(expected) - self.round_money(observed)) <= self.price_tolerance

    def within_quantity_tolerance(self, expected: Decimal, observed: Decimal) -> bool:
        return abs(expected - observed) <= self.quantity_tolerance

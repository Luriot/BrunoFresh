"""Unit tests for format_qty() in app.utils.format_qty.

Mirrors the frontend format.test.ts exactly to guarantee byte-for-byte
consistency between the Python and TypeScript implementations.
"""
from __future__ import annotations

import math

import pytest

from app.utils.format_qty import format_qty as _format_qty


class TestFormatQtyNullAndNonFinite:
    """Guards for degenerate float values."""

    def test_none_returns_empty(self):
        assert _format_qty(None) == ""

    def test_nan_returns_empty(self):
        assert _format_qty(float("nan")) == ""

    def test_positive_infinity_returns_empty(self):
        assert _format_qty(float("inf")) == ""

    def test_negative_infinity_returns_empty(self):
        assert _format_qty(float("-inf")) == ""


class TestFormatQtyWholeNumbers:
    def test_zero(self):
        assert _format_qty(0) == "0"

    def test_one(self):
        assert _format_qty(1) == "1"

    def test_four(self):
        assert _format_qty(4) == "4"

    def test_large_integer(self):
        assert _format_qty(100) == "100"


class TestFormatQtyNearWholeRounding:
    """Values within _TOLERANCE of a whole number are rounded."""

    def test_rounds_up_near_one(self):
        # 0.999 is within tolerance of 1.0
        assert _format_qty(0.999) == "1"

    def test_rounds_down_near_zero(self):
        # 0.001 is within tolerance of 0
        assert _format_qty(0.001) == "0"

    def test_rounds_up_fractional_part_near_whole(self):
        # 1.999 → "2"
        assert _format_qty(1.999) == "2"


class TestFormatQtyPureFractions:
    """All nine recognised fraction symbols."""

    def test_one_eighth(self):
        assert _format_qty(1 / 8) == "⅛"

    def test_one_quarter(self):
        assert _format_qty(0.25) == "¼"

    def test_one_third(self):
        assert _format_qty(1 / 3) == "⅓"

    def test_three_eighths(self):
        assert _format_qty(3 / 8) == "⅜"

    def test_one_half(self):
        assert _format_qty(0.5) == "½"

    def test_five_eighths(self):
        assert _format_qty(5 / 8) == "⅝"

    def test_two_thirds(self):
        assert _format_qty(2 / 3) == "⅔"

    def test_three_quarters(self):
        assert _format_qty(0.75) == "¾"

    def test_seven_eighths(self):
        assert _format_qty(7 / 8) == "⅞"


class TestFormatQtyMixedNumbers:
    """Whole part > 0 combined with a recognised fraction."""

    def test_one_and_half(self):
        assert _format_qty(1.5) == "1½"

    def test_two_and_quarter(self):
        assert _format_qty(2.25) == "2¼"

    def test_three_and_two_thirds(self):
        assert _format_qty(3 + 2 / 3) == "3⅔"

    def test_four_and_three_quarters(self):
        assert _format_qty(4.75) == "4¾"


class TestFormatQtyDecimalFallback:
    """Quantities without a fraction match fall back to a decimal string."""

    def test_unrecognised_fraction(self):
        assert _format_qty(1.23) == "1.23"

    def test_strips_trailing_zero(self):
        # 1.2 has no fraction match; should NOT show as "1.20"
        assert _format_qty(1.2) == "1.2"

    def test_strips_trailing_dot(self):
        # A value rounded to an integer via the fallback path should not end in '.'
        # (whole=2, frac=0.0 is handled by the <tolerance branch, so this is 2.0 → "2")
        assert _format_qty(2.0) == "2"


class TestFormatQtyNegativeNumbers:
    """Negative quantities don't occur in practice but must not crash."""

    def test_negative_whole_number(self):
        # int(-2) = -2, frac = 0 → returns str(-2) = "-2"
        assert _format_qty(-2) == "-2"

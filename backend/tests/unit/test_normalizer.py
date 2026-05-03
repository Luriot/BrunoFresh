"""Unit tests for app.services.normalizer — pure logic, no DB required."""
import pytest

from app.services.normalizer import (
    culinary_to_grams,
    get_unit_group,
    normalize_unit,
    smart_display_unit,
    to_base_unit,
)


# ── normalize_unit ────────────────────────────────────────────────────────────

class TestNormalizeUnit:
    def test_canonical_unit_passthrough_g(self):
        unit, qty = normalize_unit("g", 100)
        assert unit == "g"
        assert qty == 100

    def test_canonical_unit_passthrough_kg(self):
        unit, qty = normalize_unit("kg", 2.5)
        assert unit == "kg"
        assert qty == 2.5

    def test_canonical_unit_passthrough_ml(self):
        unit, qty = normalize_unit("ml", 250)
        assert unit == "ml"
        assert qty == 250

    def test_canonical_unit_case_insensitive(self):
        """Canonical lookup is lowercase-normalised."""
        unit, qty = normalize_unit("G", 50)
        assert unit == "g"
        assert qty == 50

    def test_alias_tablespoon(self):
        unit, qty = normalize_unit("tablespoon", 2)
        assert unit == "c. à soupe"
        assert qty == 2

    def test_alias_tbsp(self):
        unit, qty = normalize_unit("tbsp", 1)
        assert unit == "c. à soupe"

    def test_alias_tsp(self):
        unit, qty = normalize_unit("teaspoon", 3)
        assert unit == "c. à thé"
        assert qty == 3

    def test_alias_cup(self):
        unit, qty = normalize_unit("cup", 1)
        assert unit == "tasse"

    def test_alias_cups_plural(self):
        unit, qty = normalize_unit("cups", 2)
        assert unit == "tasse"
        assert qty == 2

    def test_alias_clove(self):
        unit, qty = normalize_unit("cloves", 4)
        assert unit == "gousse"

    def test_conversion_oz_to_g(self):
        unit, qty = normalize_unit("oz", 1)
        assert unit == "g"
        assert abs(qty - 28.3495) < 0.001

    def test_conversion_lb_to_kg(self):
        unit, qty = normalize_unit("lb", 1)
        assert unit == "kg"
        assert abs(qty - 0.453592) < 0.0001

    def test_conversion_fl_oz_to_ml(self):
        unit, qty = normalize_unit("fl oz", 1)
        assert unit == "ml"
        assert abs(qty - 29.5735) < 0.001

    def test_conversion_pounds_plural(self):
        unit, qty = normalize_unit("pounds", 2)
        assert unit == "kg"
        assert abs(qty - 0.907184) < 0.0001

    def test_unknown_unit_defaults_to_piece(self):
        unit, qty = normalize_unit("foobarunit", 5)
        assert unit == "piece"
        assert qty == 5

    def test_empty_unit_defaults_to_piece(self):
        unit, qty = normalize_unit("", 1)
        assert unit == "piece"

    def test_whitespace_stripped(self):
        unit, qty = normalize_unit("  g  ", 10)
        assert unit == "g"


# ── to_base_unit ─────────────────────────────────────────────────────────────

class TestToBaseUnit:
    def test_g_unchanged(self):
        assert to_base_unit("g", 100) == ("g", 100)

    def test_kg_to_g(self):
        unit, qty = to_base_unit("kg", 1.5)
        assert unit == "g"
        assert qty == 1500.0

    def test_ml_unchanged(self):
        assert to_base_unit("ml", 200) == ("ml", 200)

    def test_cl_to_ml(self):
        unit, qty = to_base_unit("cl", 10)
        assert unit == "ml"
        assert qty == 100.0

    def test_L_to_ml(self):
        unit, qty = to_base_unit("L", 1)
        assert unit == "ml"
        assert qty == 1000.0

    def test_non_mergeable_unit_unchanged(self):
        """Units outside weight/volume groups are returned as-is."""
        assert to_base_unit("piece", 3) == ("piece", 3)
        assert to_base_unit("c. à soupe", 2) == ("c. à soupe", 2)


# ── smart_display_unit ────────────────────────────────────────────────────────

class TestSmartDisplayUnit:
    def test_g_below_1000_stays_g(self):
        unit, qty = smart_display_unit("g", 500)
        assert unit == "g"
        assert qty == 500

    def test_g_at_1000_becomes_kg(self):
        unit, qty = smart_display_unit("g", 1000)
        assert unit == "kg"
        assert qty == 1.0

    def test_g_above_1000_becomes_kg(self):
        unit, qty = smart_display_unit("g", 2500)
        assert unit == "kg"
        assert qty == 2.5

    def test_ml_below_100_stays_ml(self):
        unit, qty = smart_display_unit("ml", 50)
        assert unit == "ml"
        assert qty == 50

    def test_ml_100_to_999_becomes_cl(self):
        unit, qty = smart_display_unit("ml", 250)
        assert unit == "cl"
        assert abs(qty - 25.0) < 0.01

    def test_ml_at_1000_becomes_L(self):
        unit, qty = smart_display_unit("ml", 1000)
        assert unit == "L"
        assert qty == 1.0

    def test_other_unit_unchanged(self):
        unit, qty = smart_display_unit("piece", 7)
        assert unit == "piece"
        assert qty == 7


# ── get_unit_group ────────────────────────────────────────────────────────────

class TestGetUnitGroup:
    def test_g_is_poids(self):
        assert get_unit_group("g") == "Poids"

    def test_kg_is_poids(self):
        assert get_unit_group("kg") == "Poids"

    def test_ml_is_volume(self):
        assert get_unit_group("ml") == "Volume"

    def test_L_is_volume(self):
        assert get_unit_group("L") == "Volume"

    def test_cl_is_volume(self):
        assert get_unit_group("cl") == "Volume"

    def test_unknown_unit_returns_none(self):
        assert get_unit_group("piece") is None
        assert get_unit_group("c. à soupe") is None


# ── culinary_to_grams ─────────────────────────────────────────────────────────

class TestCulinaryToGrams:
    def test_butter_tablespoon(self):
        result = culinary_to_grams("butter", "c. à soupe", 1)
        assert result is not None
        unit, qty = result
        assert unit == "g"
        assert abs(qty - 14.2) < 0.01

    def test_flour_cup(self):
        result = culinary_to_grams("flour", "tasse", 1)
        assert result is not None
        unit, qty = result
        assert unit == "g"
        assert abs(qty - 125.0) < 0.01

    def test_multiple_tablespoons(self):
        result = culinary_to_grams("sugar", "c. à soupe", 2)
        assert result is not None
        _, qty = result
        assert abs(qty - 25.0) < 0.01

    def test_unknown_ingredient_returns_none(self):
        assert culinary_to_grams("xyzunknown", "c. à soupe", 1) is None

    def test_known_ingredient_unknown_unit_returns_none(self):
        assert culinary_to_grams("butter", "kg", 1) is None

    def test_metric_unit_returns_none(self):
        """culinary_to_grams only applies to culinary units."""
        assert culinary_to_grams("sugar", "g", 100) is None

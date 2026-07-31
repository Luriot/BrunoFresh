"""Unit tests for app.services.normalizer — pure logic, no DB required."""
import pytest

from app.services.normalizer import (
    culinary_to_grams,
    extract_pack_grams_from_raw,
    get_unit_group,
    normalize_unit,
    pack_to_grams,
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


# ── pack_to_grams (sachet/paquet/boîte → g) ────────────────────────────────────

class TestPackToGrams:
    def test_baking_powder_paquet(self):
        result = pack_to_grams("baking powder", "paquet", 1)
        assert result is not None
        unit, qty = result
        assert unit == "g"
        assert abs(qty - 11.0) < 0.01

    def test_canned_tomatoes_boite(self):
        result = pack_to_grams("canned tomatoes", "boîte", 2)
        assert result is not None
        _, qty = result
        assert abs(qty - 800.0) < 0.01

    def test_trims_name_whitespace(self):
        """Ingredient names stored lower + stripped."""
        result = pack_to_grams("  Baking Powder  ", "paquet", 1)
        assert result is not None
        assert result[1] == 11.0

    def test_two_paquet(self):
        result = pack_to_grams("active dry yeast", "paquet", 2)
        assert result is not None
        assert abs(result[1] - 14.0) < 0.01

    def test_unknown_ingredient_returns_none(self):
        assert pack_to_grams("unicorn dust", "paquet", 1) is None

    def test_known_ingredient_unknown_pack_unit_returns_none(self):
        """baking powder has 'paquet' but not 'boîte'."""
        assert pack_to_grams("baking powder", "boîte", 1) is None

    def test_metric_unit_returns_none(self):
        """pack_to_grams is a no-op for non-pack units."""
        assert pack_to_grams("baking powder", "g", 100) is None
        assert pack_to_grams("baking powder", "c. à soupe", 1) is None

    def test_can_capitalized_unit_passthrough(self):
        """If the aggregator passes through capitalised 'Paquet', it should NOT match
        (callers must canonicalise first via normalize_unit). This documents the contract."""
        assert pack_to_grams("baking powder", "Paquet", 1) is None


# ── extract_pack_grams_from_raw (retro-calibration) ────────────────────────────

class TestExtractPackGramsFromRaw:
    def test_sachet_with_paren_g(self):
        assert extract_pack_grams_from_raw("1 sachet de levure chimique (7 g)") == 7.0

    def test_sachet_no_space_g(self):
        assert extract_pack_grams_from_raw("1 sachet de levure 7g") == 7.0

    def test_fr_decimal_comma(self):
        assert extract_pack_grams_from_raw("1 sachet (7,5 g)") == 7.5

    def test_boite_near_g(self):
        assert extract_pack_grams_from_raw("2 boîtes de tomates pelées (400 g net)") == 400.0

    def test_grams_before_unit_word(self):
        assert extract_pack_grams_from_raw("7 g de levure, 1 sachet") == 7.0

    def test_picks_closest_when_multiple_grams(self):
        """If two gram values appear, the closest to the pack word wins."""
        raw = "200 g de chocolat, 1 sachet de levure (7 g)"
        assert extract_pack_grams_from_raw(raw) == 7.0

    def test_no_pack_word_returns_none(self):
        assert extract_pack_grams_from_raw("200 g de chocolat") is None

    def test_no_grams_value_returns_none(self):
        assert extract_pack_grams_from_raw("1 sachet de levure chimique") is None

    def test_empty_or_none(self):
        assert extract_pack_grams_from_raw("") is None
        assert extract_pack_grams_from_raw(None) is None

    def test_grams_too_far_returns_none(self):
        """Grams more than 40 chars from the pack word are ignored."""
        raw = "1 sachet " + "x" * 50 + " 7 g"
        assert extract_pack_grams_from_raw(raw) is None


# ── pack_to_grams priority chain ──────────────────────────────────────────────

class TestPackToGramsPriority:
    def test_raw_beats_static(self):
        """Raw text '(7 g)' overrides the static 11 g/sachet for baking powder."""
        result = pack_to_grams("baking powder", "paquet", 2, raw_string="2 sachets (7 g)")
        assert result == ("g", 14.0)

    def test_raw_beats_admin_and_static(self):
        result = pack_to_grams(
            "baking powder", "paquet", 1,
            raw_string="1 sachet (8 g)",
            admin_override=9.0,
        )
        assert result == ("g", 8.0)

    def test_admin_beats_static(self):
        """With no raw figure, admin override wins over static."""
        result = pack_to_grams(
            "baking powder", "paquet", 1,
            admin_override=9.0,
        )
        assert result == ("g", 9.0)

    def test_static_fallback_when_no_raw_no_admin(self):
        """Existing behaviour preserved when neither raw nor admin provides a value."""
        result = pack_to_grams("baking powder", "paquet", 1)
        assert result == ("g", 11.0)

    def test_unknown_pack_falls_through_to_none_with_raw_no_grams(self):
        """Unknown ingredient + raw without grams figure → still None."""
        assert pack_to_grams(
            "unicorn spice", "paquet", 1,
            raw_string="1 sachet d'épice licorne",
            admin_override=None,
        ) is None

    def test_admin_override_only_no_static(self):
        """Admin override applies even when the static table has no entry."""
        result = pack_to_grams(
            "unicorn spice", "paquet", 3,
            admin_override=12.0,
        )
        assert result == ("g", 36.0)

    def test_boite_admin_override(self):
        result = pack_to_grams(
            "canned tomatoes", "boîte", 2,
            admin_override=410.0,
        )
        assert result == ("g", 820.0)

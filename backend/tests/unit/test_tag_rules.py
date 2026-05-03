"""Unit tests for app.services.tag_rules — pure logic, no DB required."""
import pytest

from app.models import Tag
from app.services.tag_rules import match_tags


def _make_tag(name: str) -> Tag:
    """Build an in-memory Tag ORM object (not persisted)."""
    t = Tag()
    t.id = hash(name)
    t.name = name
    t.color = "#000000"
    return t


def _tag_names(tags: list[Tag]) -> set[str]:
    return {t.name for t in tags}


ALL_TAGS = [
    _make_tag("Rapide"),
    _make_tag("Végétarien"),
    _make_tag("Végan"),
    _make_tag("Épicé"),
    _make_tag("Peu de vaisselle"),
    _make_tag("Healthy"),
    _make_tag("Comfort food"),
    _make_tag("Pâtes"),
    _make_tag("Riz"),
    _make_tag("Poulet"),
    _make_tag("Poisson"),
    _make_tag("Dessert"),
    _make_tag("Petit-déjeuner"),
    _make_tag("Batch cooking"),
]


class TestRapideTag:
    def test_prep_time_at_threshold_matches(self):
        result = match_tags(ALL_TAGS, "Some Recipe", [], prep_time_minutes=30)
        assert "Rapide" in _tag_names(result)

    def test_prep_time_below_threshold_matches(self):
        result = match_tags(ALL_TAGS, "Some Recipe", [], prep_time_minutes=15)
        assert "Rapide" in _tag_names(result)

    def test_prep_time_above_threshold_no_match(self):
        result = match_tags(ALL_TAGS, "Some Recipe", [], prep_time_minutes=31)
        assert "Rapide" not in _tag_names(result)

    def test_prep_time_none_no_match(self):
        result = match_tags(ALL_TAGS, "Some Recipe", [], prep_time_minutes=None)
        assert "Rapide" not in _tag_names(result)


class TestKeywordMatching:
    def test_poisson_from_salmon_in_title(self):
        result = match_tags(ALL_TAGS, "Grilled Saumon with vegetables", [], None)
        assert "Poisson" in _tag_names(result)

    def test_poisson_not_triggered_by_fish_sauce_alone(self):
        """STRIP_PHRASES: 'fish sauce' should not trigger Poisson."""
        result = match_tags(ALL_TAGS, "Asian noodles", ["fish sauce", "soy sauce", "noodles"], None)
        assert "Poisson" not in _tag_names(result)

    def test_poisson_triggered_when_real_fish_also_present(self):
        """fish sauce stripped, but thon still matches Poisson."""
        result = match_tags(ALL_TAGS, "Tuna salad", ["thon", "fish sauce", "lettuce"], None)
        assert "Poisson" in _tag_names(result)

    def test_vegetarien_from_ingredient_tofu(self):
        result = match_tags(ALL_TAGS, "Bowl recipe", ["tofu", "rice", "sesame"], None)
        assert "Végétarien" in _tag_names(result)

    def test_pates_from_title_spaghetti(self):
        result = match_tags(ALL_TAGS, "Spaghetti Carbonara", ["bacon", "eggs", "parmesan"], None)
        assert "Pâtes" in _tag_names(result)

    def test_poulet_from_ingredient_chicken(self):
        result = match_tags(ALL_TAGS, "Grilled dinner", ["chicken", "garlic", "lemon"], None)
        assert "Poulet" in _tag_names(result)

    def test_riz_from_tag_name_itself(self):
        """Tag name 'Riz' is an implicit keyword."""
        result = match_tags(ALL_TAGS, "Riz cantonais", ["egg", "green onion"], None)
        assert "Riz" in _tag_names(result)

    def test_dessert_from_chocolate_ingredient(self):
        result = match_tags(ALL_TAGS, "Fondant recipe", ["chocolate", "butter", "sugar", "eggs"], None)
        assert "Dessert" in _tag_names(result)

    def test_multiple_tags_matched_at_once(self):
        result = match_tags(
            ALL_TAGS,
            "Quick chicken pasta",
            ["chicken", "pasta", "cream"],
            prep_time_minutes=20,
        )
        names = _tag_names(result)
        assert "Rapide" in names
        assert "Poulet" in names
        assert "Pâtes" in names

    def test_empty_tags_list_returns_empty(self):
        result = match_tags([], "Spaghetti Bolognese", ["beef", "pasta"], 25)
        assert result == []

    def test_no_match_returns_empty(self):
        """A recipe with no matching keywords → no tags."""
        result = match_tags(ALL_TAGS, "Xyz dish", ["abc", "def"], prep_time_minutes=60)
        assert result == []

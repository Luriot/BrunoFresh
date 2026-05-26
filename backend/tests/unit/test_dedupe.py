"""Unit tests for app.services.dedupe — pure logic, no DB required."""
import pytest

from app.services.dedupe import extract_image_base_key, looks_like_duplicate, similarity_score


class TestExtractImageBaseKey:
    # The two real-world HF URLs from the bug report
    _URL_A = (
        "https://img.hellofresh.com/f_auto,fl_lossy,q_auto,w_500/hellofresh_s3/image/"
        "HF_Y25_R202_W40_FR_QFR20943-16_Main_3_high-cf1af71a.jpg"
    )
    _URL_B = (
        "https://img.hellofresh.com/f_auto,fl_lossy,q_auto,w_500/hellofresh_s3/image/"
        "HF_Y25_R202_W40_FR_QFR20943-16_Main_3_high-1d2efe42.jpg"
    )

    def test_same_recipe_different_cdn_hash_gives_same_key(self):
        """The core fix: two URLs of the same recipe must produce identical keys."""
        assert extract_image_base_key(self._URL_A) == extract_image_base_key(self._URL_B)

    def test_returned_key_is_base_filename_without_hash(self):
        key = extract_image_base_key(self._URL_A)
        assert key == "HF_Y25_R202_W40_FR_QFR20943-16_Main_3_high"

    def test_different_recipes_give_different_keys(self):
        url_other = (
            "https://img.hellofresh.com/f_auto,fl_lossy,q_auto,w_500/hellofresh_s3/image/"
            "HF_Y25_R202_W40_FR_ABC12345-99_Main_1_high-aabb1122.jpg"
        )
        assert extract_image_base_key(self._URL_A) != extract_image_base_key(url_other)

    def test_url_without_cdn_hash_returns_none(self):
        url = "https://example.com/images/my_recipe.jpg"
        assert extract_image_base_key(url) is None

    def test_none_input_returns_none(self):
        assert extract_image_base_key(None) is None

    def test_empty_string_returns_none(self):
        assert extract_image_base_key("") is None

    def test_short_hash_is_matched(self):
        """Hashes as short as 6 hex chars should still be stripped."""
        url = "https://img.hellofresh.com/hellofresh_s3/image/SomeRecipe-ab12cd.jpg"
        assert extract_image_base_key(url) == "SomeRecipe"

    def test_long_hash_is_matched(self):
        """Hashes up to 16 hex chars should be stripped."""
        url = "https://img.hellofresh.com/hellofresh_s3/image/SomeRecipe-0123456789abcdef.jpg"
        assert extract_image_base_key(url) == "SomeRecipe"

    def test_non_hex_suffix_is_not_stripped(self):
        """A suffix that is not pure hex should not be stripped (returns None)."""
        url = "https://img.hellofresh.com/hellofresh_s3/image/SomeRecipe-notahex.jpg"
        assert extract_image_base_key(url) is None



class TestSimilarityScore:
    def test_identical_recipes(self):
        title_score, ing_score = similarity_score(
            "Pasta Bolognese",
            ["beef", "tomato", "pasta", "onion"],
            "Pasta Bolognese",
            ["beef", "tomato", "pasta", "onion"],
        )
        assert title_score == 100.0
        assert ing_score == 1.0

    def test_completely_different_recipes(self):
        title_score, ing_score = similarity_score(
            "Chocolate Cake",
            ["chocolate", "flour", "sugar", "eggs"],
            "Grilled Salmon",
            ["salmon", "lemon", "garlic", "olive oil"],
        )
        assert title_score < 50
        assert ing_score == 0.0

    def test_empty_ingredient_lists_give_zero_jaccard(self):
        _, ing_score = similarity_score("Title", [], "Title", [])
        assert ing_score == 0.0

    def test_one_empty_ingredient_list(self):
        _, ing_score = similarity_score("Title", ["beef"], "Title", [])
        assert ing_score == 0.0

    def test_partial_title_match(self):
        """Near-identical titles should score high."""
        title_score, _ = similarity_score(
            "Spaghetti Carbonara",
            ["pasta"],
            "Carbonara Spaghetti",
            ["pasta"],
        )
        assert title_score >= 80

    def test_partial_ingredient_overlap(self):
        _, ing_score = similarity_score(
            "Recipe A",
            ["a", "b", "c", "d"],
            "Recipe A",
            ["a", "b", "c", "e"],
        )
        # 3 common out of 5 union
        assert abs(ing_score - 3 / 5) < 0.01

    def test_title_normalisation_ignores_case_and_punctuation(self):
        title_score, _ = similarity_score(
            "pasta bolognese!",
            ["beef"],
            "PASTA BOLOGNESE",
            ["beef"],
        )
        assert title_score == 100.0


class TestLooksLikeDuplicate:
    def test_near_duplicate_returns_true(self):
        assert looks_like_duplicate(
            "Pasta Carbonara",
            ["pasta", "eggs", "bacon", "parmesan", "pepper"],
            "Pasta Carbonara",
            ["pasta", "eggs", "bacon", "parmesan", "pepper"],
        )

    def test_different_recipe_returns_false(self):
        assert not looks_like_duplicate(
            "Beef Stew",
            ["beef", "carrot", "potato", "onion"],
            "Lemon Tart",
            ["lemon", "butter", "sugar", "flour"],
        )

    def test_same_title_different_ingredients_returns_false(self):
        """Title matches but ingredient set is very different → not a duplicate."""
        assert not looks_like_duplicate(
            "Chicken Dish",
            ["chicken", "rice", "pea", "carrot", "onion", "garlic", "tomato", "spice"],
            "Chicken Dish",
            ["chicken", "pasta", "cream", "mushroom"],
        )

    def test_custom_thresholds_override(self):
        """Lower thresholds make matching more permissive."""
        assert looks_like_duplicate(
            "Soup",
            ["carrot", "celery"],
            "Soup de Carottes",
            ["carrot", "celery"],
            title_threshold=50,
            ingredients_threshold=0.5,
        )

"""Unit tests for app.services.dedupe — pure logic, no DB required."""
import pytest

from app.services.dedupe import looks_like_duplicate, similarity_score


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

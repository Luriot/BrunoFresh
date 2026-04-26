from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# Many-to-many association table for recipe tags
recipe_tags = Table(
    "recipe_tags",
    Base.metadata,
    Column("recipe_id", Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    source_domain: Mapped[str] = mapped_column(String(120), index=True)
    image_local_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_original_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    instructions_text: Mapped[str] = mapped_column(Text)
    instruction_steps_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_servings: Mapped[int] = mapped_column(Integer, default=2)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    shopping_list_links: Mapped[list["ShoppingListRecipe"]] = relationship(
        "ShoppingListRecipe", back_populates="recipe", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=recipe_tags, back_populates="recipes")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_en: Mapped[str] = mapped_column(String(200), index=True, unique=True)
    name_fr: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="Pantry", index=True)
    is_normalized: Mapped[bool] = mapped_column(Boolean, default=True)

    recipe_links: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="ingredient"
    )
    translations: Mapped[list["IngredientTranslation"]] = relationship(
        "IngredientTranslation", back_populates="ingredient", cascade="all, delete-orphan"
    )


class IngredientTranslation(Base):
    __tablename__ = "ingredient_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    lang_code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(200))

    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="translations")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    ingredient_id: Mapped[int | None] = mapped_column(ForeignKey("ingredients.id"), nullable=True)
    raw_string: Mapped[str] = mapped_column(String(400))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(30), default="unparsed")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient: Mapped[Ingredient | None] = relationship("Ingredient", back_populates="recipe_links")


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(1024), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(String(800), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    needs_review_blob: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ShoppingListItem"]] = relationship(
        "ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan"
    )
    recipe_links: Mapped[list["ShoppingListRecipe"]] = relationship(
        "ShoppingListRecipe", back_populates="shopping_list", cascade="all, delete-orphan"
    )


class ShoppingListRecipe(Base):
    __tablename__ = "shopping_list_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shopping_list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"), index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    target_servings: Mapped[int] = mapped_column(Integer, default=2)

    shopping_list: Mapped[ShoppingList] = relationship("ShoppingList", back_populates="recipe_links")
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="shopping_list_links")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shopping_list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"), index=True)
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"), nullable=True, index=True)
    ingredient_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingredients.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    name_fr: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(30), default="item")
    category: Mapped[str] = mapped_column(String(80), default="Other", index=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    is_already_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    shopping_list: Mapped[ShoppingList] = relationship("ShoppingList", back_populates="items")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)

    recipes: Mapped[list["Recipe"]] = relationship("Recipe", secondary=recipe_tags, back_populates="tags")


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    name_fr: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ingredient: Mapped["Ingredient | None"] = relationship("Ingredient")


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    week_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entries: Mapped[list["MealPlanEntry"]] = relationship(
        "MealPlanEntry", back_populates="meal_plan", cascade="all, delete-orphan"
    )


class MealPlanEntry(Base):
    __tablename__ = "meal_plan_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Monday … 6=Sunday
    meal_slot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_servings: Mapped[int] = mapped_column(Integer, default=2)

    meal_plan: Mapped[MealPlan] = relationship("MealPlan", back_populates="entries")
    recipe: Mapped[Recipe] = relationship("Recipe")

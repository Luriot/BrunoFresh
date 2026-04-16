from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    source_domain: Mapped[str] = mapped_column(String(120), index=True)
    image_local_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_original_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    instructions_text: Mapped[str] = mapped_column(Text)
    base_servings: Mapped[int] = mapped_column(Integer, default=2)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_en: Mapped[str] = mapped_column(String(200), index=True, unique=True)
    category: Mapped[str] = mapped_column(String(80), default="Pantry", index=True)
    is_normalized: Mapped[bool] = mapped_column(Boolean, default=True)

    recipe_links: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="ingredient"
    )


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

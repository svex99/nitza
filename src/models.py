from __future__ import annotations
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class Ingredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    amount: float
    measure: str
    food: str
    verified: bool = Field(default=False)
    section: str = Field(default="")

    recipe_id: str = Field(default=None, foreign_key="recipe.id")
    recipe: Recipe = Relationship(back_populates="ingredients")


class Recipe(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    rations: int
    category: str
    price: float = Field(default=0)

    ingredients: list[Ingredient] = Relationship(back_populates="recipe")

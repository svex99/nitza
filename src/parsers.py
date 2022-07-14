import os
import re
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from src.models import Recipe, Ingredient


class RecipeParser:

    def __init__(self, key: str, text: str, category: str):
        lines = [ln for ln in text.split("\n") if ln and not ln.isspace()]

        self.key = key
        self.category = category
        self.name: str = lines[0]
        self.ingredients: list[Ingredient] = []

        section = None
        for line in lines:
            if line.startswith("-"):
                section = line.split(" ")[1]
            elif line[0].isnumeric():
                self.ingredients.append(
                    Ingredient(
                        text=line,
                        amount=0,       # TODO
                        measure="",     # TODO
                        food="",        # TODO
                        section=section,
                        recipe_id=self.key
                    )
                )

        cups = re.search(r"Da.+?taza", lines[-1])
        if cups is None:
            rations = re.search(r"Da .*?(?P<rations>\d+)", lines[-1])
            assert rations is not None, f"{self.name}: rations was not found"
            self.rations = int(rations["rations"])
        else:
            self.rations = -1

    def __str__(self):
        return (
            f"{self.name} ({self.rations})\n" +
            "\n".join(map(str, self.ingredients))
        )

    def __repr__(self):
        return str(self)
    
    def save_to_db(self, session: Session):
        recipe = session.get(Recipe, self.key)
        if not recipe:
            session.add(
                Recipe(
                    id=self.key,
                    name=self.name,
                    rations=self.rations,
                    category=self.category,
                    price=0
                )
            )
            for ingredient in self.ingredients:
                session.add(ingredient)
    

class RecipesData(dict):

    def __init__(self, root: Path, verbose: bool = True):
        self.root = root
        self.empty_recipes: set[str] = set()
        self.verbose = verbose

        self._update_data()

    def _update_data(self):
        for category in self.root.iterdir():
            count = 0
            for file in category.iterdir():
                key = file.name[:-4]
                text = file.read_text("utf8")
                if text and not text.isspace():
                    try:
                        self[key] = RecipeParser(key, text, category)
                    except Exception as e:
                        print(f"Error parsing recipe {key!r}")
                        raise e
                    count += 1
                else:
                    self.empty_recipes.add(key)
            if self.verbose:
                print(f"Recipes for {category.name!r}: {count}")

    @property
    def recipes(self):
        return self.values()

    def __getitem__(self, item: str) -> RecipeParser:
        """Dumb method for type hinting"""
        return super().__getitem__(item)

    def __str__(self):
        recipes = len(self)
        empty = len(self.empty_recipes)
        total = recipes + empty
        return f"{self.__class__.__name__}({recipes=}, {empty=}, {total=})"
    
    def __repr__(self):
        return str(self)

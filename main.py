from __future__ import annotations
from pathlib import Path
import json
import re
from unicodedata import numeric

import spacy
from spacy.tokens import Doc
from rich.console import Console
import typer

from src.parsers import RecipesData

nlp = spacy.load(Path("files/nlp/nlp_model"))
data = RecipesData(Path("files/recipes"), verbose=False)
console = Console()
app = typer.Typer()

MEASURES = json.load(Path("files/measures.json").open(encoding="latin1"))


def format_doc(doc: Doc) -> str:
    colors = {
        "AMOUNT": "cyan",
        "MEASURE": "yellow",
        "FOOD": "green",
        "LOC": "blue",
    }
    text = ""
    last = 0
    for e in doc.ents:
        text += f"{doc.text[last:e.start_char]}[bold {colors.get(e.label_, 'red')}]{e.text}[/]"
        last = e.end_char
    return text + doc.text[last:]


def get_measure(text: str) -> str | None:
    for m in MEASURES:
        if re.match(MEASURES[m], text):
            return m


def amount_to_float(amount: str) -> float:
    if len(amount) == 1:
        v = numeric(amount)
    elif amount[-1].isdigit():
        # normal number, ending in [0-9]
        v = float(amount)
    else:
        # Assume the last character is a vulgar fraction
        v = float(amount[:-1]) + numeric(amount[-1])
    return round(v, 2)


def get_labels(doc: Doc) -> tuple[tuple[float | None, str | None, list[str] | None], bool]:
    amounts, measures, foods = [], [], []
    for e in doc.ents:
        if e.label_ == "AMOUNT" or e.label_ == "LOC":   # model was labeling measures as locations
            if e.text.isnumeric():
                amounts.append(amount_to_float(e.text))  # TODO: convert to float
        elif e.label_ == "MEASURE":
            m = get_measure(e.text)
            if m is not None:
                measures.append(m)
        elif e.label_ == "FOOD":
            foods.append(e.text)
    if len(amounts) == 1 and len(measures) <= 1 and len(foods) > 0:
        return (amounts[0], measures[0] if measures else "", foods), True
    else:
        return (amounts, measures, foods), False


@app.command()
def check():
    valid_labels = 0
    not_vaild = []
    total = 0
    all_measures = set()
    all_foods = set()
    for recipe in data.recipes:
        for ing in recipe.ingredients:
            doc = nlp(ing.text)
            (amount, measure, foods), valid = get_labels(doc)
            if valid:
                all_measures.add(measure)
                for food in foods:
                    all_foods.add(food)
                valid_labels += 1
            else:
                not_vaild.append(doc)
            total += 1
    # console.print("\n".join(map(str, all_measures)))
    # for nv in not_vaild: console.print(format_doc(nv))
    console.print(*sorted(all_foods), sep="\n")
    console.print(f"Measures: {len(all_measures)}")
    console.print(f"Food: {len(all_foods)}")
    console.print(f"Valid: {valid_labels} / {total}")

@app.command()
def test():
    for recipe in data.recipes:
        print("Recipe:", recipe.name)
        for ing in recipe.ingredients:
            doc = nlp(ing.text)
            console.print(format(doc), end="")

            action = input("\t> ")
            if action == "i":
                print([f"{e}: {e.label_}" for e in doc.ents])
            elif action == "q":
                return

@app.command()
def test_one():
    while True:
        text = input("> ")
        doc = nlp(text)
        console.print(format_doc(doc))
        print([f"{e}: {e.label_}" for e in doc.ents])

@app.command()
def update_ing_db():
    import sqlite3

    con = sqlite3.connect(Path("files/database.db"))
    
    for row in con.execute("SELECT * FROM ingredient WHERE verified = 0 GROUP BY text"):
        id, text = row[0], row[1]
        doc = nlp(text)
        (amount, measure, foods), valid = get_labels(doc)
        console.print(format_doc(doc), f"\t\t(#{id})")
        if not valid:
            tokens = text.split(" ")
            amount = amount_to_float(tokens[0])
            try:
                m_index = int(input("m? > "))
            except ValueError:
                measure = ""
            else:
                measure = get_measure(tokens[m_index])
            f_start, f_end = map(int, input("f? > ").split(" "))
            foods = [" ".join(tokens[f_start:f_end])]
        console.print((amount, measure, foods))
        action = input("> ")
        if action == "y":
            with con:
                con.execute("""
                    UPDATE ingredient
                    SET amount = ?,
                        measure = ?,
                        food = ?,
                        verified = 1
                    WHERE text = ?""",
                    (amount, measure, foods[0], text)
                )
        elif action == "s":
            return
        

@app.command()
def prices():
    prices = json.load(Path("files/prices.json").open(encoding="latin1"))
    empty = {e["food"] for e in prices}
    for e in prices:
        if e["iprice"] != 0 or e["fprice"] != 0:
            try:
                empty.remove(e["food"])
            except KeyError:
                pass
    console.print(*sorted(empty), sep="\n")
    console.print(f"Total: {len(empty)}")


@app.command()
def update_prices():
    import sqlite3

    prices_data = json.load(Path("files/prices.json").open(encoding="utf8"))
    prices = {}
    for entry in prices_data:
        food, measure = entry["food"], entry["measure"]
        price = entry["iprice"] if entry["iprice"] != 0 else entry["fprice"]
        if food not in prices:
            prices[food] = {}
        prices[food][measure] = price
    # console.print(prices)

    con = sqlite3.connect(Path("files/database.db"))
    with con:
        for (recipe_id, ) in con.execute("SELECT id FROM recipe"):
            cost = 0
            ingredients_result = con.execute("""
                SELECT amount, measure, food
                FROM ingredient
                WHERE recipe_id = ?""",
                (recipe_id, )
            )
            for (amount, measure, food) in ingredients_result:
                try:
                    cost += amount * prices[food][measure]
                except KeyError as e:
                    console.print_exception(show_locals=True)
                    return
            # console.print(f"Cost of [bold green]{recipe_id}[/] ({rations}): {cost}")
            con.execute("UPDATE recipe SET price = ? WHERE id = ?", (round(cost, 0), recipe_id))


if __name__ == "__main__":
    app()

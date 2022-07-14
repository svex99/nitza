# nitza

The structured data for the recipes is in a sqlite file at `files/database.db`, there can be changed the values manually.

To update the price of the food, should be done at `files/price.json`. Then run the next command to sync the database file.

```
python main.py update-prices
```

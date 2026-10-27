# Python JSON Sorter

Builds a sorted product menu (JSON) from a products spreadsheet (`.ods`), an items file (`.csv`) and a
set of weighting rules (`.json`). A small PHP web UI lets you upload the files, edit the items table and
run the sort.

Everything lives in the [`sort_json`](sort_json) folder:

| File | Purpose |
| --- | --- |
| `sort_json.py` | Reads the products and items files, fills in missing item details, and writes the sorted menu JSON. |
| `take_screenshot.py` | Saves a full-page screenshot (and PDF) of a menu page. |
| `index.html` | Web UI for uploading files, editing items and running the sort. |
| `*.php` | Endpoints used by the web UI (`common.php` holds shared helpers). |
| `tests/` | Tests for `sort_json.py`. |

## Requirements

- Python 3.8 or higher
- For `sort_json.py`: `pip install -r sort_json/requirements.txt` (pandas, odfpy, python-bidi)
- For `take_screenshot.py`: `pip install -r sort_json/screenshot_requirements.txt`, then `python -m playwright install chromium`
- For the web UI: PHP 7.1 or higher

## Usage

All file names are relative to a `data` folder in the current directory.

```bash
cd sort_json
./sort_json.py -f products.ods -i items.csv -r rules.json -s sorted.json \
    ItemCode=2 ItemPrice=9 TreatmentGroup=1 DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5
```

The `KEY=COLUMN` arguments give the 1-based column of each field in the products sheet. `ItemCode`,
`ItemPrice`, `TreatmentGroup`, `DoseFamily`, `Type` and `ItemName` are required; `HebrewName` and
`HebrewBrand` are optional. When `TreatmentGroup`, `DoseFamily` and `Type` share one column, it is read
as a single description such as `תפרחת Indica T20 C4`.

| Option | Default | Meaning |
| --- | --- | --- |
| `-f` | (required) | Products spreadsheet (`.ods`). |
| `-i` | `items.csv` | Items file. Products missing from it are added, and missing names, brands and treatment groups are filled in. |
| `-r` | `rules.json` | Weighting rules. If the file does not exist, every value gets the same weight. |
| `-s` | `sorted_json.json` | Output file. |
| `-n` | | Create an empty rules file to fill in if it does not exist. |

The output groups items by `Type`, then by `DoseFamily`, and sorts each level by weight, heaviest first.

### Rules file

```json
{
   "Expressions": {
      "ItemPrice>=150": 5,
      "(THC_Percent>20)|!(Brand='Brand A')": 2,
      "ItemPrice<60": -99999
   },
   "Type": {"תפרחות": 10},
   "DoseFamily": {"T20/C4": 3},
   "Brand": {"Brand A": 4}
}
```

- Each item starts at 0. Every expression it matches adds that expression's weight.
- For every field, the weight listed for the item's value is added, or 1 when the value has no entry.
- The `Type` and `DoseFamily` entries also order the groups.
- A weight of `-99999` removes the item or group from the menu.
- Expressions compare a field with a value using `=`, `<>`, `<`, `<=`, `>` or `>=`. Put text values in
  single quotes, and combine comparisons with `&` (and), `|` (or), `!` (not) and parentheses.

## Tests

```bash
cd sort_json
python -m pytest tests
```

## License

This project is licensed under the MIT License.

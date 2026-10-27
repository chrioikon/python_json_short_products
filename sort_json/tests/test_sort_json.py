import json
import os
import shutil
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sort_json  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

# Column numbers used by store_items.php.
COLUMNS = {"ItemCode": 2, "ItemPrice": 9, "TreatmentGroup": 1, "DoseFamily": 1, "Type": 1,
           "ItemName": 3, "HebrewName": 4, "HebrewBrand": 5}


def products():
    """The products sheet, as pd.read_excel(..., engine="odf") would return it."""
    return pd.DataFrame({
        "Desc": ["תפרחת Indica T20 C4", "תפרחת Sativa T22 C1", "מיצוי Balanced T10 C10",
                 "מחסנית למשאף Indica T20 C4", "תפרחת Indica T20 C4", "שונות Sativa T5 C5"],
        "Code": [101, 102, 103, 104, 105, 106],
        "Name": ["Brand1 Purple Haze", "Brand2 Lemon", "Brand3 Oil", "Brand1 Vape", "Brand4 Kush", "Brand5 Misc"],
        "HebName": ["פרפל הייז", None, "שמן", "וייפ", "קוש", "שונות"],
        "HebBrand": ["מותג1", None, "מותג3", "מותג1", "מותג4", "מותג5"],
        "x6": [None] * 6, "x7": [None] * 6, "x8": [None] * 6,
        "Price": [100, 120, 200, 150, 90, 50],
    })


@pytest.fixture
def data_dir(tmp_path):
    for name in ("items.csv", "rules.json"):
        shutil.copy(os.path.join(FIXTURES, name), tmp_path / name)
    return tmp_path


def test_run_matches_expected_menu(data_dir):
    sort_json.run(products(), str(data_dir / "items.csv"), str(data_dir / "rules.json"),
                  str(data_dir / "out.json"), COLUMNS)

    with open(data_dir / "out.json", encoding="utf8") as f:
        menu = json.load(f)
    with open(os.path.join(FIXTURES, "expected_menu.json"), encoding="utf8") as f:
        assert menu == json.load(f)


def test_run_updates_items_file(data_dir):
    sort_json.run(products(), str(data_dir / "items.csv"), str(data_dir / "rules.json"),
                  str(data_dir / "out.json"), COLUMNS)

    items = sort_json.read_items(str(data_dir / "items.csv")).set_index("ItemCode")
    # "unknown" name/brand are replaced by the Hebrew ones from the products sheet.
    assert items.loc[101, "ItemNameHebrew"] == "פרפל הייז"
    assert items.loc[101, "TreatmentGroup"] == "I"
    # Existing names are kept.
    assert items.loc[103, "ItemNameHebrew"] == "שמן קיים"
    # New products are added; without a Hebrew name the English one is marked with "*".
    assert sorted(items.index) == [101, 102, 103, 104, 105, 106]
    assert items.loc[102, "ItemNameHebrew"] == "*Lemon"


def test_run_creates_rules_file(data_dir):
    rules_file = data_dir / "new_rules.json"
    sort_json.run(products(), str(data_dir / "items.csv"), str(rules_file), str(data_dir / "out.json"),
                  COLUMNS, create_rules=True)

    with open(rules_file, encoding="utf8") as f:
        rules = json.load(f)
    assert rules["Expressions"] == {}
    assert rules["Type"] == {}


def test_main_reports_missing_file(tmp_path, monkeypatch, capsys):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    args = ["%s=%d" % item for item in COLUMNS.items()] + ["-f", "missing.ods"]

    assert sort_json.main(args) == 1
    assert "Please try again" in capsys.readouterr().out


@pytest.mark.parametrize("argument", ["ItemCode=x", "ItemCode=0", "Unknown=1", "ItemCode"])
def test_main_rejects_bad_column_arguments(argument):
    with pytest.raises(SystemExit):
        sort_json.main([argument, "-f", "products.ods"])


def test_main_requires_all_keys():
    with pytest.raises(SystemExit):
        sort_json.main(["ItemCode=1", "-f", "products.ods"])


@pytest.mark.parametrize("expression, expected", [
    ("Price>=100", True),
    ("Price>100", False),
    ("Price<=100", True),
    ("Price<100", False),
    ("Price=100", True),
    ("Price<>100", False),
    ("Brand='X'", True),
    ("Brand='X'&Price>100", False),
    ("Brand='Y'|Price=100", True),
    ("!(Brand='Y')", True),
    ("!Brand='X'", False),
    ("(Price>100)|!(Brand='Y')", True),
    ("(Price>100|Brand='X')&Price<200", True),
])
def test_evaluate_python_cond(expression, expected):
    assert sort_json.evaluate_python_cond(expression, {"Price": 100, "Brand": "X"}) is expected


def test_comparison_with_none_is_false():
    assert sort_json.evaluate_python_cond("Price>1", {"Price": None}) is False


@pytest.mark.parametrize("expression", ["Missing=1", "Price=abc", "Price"])
def test_bad_expressions_raise(expression):
    with pytest.raises(sort_json.SortJsonError):
        sort_json.evaluate_python_cond(expression, {"Price": 100})


def make_item(code, price):
    item = {key: None for key in sort_json.OUTPUT_TAIL_KEYS + sort_json.OUTPUT_DROPPED_KEYS}
    item.update(ItemCode=code, ItemPrice=price)
    return item


def test_sort_by_weight_orders_and_removes():
    rules = {"Expressions": {"ItemPrice>150": 10}, "ItemCode": {"3": sort_json.REMOVE_WEIGHT}}
    items = [make_item(1, 100), make_item(2, 200), make_item(3, 300)]

    result = sort_json.sort_by_weight(items, rules)

    assert [item["ItemCode"] for item in result] == [2, 1]
    assert result[0]["weight"] > result[1]["weight"]
    assert "THC" not in result[0] and "CBD" not in result[0]
    assert list(result[0])[-len(sort_json.OUTPUT_TAIL_KEYS) - 1:] == ["BmCode"] + sort_json.OUTPUT_TAIL_KEYS


def test_numeric_rule_weight_is_counted_once():
    rules = {"Expressions": {}, "ItemPrice": {"100": 5}}
    base = sort_json.item_weight({"ItemPrice": 1}, rules)
    assert sort_json.item_weight({"ItemPrice": 100}, rules) == base - 1 + 5


@pytest.mark.parametrize("thc, cbd, expected", [
    ("20", "4", "20-4"), ("20", "None", "20"), ("None", "4", "4"), ("None", "None", ""),
])
def test_compute_assay(thc, cbd, expected):
    assert sort_json.compute_assay(thc, cbd) == expected


def test_section_map():
    assert sort_json.section_map("מיצוי") == "שמנים"
    assert sort_json.section_map("גליליות") == "תפרחות"


def test_treatment_group():
    assert sort_json.treatment_group("תפרחת Indica T20 C4") == "I"
    assert sort_json.treatment_group("no group") is None
    assert sort_json.treatment_group(None) is None

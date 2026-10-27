#!/opt/alt/python38/bin/python3
# -*- coding: utf-8 -*-
"""Build a sorted, grouped product menu (JSON) from a products ODS sheet,
an items CSV and an optional weighting rules JSON.

All file names are resolved inside the ``data`` folder of the current
working directory. Error messages contain "Please try again" because
store_items.php looks for that phrase to report a bad request.
"""
import argparse
import io
import json
import os
import re
import sys
from typing import Dict, List, Optional

import pandas as pd
from bidi.algorithm import get_display
from pandas.errors import EmptyDataError

# Weight that removes an item/group from the output entirely.
REMOVE_WEIGHT = -99999

NAME_COL = "ItemNameHebrew"
BRAND_COL = "Brand hebrew name"

REQUIRED_KEYS = ["ItemCode", "ItemPrice", "TreatmentGroup", "DoseFamily", "Type", "ItemName"]
OPTIONAL_KEYS = ["HebrewName", "HebrewBrand"]

TREATMENT_GROUP_RE = re.compile(r"[BISN]\w+")
TREATMENT_GROUP_FULL_RE = re.compile(r"[BISN]\w+(?:-\w+)*")
DOSE_RE = re.compile(r"T[0-9]+\sC[0-9]+")

SECTION_NAMES = {
    "מחסנית למשאף": "משאף",
    "מיצוי": "שמנים",
    "תפרחת": "תפרחות",
    "פרחים בתפזורת": "תפרחות",
    "תפרחת/גליליות": "תפרחות",
    "גליליות": "תפרחות",
}

# Keys moved to the end of every output item, in this order (after "BmCode").
OUTPUT_TAIL_KEYS = ["CBD_Percent", "ItemCode", "Brand", "ItemNameHebrew", "DisplayText", "Assay",
                    "ItemPrice", "THC_Percent", "TreatmentGroup", "DoseFamily", "Type"]
OUTPUT_DROPPED_KEYS = ["CBD", "THC"]


class SortJsonError(Exception):
    """A user-facing error: bad arguments, files or rules."""


def nan_to_none(frame: pd.DataFrame) -> pd.DataFrame:
    """Replace every NaN/NA with None. Columns without missing values keep their dtype."""
    frame = frame.copy()
    for column in frame.columns:
        missing = frame[column].isnull()
        if missing.any():
            frame[column] = frame[column].astype(object).where(~missing, None)
    return frame


def treatment_group(text) -> Optional[str]:
    """First letter of the treatment group in ``text`` (e.g. "Indica" -> "I")."""
    if not isinstance(text, str):
        return None
    match = TREATMENT_GROUP_RE.search(text)
    return match.group(0)[0] if match else None


def section_map(name: str) -> str:
    return SECTION_NAMES.get(name, get_display(name))


def order_string(sequence):
    if isinstance(sequence, str) and any("֐" <= c <= "״" for c in sequence):
        return get_display(get_display(''.join(sequence.split('‎')), base_dir='L'), base_dir='R')
    return sequence


def compute_assay(thc: str, cbd: str) -> str:
    return "-".join(value for value in (thc, cbd) if value != 'None')


def write_to_items(df: pd.DataFrame, items: pd.DataFrame, item_code: int, item_name: int,
                   treatment_group_col: int, heb_name: Optional[int] = None,
                   heb_brand: Optional[int] = None) -> pd.DataFrame:
    """Fill in missing names, brands and treatment groups in ``items`` from the
    products sheet ``df``, adding a row for every product not yet listed.

    Column arguments are 0-based positions in ``df``.
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df must be a DataFrame")
    if not isinstance(items, pd.DataFrame):
        raise ValueError("items must be a DataFrame")

    code_col = items.columns[0]
    if "TreatmentGroup" not in items.columns:
        items["TreatmentGroup"] = None

    for _, row in df.iterrows():
        code = row.iloc[item_code]
        group = treatment_group(row.iloc[treatment_group_col])

        if heb_name is None or heb_brand is None or pd.isnull(row.iloc[heb_name]) or pd.isnull(row.iloc[heb_brand]):
            # No Hebrew name: use the English one, marked with "*" as auto-generated.
            words = row.iloc[item_name].split()
            name = "*" + " ".join(words[1:])
            brand = words[0]
        else:
            name = row.iloc[heb_name]
            brand = row.iloc[heb_brand]

        matches = items[code_col] == code
        if not matches.any():
            new_row = pd.DataFrame([{code_col: code, NAME_COL: name, BRAND_COL: brand, "TreatmentGroup": group}])
            items = pd.concat([items, new_row], ignore_index=True)
            continue

        for index, item in items.loc[matches].iterrows():
            if pd.isnull(item["TreatmentGroup"]):
                items.loc[index, "TreatmentGroup"] = group

            old_name, old_brand = item[NAME_COL], item[BRAND_COL]
            missing = pd.isnull(old_name) or pd.isnull(old_brand)
            auto_generated = not missing and str(old_name).startswith("*")
            if missing or auto_generated or old_name == "unknown":
                items.loc[index, NAME_COL] = name
            if missing or auto_generated or old_brand == "unknown":
                items.loc[index, BRAND_COL] = brand

    return items


def build_empty_sort_rules(json_info: pd.DataFrame) -> dict:
    rules = {"Expressions": {}}
    for column in json_info.columns:
        rules[column] = {}
    return rules


def compute_bool_final(logical_list: list, bool_val_list: list) -> bool:
    """Combine operands with "&", "|" and prefix "!" operators, left to right."""
    n = len(logical_list)
    i = 0
    while i < n:
        if logical_list[i] == '!':
            logical_list.pop(i)
            n -= 1
            bool_val_list[i] = not bool_val_list[i]
            if i < n and logical_list[i] == '!':
                i -= 1
        i += 1

    result = bool_val_list[0]
    for i, operator in enumerate(logical_list):
        if operator == "&":
            result = result and bool_val_list[i + 1]
        elif operator == "|":
            result = result or bool_val_list[i + 1]
    return result


def evaluate_python_cond(expression: str, val: dict) -> bool:
    """Evaluate a rule expression such as ``(THC_Percent>20)|!(Brand='X')`` against an item."""
    if not any(sign in expression for sign in "&|!=<>"):
        raise SortJsonError("Not a valid expression: " + expression + ". Please try again.")

    ex = expression
    i = 0
    begin_index = 0
    parenthesis = False
    logical_list = []
    bool_val_list = []
    while i < len(ex):
        if ex[i] == "(":
            parenthesis = True
            begin_index = i
            depth = 1
            for j in range(i + 1, len(ex)):
                if ex[j] == ")":
                    depth -= 1
                elif ex[j] == "(":
                    depth += 1
                if depth == 0:
                    i = j
                    break
            bool_val_list.append(evaluate_python_cond(ex[begin_index + 1:j], val))
        elif ex[i] in "&|!":
            parenthesis = False
            logical_list.append(ex[i])
            begin_index = i + 1

        if not parenthesis:
            end = begin_index
            while end < len(ex) and ex[end] not in "&|":
                end += 1
            operand = ex[begin_index:end]
            if "(" not in operand and ")" not in operand and i + 1 == end:
                bool_val_list.append(bool_comp(operand, val))

        i += 1
    return compute_bool_final(logical_list=logical_list, bool_val_list=bool_val_list)


# Checked in this order, so two-character operators win over their prefixes.
COMPARISONS = [
    (">=", lambda a, b: a >= b),
    ("<=", lambda a, b: a <= b),
    ("<>", lambda a, b: a != b),
    ("=", lambda a, b: a == b),
    (">", lambda a, b: a > b),
    ("<", lambda a, b: a < b),
]


def bool_comp(exp: str, val: dict) -> bool:
    """Evaluate a single comparison such as ``ItemPrice>=100`` or ``Brand='X'``.

    The right-hand side is converted to the type of the item's value.
    """
    for sign, compare in COMPARISONS:
        if sign in exp:
            key, value = exp.split(sign)
            key = key.strip()
            value = value.strip().strip('\'')
            if key not in val:
                raise SortJsonError("There is no key that is " + key + ". Please try again.")
            try:
                return compare(val[key], type(val[key])(value))
            except ValueError:
                raise SortJsonError("There are conflicting types in " + exp + ". Please try again.")
            except TypeError:
                return False
    raise SortJsonError("There is no understandable logical sign in " + exp + ". Please try again.")


def item_weight(item: dict, rules: dict) -> Optional[int]:
    """Total weight of an item, or None if a rule removes it."""
    weight = 0
    for expression, expression_weight in rules.get("Expressions", {}).items():
        if evaluate_python_cond(expression, item):
            if expression_weight == REMOVE_WEIGHT:
                return None
            weight += expression_weight

    for key, value in item.items():
        try:
            key_weight = rules[key][str(value)]
        except KeyError:
            key_weight = 1
        if key_weight == REMOVE_WEIGHT:
            return None
        weight += key_weight
    return weight


def format_output_item(item: dict) -> dict:
    """Drop raw THC/CBD and put the menu fields last, in a fixed order."""
    tail = set(OUTPUT_TAIL_KEYS) | set(OUTPUT_DROPPED_KEYS)
    result = {key: value for key, value in item.items() if key not in tail}
    result["BmCode"] = None
    for key in OUTPUT_TAIL_KEYS:
        result[key] = item[key]
    return result


def sort_by_weight(items: List[dict], weights: dict) -> List[dict]:
    """Weigh items by the rules, drop removed ones and sort heaviest first."""
    if not isinstance(items, list):
        raise ValueError("items should be a list of dictionaries")
    if not isinstance(weights, dict):
        raise ValueError("weights should be a dictionary")

    kept = []
    for item in items:
        weight = item_weight(item, weights)
        if weight is not None:
            item['weight'] = weight
            kept.append(item)

    kept.sort(key=lambda d: d["weight"], reverse=True)
    return [format_output_item(item) for item in kept]


def group_weight(rules: dict, column: str, value) -> int:
    try:
        return rules[column][value]
    except KeyError:
        return 1


def build_menu(json_info: pd.DataFrame, rules: dict) -> list:
    """Group items by Type, then DoseFamily, and sort every level by weight."""
    menu = []
    for type_name, type_rows in json_info.groupby(by="Type"):
        type_weight = group_weight(rules, "Type", type_name)
        if type_weight == REMOVE_WEIGHT:
            continue

        dose_groups = []
        for dose_family, dose_rows in type_rows.groupby(by="DoseFamily"):
            dose_weight = group_weight(rules, "DoseFamily", dose_family)
            if dose_weight == REMOVE_WEIGHT:
                continue
            items = sort_by_weight(dose_rows.to_dict(orient="records"), rules)
            if items:
                dose_groups.append({"weight": dose_weight, "DoseFamily": dose_family, "Items": items})

        if dose_groups:
            dose_groups.sort(key=lambda d: d["weight"], reverse=True)
            menu.append({"weight": type_weight, "Type": type_name, "Items": dose_groups})

    menu.sort(key=lambda d: d["weight"], reverse=True)
    return menu


def read_items(path: str) -> pd.DataFrame:
    # The web UI stores the CSV with a blank line after every row.
    with open(path, encoding='utf-8') as f:
        content = f.read().replace(",,,,,,,,", "").replace("\n\n", "\n")
    try:
        return pd.read_csv(io.StringIO(content))
    except EmptyDataError:
        raise SortJsonError("The file " + path + " is empty. Please try again.")


def write_items(path: str, items: pd.DataFrame) -> None:
    content = items.to_csv(index=False).replace("\n", "\n\n")
    with open(path, "w", encoding='utf-8') as f:
        f.write(content)


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    text_columns = df.select_dtypes(include=['object', 'string']).columns
    df = nan_to_none(df)
    for column in text_columns:
        df[column] = [order_string(value) for value in df[column]]
        df[column] = [value.replace("‎", "") if isinstance(value, str) else value for value in df[column]]
    return df


def build_products_frame(df: pd.DataFrame, columns: Dict[str, int]) -> pd.DataFrame:
    """Extract DoseFamily, THC/CBD percent, Type, ItemCode and ItemPrice per product."""
    def column(key):
        return df[df.columns[columns[key] - 1]]

    products = pd.DataFrame()
    if columns['DoseFamily'] == columns["TreatmentGroup"] == columns["Type"]:
        # One description column holds everything, e.g. "תפרחת Indica T20 C4".
        descriptions = column("Type").tolist()
        doses = [DOSE_RE.findall(text) for text in descriptions]
        products['DoseFamily'] = ["/".join(found[0].split()) if found else None for found in doses]
        products['CBD_Percent'] = [int(dose.split('/')[1].replace("C", "")) if dose is not None else None
                                   for dose in products["DoseFamily"]]
        products['THC_Percent'] = [int(dose.split('/')[0].replace("T", "")) if dose is not None else None
                                   for dose in products["DoseFamily"]]
        products['Type'] = [section_map(
            text.replace("".join(TREATMENT_GROUP_FULL_RE.findall(text)), "")
                .replace("".join(DOSE_RE.findall(text)), "").strip())
            for text in descriptions]
    else:
        doses = column("DoseFamily").tolist()
        products['CBD_Percent'] = [int(dose.split()[1].replace("C", "")) for dose in doses]
        products['THC_Percent'] = [int(dose.split()[0].replace("T", "")) for dose in doses]
        products['DoseFamily'] = ["/".join(dose.split()) for dose in doses]
        products['Type'] = [section_map(text) for text in column("Type")]

    products["ItemCode"] = column("ItemCode")
    products["ItemPrice"] = column("ItemPrice")
    return products


def strip_auto_marker(value):
    return value[1:] if value is not None and value.startswith("*") else value


def load_rules(path: str, json_info: pd.DataFrame, create: bool) -> dict:
    if os.path.exists(path):
        with open(path, encoding='utf8') as f:
            return json.load(f)
    rules = build_empty_sort_rules(json_info)
    if create:
        with open(path, "w", encoding='utf8') as f:
            json.dump(rules, f, indent=3, ensure_ascii=False)
    return rules


def run(products: pd.DataFrame, items_file: str, rules_file: str, result_file: str,
        columns: Dict[str, int], create_rules: bool = False) -> list:
    """Update the items file from the products sheet and write the sorted menu."""
    df = clean_products(products)
    items = nan_to_none(read_items(items_file))

    heb_name = heb_brand = None
    if "HebrewName" in columns and "HebrewBrand" in columns:
        heb_name, heb_brand = columns["HebrewName"] - 1, columns["HebrewBrand"] - 1
    items = write_to_items(df, items, columns["ItemCode"] - 1, columns["ItemName"] - 1,
                           columns["TreatmentGroup"] - 1, heb_name, heb_brand)
    write_items(items_file, items)

    items = nan_to_none(items)
    items.rename(columns={BRAND_COL: "Brand"}, inplace=True)
    name_col = items.columns[1]
    items["DisplayText"] = [strip_auto_marker(name) for name in items[name_col]]
    items[name_col] = [strip_auto_marker(name) for name in items[name_col]]
    items["Assay"] = [compute_assay(str(thc), str(cbd)) for thc, cbd in zip(items["THC"], items["CBD"])]

    # Ignore item rows without a code; a product appears only once in the menu.
    items = items[items["ItemCode"].notnull() & (items["ItemCode"] != 'None')].copy()
    items["ItemCode"] = items.pop("ItemCode").astype(int)
    json_info = pd.merge(items, build_products_frame(df, columns), on="ItemCode").drop_duplicates(subset=['ItemCode'])
    json_info = nan_to_none(json_info)

    menu = build_menu(json_info, load_rules(rules_file, json_info, create_rules))
    with open(result_file, "w", encoding='utf8') as f:
        json.dump(menu, f, indent=3, ensure_ascii=False)
    return menu


def parse_columns(parser: argparse.ArgumentParser, assignments: List[str]) -> Dict[str, int]:
    """Parse KEY=COLUMN arguments (1-based column numbers)."""
    columns = {}
    for assignment in assignments:
        key, _, number = assignment.partition("=")
        if key not in REQUIRED_KEYS + OPTIONAL_KEYS or not number.strip().isdigit() or int(number) < 1:
            parser.error("Wrong argument value " + repr(assignment) +
                         ". Please try again with form KEY=COLUMNNUMBER")
        columns[key] = int(number)

    missing = [key for key in REQUIRED_KEYS if key not in columns]
    if missing:
        parser.error("Missing keys: " + ", ".join(missing) + ". All the keys are " + ", ".join(REQUIRED_KEYS) +
                     " and optionally " + ", ".join(OPTIONAL_KEYS) + ". Please try again.")
    return columns


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sort json file.")
    parser.add_argument('columns', metavar='KEY=COLUMN', nargs='+',
                        help='The 1-based column of the products file for each key, e.g. ItemCode=2. '
                             'Keys: ' + ', '.join(REQUIRED_KEYS + OPTIONAL_KEYS) + '.')
    parser.add_argument('-f', metavar="ods_filename", help="Give the ods filename.", required=True)
    parser.add_argument('-i', metavar="items_filename", help="Give the items filename.", default="items.csv")
    parser.add_argument('-r', metavar="rules_filename", help="Give the rules filename.", default="rules.json")
    parser.add_argument('-s', metavar="sorted_json_file", help="Give the sorted_json filename.",
                        default="sorted_json.json")
    parser.add_argument('-n', help="Create the rules file if it doesn't exist.", action="store_true")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    columns = parse_columns(parser, args.columns)

    data_dir = os.path.join(os.getcwd(), "data")
    ods_file = os.path.join(data_dir, args.f)
    items_file = os.path.join(data_dir, args.i)

    try:
        for path in (ods_file, items_file):
            if not os.path.exists(path):
                raise SortJsonError("The file " + path + " does not exist. Please try again.")
        products = pd.read_excel(ods_file, engine="odf")
        run(products, items_file, os.path.join(data_dir, args.r), os.path.join(data_dir, args.s),
            columns, create_rules=args.n)
    except SortJsonError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

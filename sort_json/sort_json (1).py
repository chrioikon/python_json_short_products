#!/opt/alt/python38/bin/python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import os
import json
from pandas.core.frame import DataFrame
import argparse
from pandas.errors import EmptyDataError
import re
from bidi.algorithm import get_display


def write_to_items(df: DataFrame, items: DataFrame, ItemCode: int, ItemName: int, TreatmentGroup: int,
                   heb_name: int = None, heb_brand: int = None):
    if not isinstance(df, DataFrame):
        raise ValueError("df must be a Dataframe")

    if not isinstance(items, DataFrame):
        raise ValueError("items must be a Dataframe")

    for _, row in df.iterrows():

        temp = items.loc[(items[items.columns[0]] == row[ItemCode]) & (
                (items[items.columns[1]] == "unknown") | (items[items.columns[2]] == "unknown") | (
            items[items.columns[1]].str.startswith("*")) | (items[items.columns[1]].isnull()) | (
                    items[items.columns[2]].isnull()))]

        if (heb_name == None or heb_brand == None) or (row[heb_name] == None or row[heb_brand] == None):
            name = "*" + " ".join(row[ItemName].split()[1:])
            brand = row[ItemName].split()[0]
        else:
            name = row[heb_name]
            brand = row[heb_brand]
        temp2 = items.loc[(items[items.columns[0]] == row[ItemCode])]
        for index2, row2 in temp2.iterrows():
            try:
                if row2[9] == None:
                    items.loc[index2, "TreatmentGroup"] = re.findall(r'[B|I|S|N]\w+', row[TreatmentGroup])[
                        0][0] if re.findall(r'[B|I|S|N]\w+', row[TreatmentGroup]) else None
            except IndexError:
                items.loc[index2, "TreatmentGroup"] = re.findall(r'[B|I|S|N]\w+', row[TreatmentGroup])[
                    0][0] if re.findall(r'[B|I|S|N]\w+', row[TreatmentGroup]) else None
                items["TreatmentGroup"] = items["TreatmentGroup"].fillna('').where(pd.notnull(items["TreatmentGroup"]),
                                                                                   None)
        for index1, row1 in temp.iterrows():

            if row1[1] == None or row1[2] == None or row1[1] == "unknown" or row1[1][0] == "*":
                items.loc[index1, "ItemNameHebrew"] = name
            if row1[1] == None or row1[2] == None or row1[2] == "unknown" or row1[1][0] == "*":
                items.loc[index1, "Brand hebrew name"] = brand

        if len(temp) == 0 and len(items.loc[(items[items.columns[0]] == row[ItemCode])]) == 0:
            pict = {items.columns[0]: row[ItemCode],
                    items.columns[1]: name, items.columns[2]: brand,
                    "TreatmentGroup": re.findall(r'[B|I|S|N]\w+', row[TreatmentGroup])[0][0] if re.findall(
                        r'[B|I|S|N]\w+', row[TreatmentGroup]) else None}

            items = items.append(pict, ignore_index=True)
    items.to_csv(ITEMS_FILE, index=False, encoding='utf-8')
    return items


def section_map(name: str):
    if name == "מחסנית למשאף":
        return "משאף"
    elif name == "מיצוי":
        return "שמנים"
    elif name == "תפרחת":
        return "תפרחות"
    elif name == "תפרחת/גליליות":
        return "תפרחות"
    elif name == "גליליות":
        return "תפרחות"
    elif name == "פרחים בתפזורת":
        return "תפרחות"
    else:
        return get_display(name)


def build_empty_sort_rules(json_info):
    diction = {}
    diction["Expressions"] = {}
    for column in json_info.columns:
        diction[column] = dict()
    return diction


def compute_bool_final(logical_list: list, bool_val_list: list):
    N = len(logical_list)
    i = 0
    while (i < N):
        if logical_list[i] == '!':
            logical_list.pop(i)
            N -= 1
            bool_val_list[i] = not bool_val_list[i]
            if i < N and logical_list[i] == '!':
                i -= 1
        i += 1

    comp = bool_val_list[0]
    for i in range(len(logical_list)):
        if logical_list[i] == "&":
            comp = comp and bool_val_list[i + 1]
        elif logical_list[i] == "|":
            comp = comp or bool_val_list[i + 1]

    return comp


def evaluate_python_cond(expression: str, val: dict):
    if ('&' not in expression) and ('|' not in expression) and ('!' not in expression) and ('=' not in expression) and (
            '>' not in expression) and ('<' not in expression):
        print("Not a valid expression")
        exit(1)

    ex = expression

    i = 0
    begin_index = 0
    parenthesis = False
    logical_list = []
    bool_val_list = []
    while i < len(ex):
        flag = 0
        if ex[i] == "(":
            parenthesis = True
            begin_index = i
            flag += 1
            for j in range(i + 1, len(ex)):
                if ex[j] == ")":
                    flag -= 1
                elif ex[j] == "(":
                    flag += 1
                if flag == 0:
                    i = j
                    break
            bool_val_list.append(
                evaluate_python_cond(ex[begin_index + 1:j], val))
        elif ex[i] == "&" or ex[i] == "|" or ex[i] == '!':
            parenthesis = False
            logical_list.append(ex[i])
            begin_index = i + 1

        if not parenthesis:
            count = begin_index
            while count < len(ex) and (ex[count] != "&" and ex[count] != "|"):
                count += 1
            if not ("(" in ex[begin_index:count] or ")" in ex[begin_index:count]) and i + 1 == count:
                bool_val_list.append(bool_comp(ex[begin_index:count], val))

        i += 1
    return compute_bool_final(logical_list=logical_list, bool_val_list=bool_val_list)


def bool_comp(exp: str, val: dict):
    if ">=" in exp:
        key, value = exp.split(">=")
        key = key.strip()
        value = value.strip().strip('\'')
        if key in val.keys():
            try:
                return val[key] >= type(val[key])(value)
            except ValueError:
                print("There are conflicting types in",
                      exp + '.', "Please try again")
                exit(1)
            except TypeError:
                return False
        else:
            print("There is no key that is", key + ".", "Please try again.")
            exit(1)
    elif "<=" in exp:
        key, value = exp.split("<=")
        key = key.strip()
        value = value.strip().strip('\'')
        if key in val.keys():
            try:
                return val[key] <= type(val[key])(value)
            except ValueError:
                print("There are conflicting types in",
                      exp + '.', "Please try again")
                exit(1)
            except TypeError:
                return False
        else:
            print("There is no key that is", key + ".", "Please try again.")
            exit(1)
    elif "<>" in exp:
        key, value = exp.split("<>")
        key = key.strip()
        value = value.strip().strip('\'')
        if key in val.keys():
            try:
                return val[key] != type(val[key])(value)
            except ValueError:
                print("There are conflicting types in",
                      exp + '.', "Please try again")
                exit(1)
            except TypeError:
                return False
        else:
            print("There is no key that is", key + ".", "Please try again.")
            exit(1)
    elif "=" in exp:
        key, value = exp.split("=")
        key = key.strip()
        value = value.strip().strip('\'')
        if key in val.keys():

            try:
                return val[key] == type(val[key])(value)
            except ValueError:
                print("There are conflicting types in",
                      exp + '.', "Please try again")
                exit(1)
            except TypeError:
                return False
        else:
            print("There is no key that is", key + ".", "Please try again.")
            exit(1)
    elif ">" in exp:
        key, value = exp.split(">")
        key = key.strip()
        value = value.strip().strip('\'')
        if key in val.keys():
            try:
                return val[key] > type(val[key])(value)
            except ValueError:
                print("There are conflicting types in",
                      exp + '.', "Please try again")
                exit(1)
            except TypeError:
                return False
        else:
            print("There is no key that is", key + ".", "Please try again.")
            exit(1)
    elif "<" in exp:
        key, value = exp.split("<")
        key = key.strip()
        value = value.strip().strip('\'')
        if key in val.keys():
            try:
                return val[key] < type(val[key])(value)
            except ValueError:
                print("There are conflicting types in",
                      exp + '.', "Please try again")
                exit(1)
            except TypeError:
                return False
        else:
            print("There is no key that is", key + ".", "Please try again.")
            exit(1)

    else:
        print("There is no understandable logical sign in",
              exp + ".", "Please try again.")
        exit(1)


def compute_assay(thc: str, cpd: str):
    if thc != 'None' and cpd != 'None':
        return thc + '-' + cpd
    elif thc != 'None':
        return thc
    elif cpd != 'None':
        return cpd
    else:
        return ''


def order_string(sequense: str):
    if sequense != None and any("\u0590" <= c <= "\u05F4" for c in sequense):
        return get_display(get_display(''.join(sequense.split('\u200e')), base_dir='L'), base_dir='R')
    else:
        return sequense


def sort_by_weight(items: list, weights: dict):
    if not isinstance(items, list):
        raise ValueError("items should be a list of dictionaries")

    if not isinstance(weights, dict):
        raise ValueError("weights should be a dictionary")

    i = 0
    n = len(items)
    while i < n:
        items[i]['weight'] = 0
        removed_flag = False
        for key in weights['Expressions'].keys():
            if evaluate_python_cond(key, items[i]):

                items[i]['weight'] += weights['Expressions'][key]
                if weights['Expressions'][key] == -99999:
                    items.pop(i)
                    i -= 1
                    n -= 1
                    removed_flag = True
                    break

        if not removed_flag:
            for key, _ in items[i].items():

                if key != "weight":
                    try:

                        items[i]['weight'] += weights[key][str(items[i][key])]
                        if weights[key][items[i][key]] == -99999:
                            items.pop(i)
                            i -= 1
                            n -= 1
                            break
                    except KeyError:
                        items[i]['weight'] += 1

        i += 1

    items = sorted(items, key=lambda d: d["weight"], reverse=True)
    for val in items:
        val.pop("CBD")
        val.pop("THC")
        val["BmCode"] = None
        val['CBD_Percent'] = val.pop('CBD_Percent')
        val['ItemCode'] = val.pop('ItemCode')
        val['Brand'] = val.pop('Brand')
        val['ItemNameHebrew'] = val.pop('ItemNameHebrew')
        val['DisplayText'] = val.pop('DisplayText')
        val['Assay'] = val.pop('Assay')
        val['ItemPrice'] = val.pop('ItemPrice')
        val['THC_Percent'] = val.pop('THC_Percent')
        val['TreatmentGroup'] = val.pop('TreatmentGroup')
        val['DoseFamily'] = val.pop('DoseFamily')
        val['Type'] = val.pop('Type')

        # del[val['weight']]

    return items, weights


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Sort json file.")

    parser.add_argument(
        'k=cn', type=str, help='Give the columns corresponding to the key values.', nargs='+')

    parser.add_argument('-f', metavar="ods_filename",
                        help="Give the ods filename.", required=True)

    parser.add_argument('-i', metavar="items_filename",
                        help="Give the items filename.", default="items.csv")
    parser.add_argument('-r', metavar="rules_filename",
                        help="Give the rules filename.", default="rules.json")
    parser.add_argument('-s', metavar="sorted_json_file",
                        help="Give the sorted_json filename.", default="sorted_json.json")
    parser.add_argument(
        '-n', help="Create the json file if it doesn't exist.", action="store_true")

    args = parser.parse_args()

    args_list = vars(args)['k=cn']
    values = {}
    req_list = ["ItemCode", "ItemPrice", "TreatmentGroup",
                "DoseFamily", "Type", "ItemName"]

    for argum in args_list:
        if argum.split("=")[0] in ["ItemCode", "ItemPrice", "TreatmentGroup", "DoseFamily", "Type", "ItemName",
                                   "HebrewName", "HebrewBrand"]:
            a = {}
            exec(argum.split("=")[0] + "=" +
                 argum.split("=")[1], a, values)
            if not (argum.split("=")[0] in ["HebrewName", "HebrewBrand"]):
                req_list.remove(argum.split("=")[0])

        else:
            parser.error(
                "Wrong argument value. Please try again with form KEY=COLUMNNUMBER")
            exit(1)

    if len(values) < 6 or len(req_list) > 0:
        parser.error(
            "Wrong number of keys. All the keys are \"ItemCode\", \"ItemPrice\", \"TreatmentGroup\", \"DoseFamily\", \"ItemName\", \"Type\", [\"HebrewName,HebrewBrand\"].")
        exit(1)

    ods_name = vars(args)['f']
    items_name = vars(args)['i']
    ODS_FILE = os.path.join(os.getcwd(), "data", ods_name)
    ITEMS_FILE = os.path.join(os.getcwd(), "data", items_name)
    RULES_FILE = os.path.join(os.getcwd(), "data", vars(args)['r'])
    RESULT_JSON = os.path.join(os.getcwd(), "data", vars(args)['s'])

    if not os.path.exists(ODS_FILE):
        print("The file " + ODS_FILE + " does not exist.Please try again.")
        exit(1)

    if not os.path.exists(ITEMS_FILE):
        print("The file " + ITEMS_FILE + " does not exist.Please try again.")
        exit(1)

    df = pd.read_excel(ODS_FILE, engine="odf")
    with open(ITEMS_FILE, "r", encoding='utf-8') as f:
        cont = f.read()
        cont = cont.replace(",,,,,,,,", "")
        cont = cont.replace("\n\n", "\n")
    with open(ITEMS_FILE, "w", encoding='utf-8') as f:
        f.write(cont)

    try:
        items = pd.read_csv(ITEMS_FILE)

    except EmptyDataError:
        items = pd.DataFrame()

    dd = df.select_dtypes('object')
    df = df.fillna('').where(pd.notnull(df), None)
    for column in dd.columns:
        df[column] = [order_string(it) for it in df[column].to_list()]
        df[column] = df[column].str.replace("\u200e", "")

    df = df.fillna('').where(pd.notnull(df), None)
    items = items.fillna('').where(pd.notnull(items), None)
    try:
        items = write_to_items(
            df, items, values["ItemCode"] - 1, values["ItemName"] - 1, values["TreatmentGroup"] - 1,
                       values["HebrewName"] - 1, values["HebrewBrand"] - 1)
    except KeyError:
        items = write_to_items(
            df, items, values["ItemCode"] - 1, values["ItemName"] - 1, TreatmentGroup=values["TreatmentGroup"] - 1)
    # print (items)
    with open(ITEMS_FILE, "r", encoding='utf-8') as f:
        cont = f.read()
        cont = cont.replace("\n", "\n\n")
    with open(ITEMS_FILE, "w", encoding='utf-8') as f:
        f.write(cont)
    items = items.fillna('').where(pd.notnull(items), None)
    df1 = DataFrame()

    if values['DoseFamily'] == values["TreatmentGroup"] == values["Type"]:
        df1['DoseFamily'] = ["/".join(re.findall(r'T[0-9]+\sC[0-9]+', it)[0].split()) if re.findall(
            r'T[0-9]+\sC[0-9]+', it) else None for it in df[df.columns[values["DoseFamily"] - 1]].to_list()]
        df1['CBD_Percent'] = [int(it.split('/')[1].replace("C", "")) if it != None else None
                              for it in df1["DoseFamily"].to_list()]
        df1['THC_Percent'] = [int(it.split('/')[0].replace("T", "")) if it != None else None
                              for it in df1["DoseFamily"].to_list()]
        df1['Type'] = [section_map(it.replace("".join(re.findall(r'[B|I|S|N]\w+(?:-\w+)*', it)), "").replace("".join(
            re.findall(r'T[0-9]+\sC[0-9]+', it)), "").strip()) for it in df[df.columns[values["Type"] - 1]].tolist()]
        df1["ItemCode"] = df[df.columns[values["ItemCode"] - 1]]
        # df1["TreatmentGroup"] = [re.findall(r'[B|I|S|N]\w+', it)[0][0] if re.findall(
        #     r'[B|I|S|N]\w+', it) else None for it in df[df.columns[values["TreatmentGroup"]-1]].to_list()]

        df1["ItemPrice"] = df[df.columns[values["ItemPrice"] - 1]]

    else:

        df1['CBD_Percent'] = [int(it.split()[1].replace("C", ""))
                              for it in df[df.columns[values["DoseFamily"] - 1]].to_list()]
        df1['THC_Percent'] = [int(it.split()[0].replace("T", ""))
                              for it in df[df.columns[values["DoseFamily"] - 1]].to_list()]
        df1['DoseFamily'] = ["/".join(it.split())
                             for it in df[df.columns[values["DoseFamily"] - 1]].to_list()]
        df1['Type'] = [section_map(it)
                       for it in df[df.columns[values["Type"] - 1]].to_list()]

        df1["ItemCode"] = df[df.columns[values["ItemCode"] - 1]]
        df1["ItemPrice"] = df[df.columns[values["ItemPrice"] - 1]]

    items.rename(columns={"Brand hebrew name": "Brand"}, inplace=True)

    items["DisplayText"] = [it[1:] if (
            it != None and it[0] == "*") else it for it in items[items.columns[1]].to_list()]

    items[items.columns[1]] = [it[1:] if (
            it != None and it[0] == "*") else it for it in items[items.columns[1]].to_list()]
    items["Assay"] = [compute_assay(str(items["THC"].to_list()[i]), str(
        items["CBD"].to_list()[i])) for i in range(len(items["THC"]))]

    items = pd.merge(items, items["ItemCode"].replace(to_replace='None', value=np.nan).dropna(),
                     how="right", left_index=True, right_index=True)
    del items["ItemCode_y"]
    items["ItemCode"] = items["ItemCode_x"].astype(int)
    del items["ItemCode_x"]
    json_info = pd.merge(items, df1, on="ItemCode").drop_duplicates(subset=['ItemCode'])
    json_info = json_info.fillna('').where(pd.notnull(json_info), None)

    if not os.path.exists(RULES_FILE) and vars(args)['n']:
        diction = build_empty_sort_rules(json_info)
        with open(RULES_FILE, "w", encoding='utf8') as f:
            json.dump(diction, f, indent=3, ensure_ascii=False)

    elif os.path.exists(RULES_FILE):
        with open(RULES_FILE, encoding='utf8') as f:
            diction = json.load(f)

    else:
        diction = build_empty_sort_rules(json_info)

    json_list = []

    for group in json_info.groupby(by="Type"):
        type_dict = {}
        try:
            type_dict['weight'] = diction["Type"][group[0]]
        except KeyError:
            type_dict['weight'] = 1
        if type_dict['weight'] != -99999:
            json_list.append(type_dict)
        else:
            continue
        type_dict["Type"] = group[0]
        type_dict["Items"] = []

        for group2 in group[1].groupby(by="DoseFamily"):

            dose_fam_dict = {}

            try:
                dose_fam_dict['weight'] = diction["DoseFamily"][group2[0]]
            except KeyError:
                dose_fam_dict['weight'] = 1
            if dose_fam_dict['weight'] != -99999:
                type_dict["Items"].append(dose_fam_dict)
            else:
                continue

            dose_fam_dict["DoseFamily"] = group2[0]

            dicts = group2[1].to_dict(orient="records")

            dicts, diction = sort_by_weight(dicts, diction)
            dose_fam_dict["Items"] = dicts
            if dose_fam_dict["Items"] == []:
                type_dict["Items"].remove(dose_fam_dict)
        if type_dict["Items"] == []:
            json_list.remove(type_dict)
        type_dict["Items"] = sorted(
            type_dict["Items"], key=lambda d: d["weight"], reverse=True)

        # for it in type_dict["Items"]:
        # del[it["weight"]]

    json_list = sorted(json_list, key=lambda d: d["weight"], reverse=True)

    # for it in json_list:
    #     del[it["weight"]]

    with open(RESULT_JSON, "w", encoding='utf8') as f:
        json.dump(json_list, f, indent=3, ensure_ascii=False)

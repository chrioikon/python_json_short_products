# Python JSON Sorter

This is a Python script that reads JSON files containing product information and sorts them by various criteria.

## Requirements

- Python 3.8 or higher
- pandas
- bidi
- argparse

## Usage

- Place your JSON files in the `data` folder.
- Run the script with the following command:

```bash
python3 main.py -f ods_filename -i items_filename -r rules_filename -s sorted_json_file -n k=cn
```

- The script will create a `results` folder with the sorted JSON files.

## Features

- The script can handle different types of products, such as flowers, oils, inhalers, etc.
- The script can sort the products by various criteria, such as price, popularity, rating, etc.
- The script can use different rules and weights for sorting the products, which can be specified in a JSON file.
- The script can create a JSON file with the rules and weights if it does not exist.

## Examples

Here are some examples of the command line arguments:

```bash
python3 main.py -f products.ods -i items.csv -r rules.json -s sorted.json -n ItemCode=1 ItemName=2 TreatmentGroup=3 DoseFamily=4 Type=5 HebrewName=6 HebrewBrand=7
```

This will read the products.ods file and the items.csv file, use the rules.json file for sorting, and create a sorted.json file with the sorted products. It will also create a rules.json file if it does not exist. It will use the column numbers 1 to 7 for the keys ItemCode, ItemName, TreatmentGroup, DoseFamily, Type, HebrewName, and HebrewBrand.

```bash
python3 main.py -f products.ods -i items.csv -s sorted.json ItemCode=1 ItemName=2 TreatmentGroup=3 DoseFamily=4 Type=5
```

This will read the products.ods file and the items.csv file, use the default rules for sorting, and create a sorted.json file with the sorted products. It will use the column numbers 1 to 5 for the keys ItemCode, ItemName, TreatmentGroup, DoseFamily, and Type.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

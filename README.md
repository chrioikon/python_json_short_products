# python_json_short_products

This is a sort json programm with an html and php files that sort a JSON Object according to parameters given by the user in rules.json

The rules.json file should have the form
{"Expresions":{"expresion":weight}}

Usage of this script is:

./sort_json.py ItemCode=2 ItemPrice=9 TreatmentGroup=1  DoseFamily=1 Type=1 ItemName=3 HebrewName=4 HebrewBrand=5 -f odsfilename.ods -i itemsfile.csv -r rules.json -s output.json

The first nargs are used to define wich columns of the ods correspond to the key values they represend.

-f is for the filename of the ods we will be using. It's required.

-i is for filename of the items we will be using. Also required.

-r is for filename of the rules json file. Default is rules.json.

-s is for output filename. Default is sorted_json.json.

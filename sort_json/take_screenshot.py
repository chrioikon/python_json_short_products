#!/opt/alt/python38/bin/python3
# -*- coding: utf-8 -*
import argparse
from playwright.sync_api import sync_playwright
from PIL import Image
import re

parser = argparse.ArgumentParser(description="Take url and return png and pdf")

parser.add_argument("-u",help="Input the URL to take screenshot.",required=True)
parser.add_argument("-o",help="Output file.",required=True)
args = parser.parse_args()
i= 0
while(i<10):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(vars(args)["u"])
            page.screenshot(path=vars(args)["o"],full_page=True)
        image1 = Image.open(vars(args)["o"])
        im1 = image1.convert('RGB')
        im1.save(re.sub(r'\.(png|jpg)+$',".pdf",vars(args)["o"]))
        break
    except Exception as e:
        print(e)
        i+=1
           
print("DONE")
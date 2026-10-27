#!/opt/alt/python38/bin/python3
# -*- coding: utf-8 -*-
"""Save a full-page screenshot of a URL, plus a PDF of it next to the image."""
import argparse
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

ATTEMPTS = 10


def take_screenshot(url: str, output: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url)
            page.screenshot(path=output, full_page=True)
        finally:
            browser.close()
    with Image.open(output) as image:
        image.convert('RGB').save(os.path.splitext(output)[0] + ".pdf")


def main() -> int:
    parser = argparse.ArgumentParser(description="Take url and return png and pdf")
    parser.add_argument("-u", help="Input the URL to take screenshot.", required=True)
    parser.add_argument("-o", help="Output file.", required=True)
    args = parser.parse_args()

    for _ in range(ATTEMPTS):
        try:
            take_screenshot(args.u, args.o)
            print("DONE")
            return 0
        except Exception as error:
            print(error)
    print("FAILED after", ATTEMPTS, "attempts")
    return 1


if __name__ == "__main__":
    sys.exit(main())

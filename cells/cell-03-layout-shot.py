#!/usr/bin/env python3
"""Скриншот layout-скелета через playwright (1344x768)."""
from playwright.sync_api import sync_playwright

SRC = "file:///home/z/my-project/scripts/layout_schematic.html"
OUT = "/home/z/my-project/download/reve-style-picture/step1_layout_skeleton.png"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1344, "height": 768})
    page.goto(SRC)
    page.wait_for_timeout(400)
    page.screenshot(path=OUT)
    b.close()
print("saved:", OUT)

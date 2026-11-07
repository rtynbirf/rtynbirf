#!/usr/bin/env python3
"""Склейка layout-скелета и финального рендера в одну вертикальную картинку."""
from PIL import Image, ImageDraw, ImageFont

BASE = "/home/z/my-project/download/reve-style-picture"
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)

skel = Image.open(f"{BASE}/step1_layout_skeleton.png").convert("RGB")
rend = Image.open(f"{BASE}/step2_final_render.png").convert("RGB")

GAP, CAP = 16, 56
W = 1344
H = CAP + skel.height + GAP + CAP + rend.height
canvas = Image.new("RGB", (W, H), (5, 8, 15))
d = ImageDraw.Draw(canvas)

d.text((20, 12), "ШАГ 1 — LAYOUT (структура сцены)", font=FONT, fill=(62, 230, 216))
canvas.paste(skel, (0, CAP))
y2 = CAP + skel.height + GAP
d.text((20, y2 + 8), "ШАГ 2 — РЕНДЕР по layout (фотореализм)", font=FONT, fill=(255, 179, 92))
canvas.paste(rend, (0, y2 + CAP))

canvas.save(f"{BASE}/pipeline_layout_then_render.png")
print("saved:", f"{BASE}/pipeline_layout_then_render.png", canvas.size)

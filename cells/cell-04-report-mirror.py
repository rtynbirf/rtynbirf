#!/usr/bin/env python3
"""Извлечение полного текста отчёта 'Training Reve 2.0 at scale' из HTML в Markdown."""
import re
from bs4 import BeautifulSoup, NavigableString, Tag

SRC = "/home/z/my-project/download/reve-training-infra/page_raw.html"
OUT = "/home/z/my-project/download/reve-training-infra/report_full.md"

html = open(SRC, encoding="utf-8", errors="replace").read()
soup = BeautifulSoup(html, "html.parser")

# ---------- helpers ----------

def inline_md(node):
    """Рекурсивно превращаем инлайн-содержимое узла в Markdown-строку."""
    if node is None:
        return ""
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    if not isinstance(node, Tag):
        return ""
    name = node.name
    if name in ("sup", "sub"):
        inner = "".join(inline_md(c) for c in node.children)
        marker = node.get("data-marker") or ""
        return marker + inner if marker else inner
    if name == "a":
        href = node.get("href", "")
        txt = "".join(inline_md(c) for c in node.children)
        if href.startswith("#"):
            return txt
        return f"[{txt}]({href})" if txt else href
    if name in ("strong", "b"):
        return f"**{''.join(inline_md(c) for c in node.children).strip()}**"
    if name in ("em", "i"):
        return f"*{''.join(inline_md(c) for c in node.children).strip()}*"
    if name == "code":
        return f"`{node.get_text()}`"
    if name in ("br",):
        return " "
    if name == "math":  # MathML — плоский текст
        return " " + re.sub(r"\s+", " ", node.get_text(" ", strip=True)) + " "
    if name == "span" and "katex" in " ".join(node.get("class", [])):
        return " " + re.sub(r"\s+", " ", node.get_text(" ", strip=True)) + " "
    return "".join(inline_md(c) for c in node.children)


def block_md(node, depth=0):
    """Блочные элементы -> Markdown."""
    if isinstance(node, NavigableString):
        s = re.sub(r"\s+", " ", str(node)).strip()
        return s + "\n\n" if s else ""
    if not isinstance(node, Tag):
        return ""
    name = node.name
    if name in ("h1", "h2", "h3", "h4"):
        level = int(name[1])
        return f"{'#'*(level+0)} {inline_md(node).strip()}\n\n"
    if name == "p":
        return inline_md(node).strip() + "\n\n"
    if name in ("ul", "ol"):
        out = []
        idx = 1
        for li in node.find_all("li", recursive=False):
            marker = f"{idx}." if name == "ol" else "-"
            out.append(f"{'  '*depth}{marker} {inline_md(li).strip()}")
            idx += 1
        return "\n".join(out) + "\n\n"
    if name == "pre":
        code = node.find("code")
        text = (code or node).get_text()
        lang = ""
        m = re.search(r"language-(\w+)", " ".join((code or node).get("class", []) or []))
        if m:
            lang = m.group(1)
        return f"```{lang}\n{text}\n```\n\n"
    if name == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = [inline_md(c).strip().replace("\n", " ") for c in tr.find_all(["th", "td"])]
            rows.append("| " + " | ".join(cells) + " |")
        if rows:
            ncols = rows[0].count("|") - 1
            rows.insert(1, "|" + " --- |" * max(ncols - 1, 0))
        return "\n".join(rows) + "\n\n"
    if name == "figure":
        cap = node.find("figcaption")
        cap_md = ("**" + inline_md(cap).strip() + "**\n\n") if cap else ""
        inner = "".join(block_md(c) for c in node.children if not (isinstance(c, Tag) and c.name == "figcaption"))
        desc = node.get_text(" ", strip=True)
        return cap_md + f"> [Схема/рисунок в оригинале — воспроизведён в HTML/PDF]\n> {desc[:400]}\n\n" if not inner.strip() else cap_md + inner
    if name in ("section", "div", "article", "main", "header", "footer", "nav", "aside"):
        return "".join(block_md(c, depth + 1) for c in node.children)
    # прочие блочные теги — инлайн
    txt = inline_md(node).strip()
    return txt + "\n\n" if txt else ""


article = soup.find("article")
meta = {
    "title": soup.title.get_text(strip=True) if soup.title else "",
    "desc": "",
    "url": "https://app.reve.com/training-infra",
}
md = soup.new_tag("meta")
d = soup.find("meta", attrs={"name": "description"})
if d:
    meta["desc"] = d.get("content", "")

header = f"""# {meta['title']}

> **Источник:** {meta['url']}
> **Описание (meta):** {meta['desc']}
> **Команда:** Reve Research Team
> **Дата скачивания:** 2026-11-08
> **Формат:** извлечено из HTML страницы; формулы — плоский текст (KaTeX), схемы — текстовое описание.

---

"""

body = block_md(article)
# почистить лишние пустые строки
body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
open(OUT, "w", encoding="utf-8").write(header + body)
print("WROTE", OUT, len(header + body), "chars")
print("---- HEAD ----")
print((header + body)[:600])

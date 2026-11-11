"""Wrap taiwan-400.html (the claude.ai artifact body) into a standalone index.html for GitHub Pages.

Run after editing taiwan-400.html:  python build_pages.py
"""
from pathlib import Path

here = Path(__file__).parent
body = (here / "taiwan-400.html").read_text(encoding="utf-8")

head_end = body.index("</style>") + len("</style>")
head, rest = body[:head_end], body[head_end:]

page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="台灣四百年：1600–2026 年的統治者、國家掌握範圍與族群人口動畫。Taiwan: Four Centuries — an animated, bilingual history of rulers, state control and population.">
{head}
</head>
<body>
{rest.strip()}
</body>
</html>
"""
(here / "index.html").write_text(page, encoding="utf-8")
print("wrote index.html")

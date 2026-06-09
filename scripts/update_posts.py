#!/usr/bin/env python3
"""Fetch latest published posts from r34p3r-dhan.in, render an animated square
SVG "card" per post into assets/cards/, and inject a 3-per-row card grid into
README.md between the BLOG-POST-LIST markers. Stdlib only."""
import json
import re
import sys
import shutil
import urllib.request
from urllib.parse import quote
from pathlib import Path

FEED = "https://r34p3r-dhan.in/posts.json"
POST_URL = "https://r34p3r-dhan.in/posts/post.html?file="
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CARD_DIR = ROOT / "assets" / "cards"
CARD_RAW = "https://raw.githubusercontent.com/Reaper-Dhan/Reaper-Dhan/main/assets/cards/"
START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"
MAX_POSTS = 6
PER_ROW = 3

TYPE_COLOR = {"research": "#00FF99", "writeup": "#00d4ff", "notes": "#f0c674"}


def fetch_posts():
    req = urllib.request.Request(FEED, headers={"User-Agent": "reaper-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def xesc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def slugify(name):
    name = re.sub(r"\.md$", "", name or "post")
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").lower() or "post"


def wrap(text, max_chars, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and (cur != lines[-1] or len(text.split()) > sum(len(l.split()) for l in lines)):
        lines[-1] = lines[-1][:max_chars - 1].rstrip() + "…"
    return lines[:max_lines]


def make_card_svg(post):
    title = post["title"].strip()
    ptype = (post.get("type") or "").lower()
    accent = TYPE_COLOR.get(ptype, "#8b949e")
    date = post.get("date", "")
    rt = f"{post['read_time']} min" if post.get("read_time") else ""
    tags = post.get("tags", [])[:3]
    P = 1137  # ~ perimeter of the rounded border rect

    title_lines = wrap(title, 20, 4)
    tl_svg = "".join(
        f'<text x="22" y="{104 + i * 25}" font-size="17" font-weight="600" '
        f'fill="#e9eef3">{xesc(line)}</text>'
        for i, line in enumerate(title_lines)
    )
    type_w = len(ptype) * 8 + 24
    meta = " · ".join(x for x in [date, rt] if x)
    tags_svg = ""
    if tags:
        tx = 22
        chips = []
        for t in tags:
            label = f"#{t}"
            w = len(label) * 7 + 16
            chips.append(
                f'<g transform="translate({tx} 250)">'
                f'<rect width="{w}" height="20" rx="10" fill="#161f2e" stroke="{accent}" stroke-opacity="0.4"/>'
                f'<text x="{w/2:.0f}" y="14" font-size="11" fill="{accent}" text-anchor="middle">{xesc(label)}</text>'
                f'</g>'
            )
            tx += w + 8
        tags_svg = "".join(chips)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300" font-family="'Fira Code','Consolas',monospace">
  <defs>
    <linearGradient id="n" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{accent}"/><stop offset="100%" stop-color="#00d4ff"/>
    </linearGradient>
    <radialGradient id="g" cx="30%" cy="22%" r="70%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="card"><rect x="4" y="4" width="292" height="292" rx="18"/></clipPath>
  </defs>
  <rect x="4" y="4" width="292" height="292" rx="18" fill="#0b1320" stroke="#1d3a52" stroke-width="1.5"/>
  <rect x="4" y="4" width="292" height="292" rx="18" fill="url(#g)"/>
  <!-- scanline -->
  <g clip-path="url(#card)">
    <rect x="4" width="292" height="2" y="10" fill="{accent}" opacity="0.25">
      <animate attributeName="y" values="6;290;6" dur="4.5s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1" keyTimes="0;0.5;1"/>
    </rect>
  </g>
  <!-- traveling neon border light -->
  <rect x="4" y="4" width="292" height="292" rx="18" fill="none" stroke="url(#n)" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="170 {P-170}">
    <animate attributeName="stroke-dashoffset" values="0;-{P}" dur="4s" repeatCount="indefinite"/>
  </rect>
  <!-- type badge -->
  <rect x="22" y="24" width="{type_w}" height="22" rx="11" fill="{accent}" fill-opacity="0.14" stroke="{accent}" stroke-opacity="0.6"/>
  <circle cx="35" cy="35" r="3.5" fill="{accent}">
    <animate attributeName="opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="39" font-size="11.5" font-weight="700" letter-spacing="1" fill="{accent}">{xesc(ptype.upper())}</text>
  <!-- title -->
  {tl_svg}
  <!-- meta -->
  <text x="22" y="232" font-size="12.5" fill="#5b7186">{xesc(meta)}</text>
  <!-- tags -->
  {tags_svg}
  <!-- corner prompt -->
  <text x="266" y="282" font-size="13" fill="{accent}" opacity="0.5">&gt;_</text>
</svg>
'''


def build_block(posts):
    if not posts:
        return "_No posts published yet — check back soon._"
    rows = []
    for i in range(0, len(posts), PER_ROW):
        cells = []
        for p in posts[i:i + PER_ROW]:
            slug = slugify(p.get("file"))
            url = POST_URL + quote(p.get("file", ""))
            cells.append(
                f'<td width="33%" align="center">'
                f'<a href="{url}"><img src="{CARD_RAW}{slug}.svg" width="100%" '
                f'alt="{xesc(p["title"])}" /></a></td>'
            )
        rows.append("<tr>\n" + "\n".join(cells) + "\n</tr>")
    return '<table>\n' + "\n".join(rows) + '\n</table>'


def main():
    posts = [p for p in fetch_posts() if p.get("published") and p.get("title")]
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    posts = posts[:MAX_POSTS]

    if CARD_DIR.exists():
        shutil.rmtree(CARD_DIR)
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    for p in posts:
        (CARD_DIR / f"{slugify(p.get('file'))}.svg").write_text(make_card_svg(p), encoding="utf-8")

    block = build_block(posts)
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("ERROR: markers not found", file=sys.stderr)
        sys.exit(1)
    new = re.sub(re.escape(START) + r".*?" + re.escape(END),
                 f"{START}\n{block}\n{END}", text, flags=re.S)
    README.write_text(new, encoding="utf-8")
    print(f"Generated {len(posts)} card(s); README updated.")


if __name__ == "__main__":
    main()

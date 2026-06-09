#!/usr/bin/env python3
"""Fetch latest published posts from r34p3r-dhan.in and inject them into README.md
between the BLOG-POST-LIST markers. No third-party dependencies (stdlib only)."""
import json
import re
import sys
import urllib.request
from urllib.parse import quote
from pathlib import Path

FEED = "https://r34p3r-dhan.in/posts.json"
SITE = "https://r34p3r-dhan.in"
POST_URL = "https://r34p3r-dhan.in/posts/post.html?file="
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"
MAX_POSTS = 4
PER_ROW = 2

TYPE_COLOR = {"research": "00FF99", "writeup": "00d4ff", "notes": "f0c674"}


def fetch_posts():
    req = urllib.request.Request(FEED, headers={"User-Agent": "reaper-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def reachable(url):
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "reaper-readme-bot"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def badge(label, color, label_color="0d1117"):
    txt = quote(str(label).replace("-", "--").replace("_", "__").replace(" ", "_"))
    return (f'<img src="https://img.shields.io/badge/{txt}-{color}'
            f'?style=flat-square&amp;labelColor={label_color}" alt="{label}" />')


def card(post):
    url = POST_URL + quote(post.get("file", ""))
    title = post["title"].strip()
    ptype = (post.get("type") or "").lower()
    color = TYPE_COLOR.get(ptype, "8b949e")
    date = post.get("date", "")
    rt = post.get("read_time")
    summary = (post.get("summary") or "").strip()

    parts = ['<td width="50%" valign="top">']
    # cover image only if it actually resolves
    cover = post.get("cover")
    if cover:
        cover_url = cover if cover.startswith("http") else SITE + cover
        if reachable(cover_url):
            parts.append(f'<a href="{url}"><img src="{cover_url}" width="100%" '
                         f'alt="{title}" /></a><br/>')
    parts.append(f'<h3><a href="{url}">{title}</a></h3>')
    meta = []
    if ptype:
        meta.append(badge(ptype.upper(), color))
    if date:
        meta.append(badge(date, "1f2937"))
    if rt:
        meta.append(badge(f"{rt} min read", "1f2937"))
    if meta:
        parts.append(" ".join(meta) + "<br/><br/>")
    if summary:
        parts.append(f"<sub>{summary}</sub><br/><br/>")
    tags = post.get("tags", [])
    if tags:
        parts.append(" ".join(badge(f"#{t}", "2d333b") for t in tags))
    parts.append("</td>")
    return "\n".join(parts)


def build_block(posts):
    posts = [p for p in posts if p.get("published") and p.get("title")]
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    posts = posts[:MAX_POSTS]
    if not posts:
        return "_No posts published yet — check back soon._"

    rows = []
    for i in range(0, len(posts), PER_ROW):
        chunk = posts[i:i + PER_ROW]
        cells = "\n".join(card(p) for p in chunk)
        rows.append(f"<tr>\n{cells}\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def main():
    posts = fetch_posts()
    block = build_block(posts)
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("ERROR: BLOG-POST-LIST markers not found in README.md", file=sys.stderr)
        sys.exit(1)
    new_text = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n{block}\n{END}",
        text,
        flags=re.S,
    )
    if new_text != text:
        README.write_text(new_text, encoding="utf-8")
        print("README.md updated with latest posts.")
    else:
        print("No changes — posts already up to date.")


if __name__ == "__main__":
    main()

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
POST_URL = "https://r34p3r-dhan.in/posts/post.html?file="
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"
MAX_POSTS = 5


def fetch_posts():
    req = urllib.request.Request(FEED, headers={"User-Agent": "reaper-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def build_block(posts):
    posts = [p for p in posts if p.get("published") and p.get("title")]
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    posts = posts[:MAX_POSTS]
    if not posts:
        return "_No posts published yet — check back soon._"

    lines = []
    for p in posts:
        url = POST_URL + quote(p.get("file", ""))
        title = p["title"].strip()
        ptype = (p.get("type") or "").upper()
        date = p.get("date", "")
        rt = p.get("read_time")
        meta_bits = []
        if ptype:
            meta_bits.append(f"`{ptype}`")
        if date:
            meta_bits.append(date)
        if rt:
            meta_bits.append(f"{rt} min read")
        meta = " · ".join(meta_bits)
        summary = (p.get("summary") or "").strip()
        tags = " ".join(f"`#{t}`" for t in p.get("tags", []))

        entry = f"- **[{title}]({url})**"
        if meta:
            entry += f"  \n  <sub>{meta}</sub>"
        if summary:
            entry += f"  \n  {summary}"
        if tags:
            entry += f"  \n  {tags}"
        lines.append(entry)
    return "\n".join(lines)


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

#!/usr/bin/env python3
"""Save every poem from baithak.blogspot.com into poems.json.

Run by the GitHub Action in .github/workflows/snapshot.yml (daily), or by hand:

    python3 scripts/fetch_poems.py

The page (index.html) loads poems.json first, so every poem is written on the
GitHub page itself, in full, even when the blog is slow or unreachable. The live
blog feed is still read on every visit to pick up anything newer.

Only the Python standard library is used.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BLOG = "https://baithak.blogspot.com"
PAGE_SIZE = 150
OUT = "poems.json"
UA = "Mozilla/5.0 (compatible; baithtak-snapshot/1.0; +https://github.com/Temporal3/Baithtak)"

# Markers Blogger leaves behind when a feed entry stops at a jump break.
CUT_MARKERS = re.compile(r"jump-link|class=['\"]more-link|name=['\"]more['\"]|id=['\"]more['\"]", re.I)


def get(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network hiccup: back off and try again
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("could not fetch %s: %s" % (url, last))


class PostBody(HTMLParser):
    """Collect the inner HTML of the first element whose class contains 'post-body'."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.active = False
        self.done = False
        self.parts = []

    @staticmethod
    def _attrs(attrs):
        return "".join(
            ' %s="%s"' % (k, (v or "").replace('"', "&quot;")) if v is not None else " " + k
            for k, v in attrs
        )

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if not self.active:
            cls = dict(attrs).get("class") or ""
            if tag == "div" and "post-body" in cls.split():
                self.active = True
                self.depth = 1
            return
        if tag == "div":
            self.depth += 1
        void = tag in ("br", "img", "hr", "meta", "link", "input")
        self.parts.append("<%s%s%s>" % (tag, self._attrs(attrs), " /" if void else ""))

    def handle_startendtag(self, tag, attrs):
        if self.active and not self.done:
            self.parts.append("<%s%s />" % (tag, self._attrs(attrs)))

    def handle_endtag(self, tag):
        if not self.active or self.done:
            return
        if tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.done = True
                return
        if tag not in ("br", "img", "hr", "meta", "link", "input"):
            self.parts.append("</%s>" % tag)

    def handle_data(self, data):
        if self.active and not self.done:
            self.parts.append(data)

    def handle_entityref(self, name):
        if self.active and not self.done:
            self.parts.append("&%s;" % name)

    def handle_charref(self, name):
        if self.active and not self.done:
            self.parts.append("&#%s;" % name)


def body_from_page(url):
    """Full text of one poem, taken from its own page on the blog."""
    page = get(url + ("&" if "?" in url else "?") + "m=0")
    parser = PostBody()
    parser.feed(page)
    html = "".join(parser.parts).strip()
    return html or None


def entry_to_post(e):
    url = ""
    for link in e.get("link", []):
        if link.get("rel") == "alternate":
            url = link.get("href", "")
    content = (e.get("content") or {}).get("$t") or ""
    summary = (e.get("summary") or {}).get("$t") or ""
    needs_page = (not content) or bool(CUT_MARKERS.search(content))
    partial = False
    html = content
    if needs_page and url:
        try:
            full = body_from_page(url)
        except Exception as err:
            print("  page fetch failed for %s: %s" % (url, err), file=sys.stderr)
            full = None
        if full:
            html = full
        elif not content:
            html = summary
            partial = True
    elif not content:
        html = summary
        partial = True
    return {
        "title": (e.get("title") or {}).get("$t") or "(untitled)",
        "url": url,
        "published": (e.get("published") or e.get("updated") or {}).get("$t", ""),
        "labels": [c["term"] for c in e.get("category", []) if c.get("term")],
        "html": html,
        "partial": partial,
    }


def main():
    posts, total, start = [], None, 1
    while total is None or start <= total:
        q = urllib.parse.urlencode({"alt": "json", "max-results": PAGE_SIZE, "start-index": start})
        feed = json.loads(get("%s/feeds/posts/default?%s" % (BLOG, q)))["feed"]
        if total is None:
            total = int(feed["openSearch$totalResults"]["$t"])
            print("blog reports %d posts" % total)
        entries = feed.get("entry", [])
        if not entries:
            break
        for e in entries:
            posts.append(entry_to_post(e))
        print("  fetched %d / %d" % (len(posts), total))
        start += PAGE_SIZE

    # Never replace a good snapshot with a half-finished one.
    if not total or len(posts) < total * 0.98:
        print("only %d of %s posts arrived; leaving %s untouched" % (len(posts), total, OUT), file=sys.stderr)
        return 1

    seen, unique = set(), []
    for p in posts:
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        if not p["partial"]:
            del p["partial"]
        unique.append(p)
    unique.sort(key=lambda p: p["published"], reverse=True)

    out = {"total": total, "posts": unique}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    partial = sum(1 for p in unique if p.get("partial"))
    print("wrote %d poems to %s (%d only partly available)" % (len(unique), OUT, partial))
    return 0


if __name__ == "__main__":
    sys.exit(main())

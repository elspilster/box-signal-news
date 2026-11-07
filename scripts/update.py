#!/usr/bin/env python3
"""Collect RSS headlines and keep a permanent date-indexed archive (Python stdlib)."""
import datetime as dt
import email.utils
import html
import json
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FEEDS = [
    ("UK", "BBC News", "https://feeds.bbci.co.uk/news/uk/rss.xml"),
    ("World", "BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Business", "BBC News", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Technology", "BBC News", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Science", "BBC News", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("Entertainment", "BBC News", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
    ("Sport", "BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
    ("World", "The Guardian", "https://www.theguardian.com/world/rss"),
    ("UK", "The Guardian", "https://www.theguardian.com/uk-news/rss"),
    ("Technology", "The Guardian", "https://www.theguardian.com/uk/technology/rss"),
    ("Science", "The Guardian", "https://www.theguardian.com/science/rss"),
    ("Business", "The Guardian", "https://www.theguardian.com/uk/business/rss"),
    ("Sport", "The Guardian", "https://www.theguardian.com/uk/sport/rss"),
]

def clean(value, limit=220):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()[:limit]

def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "BoxSignalNews/1.0 (RSS headline reader)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read(2000000)

def parse(raw, category, publisher):
    result = []
    root = ET.fromstring(raw)
    for item in root.findall(".//item")[:25]:
        title = clean(item.findtext("title"), 170)
        url = (item.findtext("link") or "").strip()
        if not title or not url.startswith(("https://", "http://")):
            continue
        date = item.findtext("pubDate") or ""
        try:
            published = email.utils.parsedate_to_datetime(date).astimezone(dt.timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            published = ""
        result.append({"title": title, "url": url, "summary": clean(item.findtext("description")),
                       "source": publisher, "category": category, "published": published})
    return result

def main():
    now = dt.datetime.now(dt.timezone.utc)
    date = now.date().isoformat()
    stories = []
    for category, publisher, url in FEEDS:
        try:
            stories.extend(parse(fetch(url), category, publisher))
        except Exception as exc:
            print("Feed unavailable:", publisher, category, str(exc))
    unique, seen = [], set()
    for story in sorted(stories, key=lambda s: s["published"], reverse=True):
        key = story["url"].split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(story)
    if not unique:
        raise RuntimeError("No feeds available; existing archive remains unchanged")
    DATA.mkdir(exist_ok=True)
    issues = DATA / "issues"
    issues.mkdir(exist_ok=True)
    payload = {"date": date, "updated": now.isoformat(), "stories": unique[:180]}
    # Refresh only today's issue. Never overwrite older dated issues.
    today_file = issues / (date + ".json")
    today_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATA / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dates = sorted((p.stem for p in issues.glob("????-??-??.json")), reverse=True)
    (DATA / "index.json").write_text(json.dumps({"dates": dates}, indent=2) + "\n", encoding="utf-8")
    print("Saved", len(payload["stories"]), "headlines for", date)

if __name__ == "__main__":
    main()

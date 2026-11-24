#!/usr/bin/env python3
"""Fetch public biotech / nano / AI-med news into nanotech/data/biotech-news.json.

Designed for GitHub Actions (stdlib only). Sources are reputable RSS / NCBI E-utilities.
Items are third-party; never invent Nanotech-owned papers.
"""

from __future__ import annotations

import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "biotech-news.json"
MAX_ITEMS = 12
# Agency RSS hosts often 404 non-browser UAs.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

FEEDS = [
    {
        "id": "fda-press",
        "source": "FDA",
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
        "prefer_keywords": True,
    },
    {
        "id": "nature-nbt",
        "source": "Nature Biotechnology",
        "url": "https://www.nature.com/nbt.rss",
        "prefer_keywords": False,
    },
    {
        "id": "nature-biotech",
        "source": "Nature Biotechnology subject",
        "url": "https://www.nature.com/subjects/biotechnology.rss",
        "prefer_keywords": False,
    },
    {
        "id": "sciencedaily-biotech",
        "source": "ScienceDaily",
        "url": "https://www.sciencedaily.com/rss/plants_animals/biotechnology.xml",
        "prefer_keywords": True,
    },
]

KEYWORDS = re.compile(
    r"\b("
    r"AI|artificial intelligence|machine learning|deep learning|"
    r"nano(?:particle|medicine|tech|carrier)?|lipid nanoparticle|LNP|"
    r"mRNA|siRNA|gene therap(?:y|ies)|CRISPR|"
    r"biotech(?:nology)?|biomedical|medtech|medical device|"
    r"cancer|oncolog|vaccine|drug deliver|"
    r"FDA|EMA|clinical trial"
    r")\b",
    re.I,
)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss": "http://purl.org/rss/1.0/",
}


def http_get(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except Exception:
        # Some hosts (e.g. FDA) answer curl more reliably than urllib.
        import subprocess

        proc = subprocess.run(
            [
                "curl",
                "-fsSL",
                "-A",
                USER_AGENT,
                "--max-time",
                str(timeout),
                url,
            ],
            check=False,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        raise


def strip_html(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clip(text: str, n: int = 280) -> str:
    text = strip_html(text)
    if len(text) <= n:
        return text
    cut = text[: n - 1].rsplit(" ", 1)[0]
    return (cut or text[: n - 1]).rstrip(".,;:") + "…"


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        pass
    try:
        # ISO-ish
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def item_id(url: str, title: str) -> str:
    return hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()[:16]


def text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def extract_rss_items(xml_bytes: bytes, source: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items: list[dict] = []

    # RSS 2.0
    for item in root.findall("./channel/item"):
        title = text_of(item.find("title"))
        link = text_of(item.find("link"))
        if not link:
            guid = item.find("guid")
            link = text_of(guid)
        desc = text_of(item.find("description")) or text_of(item.find("content:encoded", NS))
        pub = text_of(item.find("pubDate")) or text_of(item.find("dc:date", NS))
        if title and link:
            items.append(
                {
                    "source": source,
                    "title": title,
                    "summary": clip(desc or title),
                    "url": link.strip(),
                    "publishedAt": parse_date(pub),
                }
            )

    # Atom
    for entry in root.findall("atom:entry", NS) or root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = text_of(entry.find("atom:title", NS)) or text_of(
            entry.find("{http://www.w3.org/2005/Atom}title")
        )
        link = ""
        for link_el in entry.findall("atom:link", NS) or entry.findall(
            "{http://www.w3.org/2005/Atom}link"
        ):
            href = link_el.attrib.get("href", "")
            rel = link_el.attrib.get("rel", "alternate")
            if href and rel in ("alternate", ""):
                link = href
                break
            if href and not link:
                link = href
        summary = text_of(entry.find("atom:summary", NS)) or text_of(
            entry.find("{http://www.w3.org/2005/Atom}summary")
        )
        if not summary:
            summary = text_of(entry.find("atom:content", NS)) or text_of(
                entry.find("{http://www.w3.org/2005/Atom}content")
            )
        pub = text_of(entry.find("atom:updated", NS)) or text_of(
            entry.find("atom:published", NS)
        )
        if title and link:
            items.append(
                {
                    "source": source,
                    "title": title,
                    "summary": clip(summary or title),
                    "url": link.strip(),
                    "publishedAt": parse_date(pub),
                }
            )

    # RDF RSS 1.0 (Nature)
    if not items:
        for item in root.findall(".//{http://purl.org/rss/1.0/}item") or root.findall(
            ".//item"
        ):
            title = ""
            link = item.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "")
            desc = ""
            pub = ""
            for child in list(item):
                name = local(child.tag)
                if name == "title":
                    title = text_of(child)
                elif name == "link":
                    link = text_of(child) or link
                elif name in ("description", "abstract"):
                    desc = text_of(child)
                elif name in ("date", "created", "issued"):
                    pub = text_of(child)
            if title and link:
                items.append(
                    {
                        "source": source,
                        "title": title,
                        "summary": clip(desc or title),
                        "url": link.strip(),
                        "publishedAt": parse_date(pub),
                    }
                )

    return items


def parse_one_pubmed_date(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y %b %d", "%Y %b", "%Y/%m/%d %H:%M", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    # Truncate time portion for sortpubdate like "2026/09/04 00:00"
    if " " in raw:
        return parse_one_pubmed_date(raw.split(" ")[0])
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def parse_pubmed_date(rec: dict) -> str | None:
    """Prefer electronic publication date over journal print date (can be future)."""
    now = datetime.now(timezone.utc)
    # Allow slight future dating; reject far-ahead print schedules.
    soft_horizon = now + timedelta(days=14)
    for key in ("epubdate", "sortpubdate", "pubdate"):
        dt = parse_one_pubmed_date(rec.get(key) or "")
        if not dt:
            continue
        if dt > soft_horizon:
            continue
        return dt.isoformat().replace("+00:00", "Z")
    return None


def fetch_pubmed(limit: int = 6) -> list[dict]:
    """Recent PubMed hits on nanomedicine / LNP / AI delivery (E-utilities)."""
    term = (
        '("lipid nanoparticle"[Title/Abstract] OR nanomedicine[Title/Abstract] '
        'OR "drug delivery"[Title/Abstract]) AND ("machine learning"[Title/Abstract] '
        'OR "artificial intelligence"[Title/Abstract] OR "deep learning"[Title/Abstract])'
    )
    search_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&retmode=json&retmax={limit}&sort=pub+date&term={urllib.parse.quote(term)}"
    )
    try:
        data = json.loads(http_get(search_url).decode("utf-8"))
        ids = data.get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        print(f"pubmed search failed: {exc}", file=sys.stderr)
        return []
    if not ids:
        return []
    summary_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pubmed&retmode=json&id={','.join(ids)}"
    )
    try:
        summary = json.loads(http_get(summary_url).decode("utf-8"))
    except Exception as exc:
        print(f"pubmed summary failed: {exc}", file=sys.stderr)
        return []
    result = []
    for pmid in ids:
        rec = summary.get("result", {}).get(pmid)
        if not isinstance(rec, dict):
            continue
        title = strip_html(rec.get("title") or "")
        if not title:
            continue
        pub = parse_pubmed_date(rec)
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        journal = (rec.get("fulljournalname") or rec.get("source") or "PubMed").strip()
        result.append(
            {
                "source": f"PubMed · {journal}",
                "title": title.rstrip("."),
                "summary": clip(f"{journal}. PMID {pmid}."),
                "url": url,
                "publishedAt": pub,
            }
        )
    return result


def score_item(item: dict, prefer_keywords: bool) -> float:
    blob = f"{item['title']} {item['summary']}"
    score = 0.0
    if KEYWORDS.search(blob):
        score += 3.0
    elif prefer_keywords:
        score -= 1.0
    if item.get("publishedAt"):
        try:
            dt = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
            score += max(0.0, 2.0 - age_days / 30.0)
        except Exception:
            pass
    return score


def normalize(item: dict) -> dict:
    title = strip_html(item["title"])
    url = item["url"]
    source = item["source"]
    return {
        "id": item_id(url, title),
        "publishedAt": item.get("publishedAt"),
        "source": source,
        "title": {"en": title},
        "summary": {"en": item.get("summary") or title},
        "url": url,
        "linkLabel": {
            "en": f"Read on {source.split('·')[0].strip()}",
            "zh-Hant": f"前往 {source.split('·')[0].strip()}",
            "zh-Hans": f"前往 {source.split('·')[0].strip()}",
        },
        "langNote": {
            "en": "Source language: English",
            "zh-Hant": "原文為英文",
            "zh-Hans": "原文为英文",
        },
    }


def main() -> int:
    collected: list[dict] = []
    errors: list[str] = []

    for feed in FEEDS:
        try:
            raw = http_get(feed["url"])
            parsed = extract_rss_items(raw, feed["source"])
            for it in parsed:
                it["_prefer"] = feed["prefer_keywords"]
                it["_feed"] = feed["id"]
            collected.extend(parsed)
            print(f"ok {feed['id']}: {len(parsed)} items")
        except Exception as exc:
            msg = f"fail {feed['id']}: {exc}"
            errors.append(msg)
            print(msg, file=sys.stderr)

    try:
        pm = fetch_pubmed(6)
        for it in pm:
            it["_prefer"] = False
            it["_feed"] = "pubmed"
        collected.extend(pm)
        print(f"ok pubmed: {len(pm)} items")
    except Exception as exc:
        errors.append(f"fail pubmed: {exc}")
        print(f"fail pubmed: {exc}", file=sys.stderr)

    # Rank + dedupe by URL
    ranked = sorted(
        collected,
        key=lambda it: score_item(it, it.get("_prefer", False)),
        reverse=True,
    )
    seen = set()
    selected = []
    for it in ranked:
        key = re.sub(r"[?#].*$", "", it["url"]).rstrip("/").lower()
        if key in seen:
            continue
        if it.get("_prefer") and score_item(it, True) < 2.0:
            continue
        seen.add(key)
        selected.append(normalize(it))
        if len(selected) >= MAX_ITEMS:
            break

    # Keep previous curated bilingual items if fetch nearly empty
    previous = []
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            previous = []

    if len(selected) < 3 and previous:
        print("warning: few fresh items; merging with previous feed", file=sys.stderr)
        for old in previous:
            if len(selected) >= MAX_ITEMS:
                break
            oid = old.get("id") or item_id(old.get("url", ""), old.get("title", {}).get("en", ""))
            if any(s["id"] == oid for s in selected):
                continue
            selected.append(old)

    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "refreshHours": 6,
        "generator": "nanotech/scripts/fetch_biotech_news.py",
        "sources": [f["id"] for f in FEEDS] + ["pubmed-eutils"],
        "errors": errors,
        "items": selected,
        "disclaimer": {
            "en": "Third-party news for industry scanning — not Nanotech Innovation publications or endorsements.",
            "zh-Hant": "第三方產業新聞掃描——非納米科研技術之論文或背書。",
            "zh-Hans": "第三方产业新闻扫描——非纳米科研技术之论文或背书。",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(selected)} items)")
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())

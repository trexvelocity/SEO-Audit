#!/usr/bin/env python3
"""
GEO + AEO Audit Crawler for aistechnolabs.com
Crawls up to 50 pages and produces structured JSON for PDF report generation.
"""
import json
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

START_URL = "https://www.aistechnolabs.com/"
DOMAIN = "www.aistechnolabs.com"
MAX_PAGES = 50
OUTPUT_DIR = Path("/tmp/audit-aistechnolabs")
PAGES_DIR = OUTPUT_DIR / "pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 ClaudeSEO/1.2"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
           "PerplexityBot", "CCBot", "Bytespider", "cohere-ai", "Google-Extended",
           "Applebot-Extended", "FacebookBot", "Amazonbot", "DuckAssistBot",
           "Diffbot", "ImagesiftBot", "Omgilibot", "YouBot"]


def normalize_url(url, base):
    full = urljoin(base, url)
    full, _ = urldefrag(full)
    return full


def is_internal(url):
    try:
        p = urlparse(url)
        return p.netloc in (DOMAIN, "aistechnolabs.com", "") and p.scheme in ("http", "https", "")
    except Exception:
        return False


def fetch(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        return None


def check_robots():
    robots_url = "https://www.aistechnolabs.com/robots.txt"
    r = fetch(robots_url)
    result = {
        "url": robots_url,
        "found": False,
        "status": None,
        "content": "",
        "ai_bot_status": {},
        "sitemaps": [],
    }
    if r is None:
        return result
    result["status"] = r.status_code
    if r.status_code == 200:
        result["found"] = True
        result["content"] = r.text[:5000]
        # parse sitemaps
        for line in r.text.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                sm = line.split(":", 1)[1].strip()
                result["sitemaps"].append(sm)
        # check each AI bot
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        for bot in AI_BOTS:
            try:
                allowed = rp.can_fetch(bot, "https://www.aistechnolabs.com/")
                result["ai_bot_status"][bot] = "allowed" if allowed else "blocked"
            except Exception:
                result["ai_bot_status"][bot] = "unknown"
    return result


def check_llms_txt():
    urls = ["https://www.aistechnolabs.com/llms.txt", "https://www.aistechnolabs.com/llms-full.txt"]
    out = {}
    for u in urls:
        r = fetch(u, timeout=10)
        out[u] = {
            "status": r.status_code if r else None,
            "found": bool(r and r.status_code == 200),
            "size_bytes": len(r.content) if r and r.status_code == 200 else 0,
        }
    return out


def check_sitemap(sm_url):
    r = fetch(sm_url, timeout=20)
    if not r or r.status_code != 200:
        return {"url": sm_url, "found": False, "status": r.status_code if r else None, "urls": []}
    try:
        soup = BeautifulSoup(r.content, "xml")
        urls = [loc.text.strip() for loc in soup.find_all("loc")]
        return {"url": sm_url, "found": True, "status": 200, "urls": urls, "url_count": len(urls)}
    except Exception:
        return {"url": sm_url, "found": True, "status": 200, "urls": [], "parse_error": True}


# --- GEO/AEO analysis helpers ---

def extract_passages(text, target_min=134, target_max=167):
    """Find paragraphs in optimal AI citation length range."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    optimal = []
    for p in paragraphs:
        wc = len(p.split())
        if target_min <= wc <= target_max:
            optimal.append({"word_count": wc, "preview": p[:200]})
    return optimal[:5], len(paragraphs)


def detect_question_headings(headings):
    q_words = ["what", "why", "how", "when", "where", "who", "which", "can", "do",
               "does", "is", "are", "should"]
    q_count = 0
    for h in headings:
        ht = h.lower().strip().rstrip(":?!.")
        for qw in q_words:
            if ht.startswith(qw + " ") or "?" in h:
                q_count += 1
                break
    return q_count


def analyze_page(url, html, status_code):
    soup = BeautifulSoup(html, "lxml")

    # Strip nav/footer/script/style for text analysis
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    title = (soup.title.string if soup.title and soup.title.string else "").strip()
    meta_desc = ""
    m = soup.find("meta", attrs={"name": "description"})
    if m and m.get("content"):
        meta_desc = m["content"].strip()
    canonical = ""
    c = soup.find("link", rel="canonical")
    if c and c.get("href"):
        canonical = c["href"]
    robots_meta = ""
    rm = soup.find("meta", attrs={"name": "robots"})
    if rm and rm.get("content"):
        robots_meta = rm["content"]

    # OG / Twitter tags
    og_tags = {m.get("property", ""): m.get("content", "") for m in soup.find_all("meta", attrs={"property": re.compile("^og:")})}
    tw_tags = {m.get("name", ""): m.get("content", "") for m in soup.find_all("meta", attrs={"name": re.compile("^twitter:")})}

    # Headings
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3s = [h.get_text(strip=True) for h in soup.find_all("h3")]
    headings_all = h1s + h2s + h3s
    q_headings = detect_question_headings(headings_all)

    # Body text
    body = soup.find("body")
    text = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)
    word_count = len(text.split())

    # Optimal AI citation passages
    optimal_passages, total_paragraphs = extract_passages(text)

    # Schema / JSON-LD
    schema_blocks = []
    schema_types = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "{}")
            schema_blocks.append(data)
            if isinstance(data, dict):
                t = data.get("@type")
                if isinstance(t, list):
                    schema_types.extend(t)
                elif t:
                    schema_types.append(t)
                if "@graph" in data:
                    for g in data["@graph"]:
                        if isinstance(g, dict) and g.get("@type"):
                            gt = g["@type"]
                            if isinstance(gt, list):
                                schema_types.extend(gt)
                            else:
                                schema_types.append(gt)
            elif isinstance(data, list):
                for d in data:
                    if isinstance(d, dict) and d.get("@type"):
                        t = d["@type"]
                        if isinstance(t, list):
                            schema_types.extend(t)
                        else:
                            schema_types.append(t)
        except Exception:
            pass

    # FAQ detection (structural, not just schema)
    faq_blocks = 0
    for h in soup.find_all(["h2", "h3", "h4"]):
        if "?" in h.get_text():
            faq_blocks += 1

    # Images
    imgs = soup.find_all("img")
    img_count = len(imgs)
    img_no_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())
    img_lazy = sum(1 for i in imgs if (i.get("loading") or "").lower() == "lazy")

    # Tables and lists
    tables = len(soup.find_all("table"))
    uls = len(soup.find_all("ul"))
    ols = len(soup.find_all("ol"))

    # Author / date signals
    has_author = bool(soup.find(attrs={"rel": "author"})) or bool(soup.find("meta", attrs={"name": "author"}))
    has_pub_date = bool(soup.find("meta", attrs={"property": "article:published_time"})) or \
                   bool(soup.find("time"))
    has_mod_date = bool(soup.find("meta", attrs={"property": "article:modified_time"}))

    # Links
    internal_links = 0
    external_links = 0
    nofollow_links = 0
    for a in soup.find_all("a", href=True):
        full = normalize_url(a["href"], url)
        if is_internal(full):
            internal_links += 1
        else:
            external_links += 1
        rel = (a.get("rel") or [])
        if isinstance(rel, list) and "nofollow" in rel:
            nofollow_links += 1

    # hreflang
    hreflangs = [l.get("hreflang") for l in soup.find_all("link", rel="alternate") if l.get("hreflang")]

    # JS shell detection: short body, lots of <script>
    scripts_inline = len(soup.find_all("script"))
    js_dependent = word_count < 100 and scripts_inline > 5

    # Per-page GEO score
    score = 0
    score_breakdown = {}

    # Citability (25)
    cit = 0
    if optimal_passages: cit += 12
    elif total_paragraphs >= 5: cit += 6
    if word_count >= 800: cit += 8
    elif word_count >= 300: cit += 4
    if any(re.search(r'\b(is|are|refers to|means|defined as)\b', p["preview"].lower()) for p in optimal_passages):
        cit += 5
    cit = min(25, cit)
    score += cit
    score_breakdown["citability"] = cit

    # Structural readability (20)
    sr = 0
    if h1s and len(h1s) == 1: sr += 4
    elif h1s: sr += 2
    if h2s: sr += 4
    if q_headings >= 3: sr += 6
    elif q_headings >= 1: sr += 3
    if tables: sr += 3
    if uls + ols >= 3: sr += 3
    sr = min(20, sr)
    score += sr
    score_breakdown["structural_readability"] = sr

    # Multimodal (15)
    mm = 0
    if img_count >= 3: mm += 6
    elif img_count >= 1: mm += 3
    if img_count > 0 and img_no_alt / max(img_count, 1) < 0.2: mm += 4
    if soup.find("video") or soup.find("iframe", src=re.compile(r"youtube|vimeo")): mm += 5
    mm = min(15, mm)
    score += mm
    score_breakdown["multimodal"] = mm

    # Authority (20)
    au = 0
    if has_author: au += 5
    if has_pub_date: au += 5
    if has_mod_date: au += 3
    if "Organization" in schema_types or "Person" in schema_types: au += 4
    if external_links >= 2: au += 3
    au = min(20, au)
    score += au
    score_breakdown["authority"] = au

    # Technical (20)
    tc = 0
    if not js_dependent: tc += 8
    if canonical: tc += 3
    if title and 30 <= len(title) <= 65: tc += 3
    elif title: tc += 1
    if meta_desc and 70 <= len(meta_desc) <= 160: tc += 3
    elif meta_desc: tc += 1
    if "noindex" not in robots_meta.lower(): tc += 3
    tc = min(20, tc)
    score += tc
    score_breakdown["technical"] = tc

    # AEO score (separate, focused on answer-engine specifics)
    aeo_score = 0
    aeo_breakdown = {}
    # FAQ presence
    aeo_f = min(25, faq_blocks * 5)
    aeo_score += aeo_f
    aeo_breakdown["faq_structure"] = aeo_f
    # Direct-answer first 60 words
    first_60 = " ".join(text.split()[:60]).lower()
    direct = 0
    if re.search(r'\b(is|are|provides|offers|delivers|specializes)\b', first_60): direct += 15
    if any(kw in first_60 for kw in ["ai", "service", "company", "agency", "solution"]): direct += 10
    aeo_score += direct
    aeo_breakdown["direct_answer"] = direct
    # Schema for AEO
    aeo_s = 0
    aeo_types = ["FAQPage", "HowTo", "QAPage", "Article", "Organization", "Service",
                 "BreadcrumbList", "Product", "WebSite", "WebPage"]
    matched = [t for t in schema_types if t in aeo_types]
    aeo_s = min(25, len(set(matched)) * 6)
    aeo_score += aeo_s
    aeo_breakdown["schema_coverage"] = aeo_s
    # Listicle / table density (AEO loves them)
    aeo_l = 0
    if tables: aeo_l += 8
    if ols >= 2: aeo_l += 8
    if q_headings >= 2: aeo_l += 9
    aeo_l = min(25, aeo_l)
    aeo_score += aeo_l
    aeo_breakdown["list_table_density"] = aeo_l
    aeo_score = min(100, aeo_score)

    return {
        "url": url,
        "status_code": status_code,
        "title": title,
        "title_length": len(title),
        "meta_description": meta_desc,
        "meta_desc_length": len(meta_desc),
        "canonical": canonical,
        "robots_meta": robots_meta,
        "h1_count": len(h1s),
        "h1_text": h1s[:3],
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "question_headings": q_headings,
        "word_count": word_count,
        "paragraph_count": total_paragraphs,
        "optimal_passages": optimal_passages,
        "optimal_passage_count": len(optimal_passages),
        "schema_types": list(set(schema_types)),
        "schema_count": len(schema_blocks),
        "faq_blocks": faq_blocks,
        "img_count": img_count,
        "img_no_alt": img_no_alt,
        "img_lazy_loaded": img_lazy,
        "tables": tables,
        "lists_ul": uls,
        "lists_ol": ols,
        "has_author": has_author,
        "has_pub_date": has_pub_date,
        "has_mod_date": has_mod_date,
        "internal_links": internal_links,
        "external_links": external_links,
        "nofollow_links": nofollow_links,
        "hreflangs": hreflangs,
        "scripts_inline": scripts_inline,
        "js_dependent": js_dependent,
        "og_tags": list(og_tags.keys()),
        "twitter_tags": list(tw_tags.keys()),
        "geo_score": score,
        "geo_breakdown": score_breakdown,
        "aeo_score": aeo_score,
        "aeo_breakdown": aeo_breakdown,
    }


def crawl():
    visited = set()
    queue = deque([START_URL])
    pages = []
    errors = []

    print(f"[crawler] starting from {START_URL}, max {MAX_PAGES} pages")

    while queue and len(pages) < MAX_PAGES:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        print(f"[{len(pages)+1}/{MAX_PAGES}] {url}")
        r = fetch(url)
        if r is None:
            errors.append({"url": url, "error": "fetch_failed"})
            continue
        if r.status_code != 200:
            errors.append({"url": url, "status": r.status_code})
            # still note for status tracking but don't analyze body
            continue

        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype.lower():
            continue

        try:
            page_data = analyze_page(url, r.text, r.status_code)
            page_data["response_time_ms"] = int(r.elapsed.total_seconds() * 1000)
            page_data["content_length_bytes"] = len(r.content)
            pages.append(page_data)
        except Exception as e:
            errors.append({"url": url, "error": f"analyze_failed: {e}"})
            continue

        # discover new links
        try:
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                full = normalize_url(a["href"], url)
                if is_internal(full) and full not in visited and full not in queue:
                    # skip non-html assets
                    if re.search(r"\.(jpg|jpeg|png|gif|svg|webp|pdf|zip|css|js|ico|woff2?)$", full, re.I):
                        continue
                    # skip fragments to same page
                    queue.append(full)
        except Exception:
            pass

        time.sleep(0.5)

    return pages, errors, list(visited)


if __name__ == "__main__":
    print("=== STEP 1: robots.txt ===")
    robots = check_robots()
    print(json.dumps(robots, indent=2)[:1500])

    print("\n=== STEP 2: llms.txt ===")
    llms = check_llms_txt()
    print(json.dumps(llms, indent=2))

    print("\n=== STEP 3: sitemaps ===")
    sitemaps = []
    sm_urls_to_check = robots.get("sitemaps", [])
    if not sm_urls_to_check:
        sm_urls_to_check = ["https://www.aistechnolabs.com/sitemap.xml",
                            "https://www.aistechnolabs.com/sitemap_index.xml"]
    for sm in sm_urls_to_check:
        sm_data = check_sitemap(sm)
        sitemaps.append(sm_data)
        print(f"  {sm}: found={sm_data['found']} urls={sm_data.get('url_count', 0)}")

    print("\n=== STEP 4: crawl ===")
    pages, errors, visited = crawl()

    summary = {
        "start_url": START_URL,
        "total_pages_crawled": len(pages),
        "total_visited": len(visited),
        "errors_count": len(errors),
        "robots": robots,
        "llms_txt": llms,
        "sitemaps": sitemaps,
        "pages": pages,
        "errors": errors,
    }

    out_file = OUTPUT_DIR / "audit_data.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[done] wrote {out_file} ({len(pages)} pages, {len(errors)} errors)")

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.moneydj.com/KMDJ/News/NewsRealList.aspx?a=MB010000"
OUTPUT = Path("data/news.json")

DAYS = 30
MAX_PAGES = 50

# Company universe: edit this list to add/remove companies.
COMPANIES = [
    "台積電", "聯發科", "廣達", "緯創", "緯穎",
    "鴻海", "英業達", "和碩", "日月光", "欣興",
    "南電", "金像電", "台光電", "雙鴻", "奇鋐",
    "技嘉", "華碩", "仁寶", "神達", "台達電"
]

# Event keywords: article must contain at least one company AND at least one event keyword.
EVENT_KEYWORDS = [
    "海外投資",
    "海外設廠",
    "設廠",
    "新廠",
    "擴廠",
    "投資",
    "產能",
    "資本支出",
    "海外布局",
    "美國廠",
    "墨西哥廠",
    "越南廠",
    "泰國廠",
    "馬來西亞廠",
    "日本廠",
    "歐洲廠"
]

# Optional topic keywords. These increase relevance score but are not required.
TOPIC_KEYWORDS = [
    "AI", "人工智慧", "輝達", "NVIDIA", "伺服器", "AI伺服器", "半導體", "晶片",
    "GPU", "CPU", "HBM", "記憶體", "DRAM", "先進封裝", "CoWoS", "封測",
    "散熱", "液冷", "水冷", "電源", "電源供應器", "被動元件", "MLCC",
    "電感", "PCB", "ABF", "載板", "光通訊", "光模組", "交換器", "網通",
    "資料中心", "電力", "儲能", "供應鏈", "瓶頸", "交期"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GitHub-Pages-company-event-news-monitor/1.0)"
}

def now_taipei():
    return datetime.now(timezone(timedelta(hours=8)))

def parse_tw_date(mmdd, hhmm):
    current = now_taipei()
    month, day = map(int, mmdd.split("/"))
    hour, minute = map(int, hhmm.split(":"))
    dt = datetime(current.year, month, day, hour, minute, tzinfo=current.tzinfo)

    if dt > current + timedelta(days=7):
        dt = dt.replace(year=current.year - 1)

    return dt

def find_hits(text, keywords):
    lower = text.lower()
    return sorted({kw for kw in keywords if kw.lower() in lower})

def score_article(company_hits, event_hits, topic_hits):
    # Required match gets a strong base score.
    return 100 + len(company_hits) * 10 + len(event_hits) * 10 + len(topic_hits)

def get(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text

def list_url(page_index):
    if page_index == 1:
        return BASE_URL
    return f"{BASE_URL}&index1={page_index}"

def parse_list_page(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "newsviewer.aspx" not in href.lower():
            continue

        title = a.get_text(" ", strip=True)
        if not title:
            continue

        context = " ".join([
            a.parent.get_text(" ", strip=True) if a.parent else "",
            " ".join(str(s).strip() for s in a.find_all_previous(string=True, limit=4))
        ])

        match = re.search(r"(\d{2}/\d{2})\s+(\d{2}:\d{2})", context)
        published_at = parse_tw_date(match.group(1), match.group(2)) if match else None

        items.append({
            "title": title,
            "url": urljoin("https://www.moneydj.com/KMDJ/News/", href),
            "published_at": published_at,
        })

    seen = set()
    deduped = []
    for item in items:
        if item["url"] in seen:
            continue
        deduped.append(item)
        seen.add(item["url"])

    return deduped

def article_body(url):
    try:
        soup = BeautifulSoup(get(url), "html.parser")
        text = soup.get_text("\n", strip=True)

        marker = "MoneyDJ新聞"
        marker_index = text.find(marker)
        if marker_index >= 0:
            text = text[marker_index:]

        text = re.sub(r"\n{2,}", "\n", text)
        return text[:5000]
    except Exception as error:
        return f"ARTICLE_FETCH_ERROR: {error}"

def crawl():
    current = now_taipei()
    cutoff = current - timedelta(days=DAYS)
    results = []

    for page in range(1, MAX_PAGES + 1):
        items = parse_list_page(get(list_url(page)))
        found_old_item = False

        for item in items:
            if item["published_at"] and item["published_at"] < cutoff:
                found_old_item = True
                continue

            body = article_body(item["url"])
            text = item["title"] + "\n" + body

            company_hits = find_hits(text, COMPANIES)
            event_hits = find_hits(text, EVENT_KEYWORDS)
            topic_hits = find_hits(text, TOPIC_KEYWORDS)

            # Main rule:
            # include only if article has at least one company AND one event keyword.
            if not company_hits or not event_hits:
                continue

            results.append({
                "title": item["title"],
                "url": item["url"],
                "published_at": item["published_at"].isoformat() if item["published_at"] else None,
                "score": score_article(company_hits, event_hits, topic_hits),
                "companies": company_hits,
                "events": event_hits,
                "topics": topic_hits,
                "keywords": company_hits + event_hits + topic_hits,
                "snippet": body[:700],
            })

        if found_old_item and results:
            break

    results.sort(key=lambda item: (item["published_at"] or "", item["score"]), reverse=True)

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "source": BASE_URL,
        "generated_at": current.isoformat(),
        "days": DAYS,
        "rule": "company AND event keyword",
        "companies": COMPANIES,
        "event_keywords": EVENT_KEYWORDS,
        "topic_keywords": TOPIC_KEYWORDS,
        "count": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    crawl()

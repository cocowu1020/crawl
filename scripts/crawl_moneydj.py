import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.moneydj.com/KMDJ/News/NewsRealList.aspx?a=MB010000"
OUTPUT = Path("data/news.json")
DAYS = 7
MAX_PAGES = 12

AI_SUPPLY_CHAIN_KEYWORDS = [
    "AI", "人工智慧", "輝達", "NVIDIA", "伺服器", "AI伺服器", "半導體", "晶片",
    "GPU", "CPU", "HBM", "記憶體", "DRAM", "先進封裝", "CoWoS", "封測",
    "台積電", "聯發科", "廣達", "緯創", "緯穎", "鴻海", "英業達", "和碩",
    "散熱", "液冷", "水冷", "電源", "電源供應器", "被動元件", "MLCC",
    "電感", "PCB", "ABF", "載板", "光通訊", "光模組", "交換器", "網通",
    "資料中心", "電力", "儲能", "供應鏈", "瓶頸", "產能", "交期"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GitHub-Pages-AI-supply-chain-news-monitor/1.0)"
}

def now_taipei():
    return datetime.now(timezone(timedelta(hours=8)))

def parse_tw_date(mmdd, hhmm):
    current = now_taipei()
    month, day = map(int, mmdd.split("/"))
    hour, minute = map(int, hhmm.split(":"))
    dt = datetime(current.year, month, day, hour, minute, tzinfo=current.tzinfo)

    # Handles year boundary if the crawler runs in early January.
    if dt > current + timedelta(days=7):
        dt = dt.replace(year=current.year - 1)

    return dt

def score_text(text):
    hits = []
    score = 0
    lower = text.lower()

    for kw in AI_SUPPLY_CHAIN_KEYWORDS:
        if kw.lower() in lower:
            hits.append(kw)
            score += 1

    return score, sorted(set(hits))

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
            score, hits = score_text(item["title"] + "\n" + body)

            if score <= 0:
                continue

            results.append({
                "title": item["title"],
                "url": item["url"],
                "published_at": item["published_at"].isoformat() if item["published_at"] else None,
                "score": score,
                "keywords": hits,
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
        "count": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    crawl()

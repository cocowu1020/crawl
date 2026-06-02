# MoneyDJ Company Event News Monitor

This GitHub Pages dashboard shows MoneyDJ articles that match:

```text
ANY company in COMPANIES
AND
ANY event keyword in EVENT_KEYWORDS
```

Example:

```text
台積電 + 海外投資
廣達 + 海外設廠
鴻海 + 墨西哥廠
```

## Edit companies or events

Open:

```text
scripts/crawl_moneydj.py
```

Edit these lists:

```python
COMPANIES = [...]
EVENT_KEYWORDS = [...]
TOPIC_KEYWORDS = [...]
```

`COMPANIES` and `EVENT_KEYWORDS` are required for an article to appear.

`TOPIC_KEYWORDS` only boosts relevance and displays tags.

## GitHub setup

1. Upload these files to the root of your repo.
2. Enable GitHub Pages.
3. Add the workflow file at `.github/workflows/crawl.yml`.
4. In GitHub repo settings, set Actions workflow permissions to **Read and write permissions**.
5. Run the crawler workflow manually once.

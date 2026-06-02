# MoneyDJ AI Supply Chain News Dashboard

This is a GitHub Pages-ready static dashboard. It uses a GitHub Actions workflow to crawl MoneyDJ every 6 hours and writes the results into `data/news.json`.

## Files

```text
index.html
data/news.json
scripts/crawl_moneydj.py
requirements.txt
.github/workflows/crawl.yml
```

## How to publish on GitHub Pages

1. Create a new GitHub repository.
2. Upload all files in this folder.
3. Go to **Settings → Actions → General**.
4. Under **Workflow permissions**, choose **Read and write permissions**.
5. Go to **Actions** and run **Crawl MoneyDJ AI Supply Chain News** manually once.
6. Go to **Settings → Pages**.
7. Under **Build and deployment**, choose:
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/ root**
8. Save.

Your site will be available at:

```text
https://YOUR_USERNAME.github.io/YOUR_REPOSITORY/
```

## Notes

- GitHub Pages cannot run Python directly. The Python crawler runs inside GitHub Actions, commits `data/news.json`, and the website reads that static JSON file.
- The default crawler window is the last 7 days.
- The workflow runs every 6 hours and can also be run manually.
- Please respect MoneyDJ's terms and avoid aggressive crawling.

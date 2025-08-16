# crawler.py
import os, re, time, json, sqlite3
from urllib.parse import urljoin, urlparse
from collections import deque
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "school_data.db")

# ---- 설정 -----------------------------------------------------------
# GitHub Actions나 로컬에서 환경변수로 넣을 수 있게 함.
# 예: '["https://학교도메인/","https://학교도메인/notice"]'
ENV_START_URLS = os.getenv("START_URLS_JSON")
if ENV_START_URLS:
    START_URLS = json.loads(ENV_START_URLS)
else:
    START_URLS = [
        "https://pajuwaseok-e.goepj.kr/pajuwaseok-e/main.do",              # ← 나중에 실제 도메인으로 바꿔요
        "https://pajuwaseok-e.goepj.kr/pajuwaseok-e/na/ntt/selectNttList.do?mi=8417&bbsId=5771"
    ]

MAX_PAGES = 200            # 과도한 크롤 방지
REQUEST_GAP_SEC = 0.5      # 로봇/서버 배려: 요청 간격
TIMEOUT = 10
SAME_DOMAIN_ONLY = True    # 시작 도메인(첫 URL) 밖으로는 안 나감
USER_AGENT = "Mozilla/5.0 (compatible; SchoolBot/1.0; +https://example.com/bot)"

# ---- 유틸 -----------------------------------------------------------
def same_domain(u, root):
    return urlparse(u).netloc == urlparse(root).netloc

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:20000]  # 너무 긴 문서는 잘라 저장

def fetch(url):
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text

def ensure_tables(con):
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      url TEXT UNIQUE,
      title TEXT,
      content TEXT,
      fetched_at TEXT
    );
    CREATE TABLE IF NOT EXISTS page_embeddings (
      page_id INTEGER PRIMARY KEY,
      vector TEXT NOT NULL,
      FOREIGN KEY(page_id) REFERENCES pages(id)
    );
    """)
    con.commit()

def save_page(con, url, title, content):
    cur = con.cursor()
    cur.execute("""
      INSERT OR REPLACE INTO pages(url, title, content, fetched_at)
      VALUES (?, ?, ?, ?)
    """, (url, title, content, datetime.utcnow().isoformat()))
    con.commit()

# ---- 본작업 ---------------------------------------------------------
def crawl():
    visited = set()
    q = deque(START_URLS)
    root = START_URLS[0]

    con = sqlite3.connect(DB_PATH)
    ensure_tables(con)

    saved = 0
    while q and saved < MAX_PAGES:
        url = q.popleft()
        if url in visited:
            continue
        if SAME_DOMAIN_ONLY and not same_domain(url, root):
            continue

        try:
            html = fetch(url)
        except Exception:
            # 실패한 페이지는 건너뜀
            continue

        visited.add(url)
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string.strip() if soup.title and soup.title.string else url)
        content = clean_text(html)
        if len(content) >= 50:
            save_page(con, url, title, content)
            saved += 1

        # 다음 링크 수집
        for a in soup.find_all("a", href=True):
            nxt = urljoin(url, a["href"])
            if nxt.startswith(("mailto:", "javascript:")):
                continue
            if nxt not in visited:
                q.append(nxt)

        # 서버 부하 방지
        time.sleep(REQUEST_GAP_SEC)

    con.close()
    print(f"[CRAWL DONE] saved_pages={saved}")

if __name__ == "__main__":
    crawl()

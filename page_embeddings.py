# page_embeddings.py
import os, sqlite3, json
from openai import OpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "school_data.db")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def build_embeddings():
    con = sqlite3.connect(DB_PATH)
    ensure_tables(con)
    cur = con.cursor()

    # 임베딩 없는 페이지 찾기
    cur.execute("""
      SELECT id, content FROM pages
      WHERE id NOT IN (SELECT page_id FROM page_embeddings)
    """)
    rows = cur.fetchall()

    for pid, content in rows:
        text = content[:2000]  # 길이 제한 (토큰 초과 방지)
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        ).data[0].embedding
        cur.execute("""
          INSERT OR REPLACE INTO page_embeddings(page_id, vector)
          VALUES (?, ?)
        """, (pid, json.dumps(emb)))
        con.commit()
        print(f"[EMBEDDED] page_id={pid}, len={len(text)}")

    con.close()

if __name__ == "__main__":
    build_embeddings()

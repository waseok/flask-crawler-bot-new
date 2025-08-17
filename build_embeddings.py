import os, csv, json, sqlite3, time, sys
from openai import OpenAI

DB_PATH = os.path.join(os.path.dirname(__file__), "school_data.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "qa_seed.csv")
MODEL = "text-embedding-3-small"
client = OpenAI()  # OPENAI_API_KEY는 Actions Secrets로

def ensure_tables(con):
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      question TEXT UNIQUE,
      answer TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_embeddings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      qa_id INTEGER UNIQUE,
      vector TEXT,
      FOREIGN KEY(qa_id) REFERENCES qa_data(id) ON DELETE CASCADE
    )""")
    con.commit()

def normalize_text(s: str) -> str:
    # 좌우 공백/특수공백 제거 + 내부 연속 공백 정리
    if s is None: return ""
    s = s.strip().replace("\u00A0", " ").replace("\u200b", "")
    return " ".join(s.split())

def upsert_qa(con, question, answer):
    """SELECT로 존재 확인 → UPDATE or INSERT. 항상 qa_id 반환."""
    q = normalize_text(question)
    a = normalize_text(answer)
    if not q or not a:
        return None

    cur = con.cursor()
    cur.execute("SELECT id, answer FROM qa_data WHERE question=?", (q,))
    row = cur.fetchone()
    if row:
        qa_id, old_answer = row[0], row[1] or ""
        if normalize_text(old_answer) != a:
            cur.execute("UPDATE qa_data SET answer=? WHERE id=?", (a, qa_id))
            con.commit()
        return qa_id
    else:
        cur.execute("INSERT INTO qa_data(question,answer) VALUES(?,?)", (q, a))
        con.commit()
        return cur.lastrowid

def embed(text: str) -> str:
    vec = client.embeddings.create(model=MODEL, input=text).data[0].embedding
    return json.dumps(vec)

def upsert_embedding(con, qa_id: int, vec_json: str):
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO qa_embeddings(qa_id, vector) VALUES(?,?)", (qa_id, vec_json))
    con.commit()

def main():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV not found: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    ensure_tables(con)

    added, updated, skipped = 0, 0, 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "question" not in reader.fieldnames or "answer" not in reader.fieldnames:
            print(f"[ERROR] CSV header must contain 'question,answer' (got {reader.fieldnames})", file=sys.stderr)
            sys.exit(1)

        for i, row in enumerate(reader, start=1):
            q_raw = row.get("question"); a_raw = row.get("answer")
            q = normalize_text(q_raw); a = normalize_text(a_raw)
            if not q or not a:
                skipped += 1
                continue

            # 업서트
            cur = con.cursor()
            cur.execute("SELECT id, answer FROM qa_data WHERE question=?", (q,))
            existed = cur.fetchone()
            qa_id = upsert_qa(con, q, a)
            if qa_id is None:
                skipped += 1
                continue

            # 임베딩
            try:
                vec_json = embed(q)  # 질문 텍스트 기준
                upsert_embedding(con, qa_id, vec_json)
            except Exception as e:
                print(f"[WARN] embed failed at row {i} question='{q[:30]}...' : {type(e).__name__}: {e}", file=sys.stderr)
                skipped += 1
                continue

            if existed:
                updated += 1
            else:
                added += 1

            # API rate 완화
            time.sleep(0.35)

    con.close()
    print(f"[OK] QA upsert done. added={added}, updated={updated}, skipped={skipped}")

if __name__ == "__main__":
    main()

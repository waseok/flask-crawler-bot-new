import os, csv, json, sqlite3, time
from openai import OpenAI

DB_PATH = os.path.join(os.path.dirname(__file__), "school_data.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "qa_seed.csv")

MODEL = "text-embedding-3-small"
client = OpenAI()  # OPENAI_API_KEY는 환경변수로

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

def upsert_qa(con, question, answer):
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO qa_data(question,answer) VALUES(?,?)", (question, answer))
    if cur.rowcount == 0:
        cur.execute("UPDATE qa_data SET answer=? WHERE question=?", (answer, question))
    con.commit()
    cur.execute("SELECT id FROM qa_data WHERE question=?", (question,))
    return cur.fetchone()[0]

def embed(text):
    vec = client.embeddings.create(model=MODEL, input=text).data[0].embedding
    return json.dumps(vec)

def upsert_embedding(con, qa_id, vec_json):
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO qa_embeddings(qa_id, vector) VALUES(?,?)", (qa_id, vec_json))
    con.commit()

def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    con = sqlite3.connect(DB_PATH)
    ensure_tables(con)

    added, updated = 0, 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = (row.get("question") or "").strip()
            a = (row.get("answer") or "").strip()
            if not q or not a:
                continue
            qa_id_before = None
            cur = con.cursor()
            cur.execute("SELECT id, answer FROM qa_data WHERE question=?", (q,))
            r = cur.fetchone()
            if r:
                qa_id_before, old_answer = r[0], r[1]
            qa_id = upsert_qa(con, q, a)
            vec_json = embed(q)  # 질문 기준 임베딩
            upsert_embedding(con, qa_id, vec_json)
            if qa_id_before:
                updated += 1
            else:
                added += 1
            time.sleep(0.4)  # API rate 완화

    con.close()
    print(f"QA upsert done. added={added}, updated={updated}")

if __name__ == "__main__":
    main()

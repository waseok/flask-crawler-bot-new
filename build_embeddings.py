import os, csv, json, sqlite3, time, sys
from openai import OpenAI

DB_PATH = os.path.join(os.path.dirname(__file__), "school_data.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "qa_seed.csv")
MODEL = "text-embedding-3-small"
client = OpenAI()  # OPENAI_API_KEY는 Actions Secrets/환경변수로

# ---------- 스키마 점검/마이그레이션 ----------
def pragma_table_info(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]  # column names

def ensure_and_migrate_schema(con):
    cur = con.cursor()
    # qa_data 테이블 생성(없으면)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      question TEXT UNIQUE,
      answer   TEXT
    )
    """)
    # qa_embeddings 테이블 생성(없으면)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_embeddings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      qa_id  INTEGER UNIQUE,
      vector TEXT,
      FOREIGN KEY(qa_id) REFERENCES qa_data(id) ON DELETE CASCADE
    )
    """)
    con.commit()

    # qa_data에 category 컬럼 없으면 추가 (기본값 '기타')
    cols = pragma_table_info(cur, "qa_data")
    if "category" not in cols:
        cur.execute("ALTER TABLE qa_data ADD COLUMN category TEXT DEFAULT '기타'")
        con.commit()
    # NULL 값이 있으면 기본값 채우기
    cur.execute("UPDATE qa_data SET category='기타' WHERE category IS NULL")
    con.commit()

# ---------- 텍스트 정규화 ----------
def normalize_text(s: str) -> str:
    if s is None: return ""
    s = s.strip().replace("\u00A0", " ").replace("\u200b", "")
    return " ".join(s.split())

# ---------- 업서트 ----------
def upsert_qa(con, question, answer, category):
    """question 고유. 있으면 answer/category 갱신, 없으면 추가. qa_id 반환"""
    q = normalize_text(question)
    a = normalize_text(answer)
    c = normalize_text(category) or "기타"
    if not q or not a:
        return None

    cur = con.cursor()
    cur.execute("SELECT id, answer, category FROM qa_data WHERE question=?", (q,))
    row = cur.fetchone()
    if row:
        qa_id, old_a, old_c = row[0], normalize_text(row[1] or ""), normalize_text(row[2] or "")
        if old_a != a or old_c != c:
            cur.execute("UPDATE qa_data SET answer=?, category=? WHERE id=?", (a, c, qa_id))
            con.commit()
        return qa_id
    else:
        cur.execute("INSERT INTO qa_data(question, answer, category) VALUES(?,?,?)", (q, a, c))
        con.commit()
        return cur.lastrowid

# ---------- 임베딩 ----------
def embed(text: str) -> str:
    vec = client.embeddings.create(model=MODEL, input=text).data[0].embedding
    return json.dumps(vec)

def upsert_embedding(con, qa_id: int, vec_json: str):
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO qa_embeddings(qa_id, vector) VALUES(?,?)", (qa_id, vec_json))
    con.commit()

# ---------- 메인 ----------
def main():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV not found: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    ensure_and_migrate_schema(con)

    added, updated, skipped = 0, 0, 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fns = [fn.lower() for fn in (reader.fieldnames or [])]
        if "question" not in fns or "answer" not in fns:
            print(f"[ERROR] CSV header must contain 'question,answer' (got {reader.fieldnames})", file=sys.stderr)
            sys.exit(1)

        # category 열은 선택(없으면 기본 '기타')
        has_cat = "category" in fns

        for i, row in enumerate(reader, start=1):
            # DictReader는 키 케이스를 보존하니 안전하게 get으로 접근
            q_raw = row.get("question") or row.get("Question") or row.get("질문")
            a_raw = row.get("answer")   or row.get("Answer")   or row.get("답변")
            c_raw = (row.get("category") or row.get("Category") or row.get("분류")) if has_cat else "기타"

            q = normalize_text(q_raw); a = normalize_text(a_raw); c = normalize_text(c_raw or "기타")
            if not q or not a:
                skipped += 1
                continue

            # 업서트 QA
            cur = con.cursor()
            cur.execute("SELECT id FROM qa_data WHERE question=?", (q,))
            existed = cur.fetchone() is not None

            qa_id = upsert_qa(con, q, a, c)
            if qa_id is None:
                skipped += 1
                continue

            # 임베딩(질문 기준)
            try:
                vec_json = embed(q)
                upsert_embedding(con, qa_id, vec_json)
            except Exception as e:
                print(f"[WARN] embed failed at row {i} q='{q[:30]}...': {type(e).__name__}: {e}", file=sys.stderr)
                skipped += 1
                continue

            if existed:
                updated += 1
            else:
                added += 1

            time.sleep(0.35)  # API rate 완화

    con.close()
    print(f"[OK] QA upsert done. added={added}, updated={updated}, skipped={skipped}")

if __name__ == "__main__":
    main()
import os, csv, json, sqlite3, time, sys
from openai import OpenAI

DB_PATH = os.path.join(os.path.dirname(__file__), "school_data.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "qa_seed.csv")
MODEL = "text-embedding-3-small"
client = OpenAI()  # OPENAI_API_KEY는 Actions Secrets/환경변수로

# ---------- 스키마 점검/마이그레이션 ----------
def pragma_table_info(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]  # column names

def ensure_and_migrate_schema(con):
    cur = con.cursor()
    # qa_data 테이블 생성(없으면)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      question TEXT UNIQUE,
      answer   TEXT
    )
    """)
    # qa_embeddings 테이블 생성(없으면)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_embeddings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      qa_id  INTEGER UNIQUE,
      vector TEXT,
      FOREIGN KEY(qa_id) REFERENCES qa_data(id) ON DELETE CASCADE
    )
    """)
    con.commit()

    # qa_data에 category 컬럼 없으면 추가 (기본값 '기타')
    cols = pragma_table_info(cur, "qa_data")
    if "category" not in cols:
        cur.execute("ALTER TABLE qa_data ADD COLUMN category TEXT DEFAULT '기타'")
        con.commit()
    # NULL 값이 있으면 기본값 채우기
    cur.execute("UPDATE qa_data SET category='기타' WHERE category IS NULL")
    con.commit()

# ---------- 텍스트 정규화 ----------
def normalize_text(s: str) -> str:
    if s is None: return ""
    s = s.strip().replace("\u00A0", " ").replace("\u200b", "")
    return " ".join(s.split())

# ---------- 업서트 ----------
def upsert_qa(con, question, answer, category):
    """question 고유. 있으면 answer/category 갱신, 없으면 추가. qa_id 반환"""
    q = normalize_text(question)
    a = normalize_text(answer)
    c = normalize_text(category) or "기타"
    if not q or not a:
        return None

    cur = con.cursor()
    cur.execute("SELECT id, answer, category FROM qa_data WHERE question=?", (q,))
    row = cur.fetchone()
    if row:
        qa_id, old_a, old_c = row[0], normalize_text(row[1] or ""), normalize_text(row[2] or "")
        if old_a != a or old_c != c:
            cur.execute("UPDATE qa_data SET answer=?, category=? WHERE id=?", (a, c, qa_id))
            con.commit()
        return qa_id
    else:
        cur.execute("INSERT INTO qa_data(question, answer, category) VALUES(?,?,?)", (q, a, c))
        con.commit()
        return cur.lastrowid

# ---------- 임베딩 ----------
def embed(text: str) -> str:
    vec = client.embeddings.create(model=MODEL, input=text).data[0].embedding
    return json.dumps(vec)

def upsert_embedding(con, qa_id: int, vec_json: str):
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO qa_embeddings(qa_id, vector) VALUES(?,?)", (qa_id, vec_json))
    con.commit()

# ---------- 메인 ----------
def main():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] CSV not found: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    ensure_and_migrate_schema(con)

    added, updated, skipped = 0, 0, 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fns = [fn.lower() for fn in (reader.fieldnames or [])]
        if "question" not in fns or "answer" not in fns:
            print(f"[ERROR] CSV header must contain 'question,answer' (got {reader.fieldnames})", file=sys.stderr)
            sys.exit(1)

        # category 열은 선택(없으면 기본 '기타')
        has_cat = "category" in fns

        for i, row in enumerate(reader, start=1):
            # DictReader는 키 케이스를 보존하니 안전하게 get으로 접근
            q_raw = row.get("question") or row.get("Question") or row.get("질문")
            a_raw = row.get("answer")   or row.get("Answer")   or row.get("답변")
            c_raw = (row.get("category") or row.get("Category") or row.get("분류")) if has_cat else "기타"

            q = normalize_text(q_raw); a = normalize_text(a_raw); c = normalize_text(c_raw or "기타")
            if not q or not a:
                skipped += 1
                continue

            # 업서트 QA
            cur = con.cursor()
            cur.execute("SELECT id FROM qa_data WHERE question=?", (q,))
            existed = cur.fetchone() is not None

            qa_id = upsert_qa(con, q, a, c)
            if qa_id is None:
                skipped += 1
                continue

            # 임베딩(질문 기준)
            try:
                vec_json = embed(q)
                upsert_embedding(con, qa_id, vec_json)
            except Exception as e:
                print(f"[WARN] embed failed at row {i} q='{q[:30]}...': {type(e).__name__}: {e}", file=sys.stderr)
                skipped += 1
                continue

            if existed:
                updated += 1
            else:
                added += 1

            time.sleep(0.35)  # API rate 완화

    con.close()
    print(f"[OK] QA upsert done. added={added}, updated={updated}, skipped={skipped}")

if __name__ == "__main__":
    main()

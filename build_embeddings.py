# build_embeddings.py
import os
import json
import time
import hashlib
import sqlite3
from datetime import datetime
from typing import List, Tuple

import numpy as np
from openai import OpenAI

# === 설정 ============================================================
MODEL = "text-embedding-3-small"  # 가볍고 저렴, 학교 챗봇 용도로 충분
BATCH_SIZE = 64                   # 질문이 아주 많을 때 배치 임베딩용(여기선 단건씩도 OK)
RETRY = 3                         # API 오류 시 재시도 횟수
SLEEP = 2                         # 재시도 간 대기(초)

# === 경로 ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "school_data.db")

# === OpenAI 클라이언트 ===============================================
# 환경변수 OPENAI_API_KEY 를 사용합니다.
# (예: mac/linux: export OPENAI_API_KEY='sk-xxx')
client = OpenAI()  # 별도 api_key 인자 없이 env에서 자동 인식

# === 유틸 ============================================================
def sha256_text(s: str) -> str:
    return hashlib.sha256((s or "").strip().lower().encode("utf-8")).hexdigest()

def embed_one(text: str) -> List[float]:
    # 단일 텍스트 임베딩
    for i in range(RETRY):
        try:
            resp = client.embeddings.create(model=MODEL, input=text)
            return resp.data[0].embedding
        except Exception as e:
            if i == RETRY - 1:
                raise
            time.sleep(SLEEP)

# === DB 작업 =========================================================
DDL = """
CREATE TABLE IF NOT EXISTS qa_embeddings (
  qa_id     INTEGER PRIMARY KEY,
  vector    TEXT NOT NULL,     -- JSON 배열로 저장
  text_hash TEXT NOT NULL,     -- 질문 텍스트 해시(변경 감지)
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(qa_id) REFERENCES qa_data(id)
);
"""

def fetch_qa_rows(conn) -> List[Tuple[int, str]]:
    cur = conn.cursor()
    return cur.execute("SELECT id, question FROM qa_data").fetchall()

def get_existing_hash(conn, qa_id: int) -> str:
    cur = conn.cursor()
    row = cur.execute("SELECT text_hash FROM qa_embeddings WHERE qa_id=?", (qa_id,)).fetchone()
    return row[0] if row else None

def upsert_embedding(conn, qa_id: int, vector, text_hash: str):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO qa_embeddings (qa_id, vector, text_hash, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(qa_id) DO UPDATE SET
          vector=excluded.vector,
          text_hash=excluded.text_hash,
          updated_at=excluded.updated_at
        """,
        (qa_id, json.dumps(vector), text_hash, datetime.utcnow().isoformat())
    )
    conn.commit()

def main():
    print(f"[INFO] Using DB: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(DDL)
    conn.commit()

    rows = fetch_qa_rows(conn)
    print(f"[INFO] qa_data rows: {len(rows)}")

    created, updated, skipped = 0, 0, 0
    for qa_id, question in rows:
        q = (question or "").strip()
        if not q:
            skipped += 1
            continue

        new_hash = sha256_text(q)
        old_hash = get_existing_hash(conn, qa_id)

        if old_hash == new_hash:
            skipped += 1
            continue

        vec = embed_one(q)
        upsert_embedding(conn, qa_id, vec, new_hash)
        if old_hash is None:
            created += 1
        else:
            updated += 1

    conn.close()
    print(f"[DONE] created: {created}, updated: {updated}, skipped(no change/empty): {skipped}")

if __name__ == "__main__":
    # 키가 없으면 친절히 에러 안내
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError(
            "환경변수 OPENAI_API_KEY가 설정되지 않았습니다. "
            "아래 2단계 안내를 보고 먼저 키를 등록하세요."
        )
    main()

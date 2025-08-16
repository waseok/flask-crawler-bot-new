import os
import json
import sqlite3
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from flask import Flask, request, jsonify
from openai import OpenAI

# database.py 에서 DatabaseManager, db_diagnostics 가져오기
from database import DatabaseManager, db_diagnostics

app = Flask(__name__)

# -----------------------------
# OpenAI API (환경변수 OPENAI_API_KEY 필요)
# -----------------------------
client = OpenAI()

# -----------------------------
# 퀵리플라이 (고정)
# -----------------------------
QUICK_REPLIES = [
    {"label": "📅 학사일정",             "action": "message", "messageText": "📅 학사일정"},
    {"label": "📋 늘봄/방과후",          "action": "message", "messageText": "📋 늘봄/방과후"},
    {"label": "📖 수업시간/시정표(초등)", "action": "message", "messageText": "📖 수업시간/시정표(초등)"},
    {"label": "📚 교과서",               "action": "message", "messageText": "📚 교과서"},
    {"label": "🏠 전입/전출",            "action": "message", "messageText": "🏠 전입/전출"},
    {"label": "📋 증명서/서류",          "action": "message", "messageText": "📋 증명서/서류"},
    {"label": "📞 연락처/상담",          "action": "message", "messageText": "📞 연락처/상담"},
    {"label": "🍽️ 급식",                "action": "message", "messageText": "🍽️ 급식"},
    {"label": "🎶 기타",                 "action": "message", "messageText": "🎶 기타"},
    {"label": "🧸 유치원",               "action": "message", "messageText": "🧸 유치원"},
]

# -----------------------------
# 유사도/임베딩 유틸
# -----------------------------
def _cos(a, b):
    a = np.array(a); b = np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def _embed_query(text: str):
    return client.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding

# -----------------------------
# /health 엔드포인트
# -----------------------------
@app.get("/health")
def health():
    diag = db_diagnostics()
    connected = (diag.get("exists") and diag.get("integrity") == "ok")
    return jsonify({
        "status": "healthy",
        "database": "connected" if connected else "disconnected",
        "diag": diag
    }), 200

# -----------------------------
# 기본 QA 스킬
# -----------------------------
@app.post("/")
def main_skill():
    body = request.get_json()
    user_text = body.get("userRequest", {}).get("utterance", "")

    # DB에서 QA 불러오기
    db = DatabaseManager()
    qa_list = db.get_qa_data()

    # 임베딩 검색
    q_emb = _embed_query(user_text)
    scored = []
    for q, a, emb in qa_list:
        try:
            emb = json.loads(emb)
            score = _cos(q_emb, emb)
            scored.append((score, q, a))
        except Exception:
            continue

    scored.sort(reverse=True, key=lambda x: x[0])
    best = scored[0] if scored else None

    if best and best[0] >= 0.75:
        answer = best[2]
    else:
        # 답변이 없으면 link_reco로 포워딩
        return link_reco_internal(user_text)

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {"text": answer}
            }],
            "quickReplies": QUICK_REPLIES
        }
    })

# -----------------------------
# 링크 추천 스킬 (/link_reco)
# -----------------------------
@app.post("/link_reco")
def link_reco():
    body = request.get_json()
    user_text = body.get("userRequest", {}).get("utterance", "")
    return link_reco_internal(user_text)

def link_reco_internal(user_text: str):
    db_path = os.path.join(os.path.dirname(__file__), "school_data.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT url, title, content, embedding FROM pages")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return ("", 204)

    q_emb = _embed_query(user_text)
    candidates = []
    for url, title, content, emb in rows:
        try:
            emb = json.loads(emb)
            score = _cos(q_emb, emb)
            candidates.append((score, title, url, content))
        except Exception:
            continue

    candidates.sort(reverse=True, key=lambda x: x[0])

    # 임계값 필터링
    GOOD = [c for c in candidates if c[0] >= 0.70]

    # URL 정규화 & 중복 제거
    def _normalize_url(u):
        s = urlsplit(u)
        return urlunsplit((s.scheme, s.netloc, s.path, "", ""))

    seen = set()
    dedup = []
    for score, title, url, content in GOOD:
        key = _normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        dedup.append((score, title, url, content))

    GOOD = dedup[:5]  # 최대 5개만

    if not GOOD:
        return ("", 204)

    items = []
    for score, title, url, content in GOOD:
        snippet = (content or "").strip().replace("\n", " ")[:80]
        items.append({
            "title": title[:50] if title else url,
            "description": snippet if snippet else f"관련도 {score:.2f}",
            "link": {"web": url}
        })

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "listCard": {
                    "header": {"title": "가장 관련있는 학교 홈페이지 안내"},
                    "items": items
                }
            }],
            "quickReplies": QUICK_REPLIES
        }
    })

# -----------------------------
# 앱 실행 (로컬)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

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
    try:
        diag = db_diagnostics()
    except Exception as e:
        # db_diagnostics 자체가 실패해도 200으로 내려주고 원인을 JSON에 담음
        diag = {"error": f"{type(e).__name__}: {e}"}

    connected = bool(diag.get("exists")) and diag.get("integrity") == "ok"
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
    # 어떤 에러가 나도 500 터지지 않게 전역 가드
    try:
        body = request.get_json(silent=True) or {}
        utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    except Exception as e:
        utter = ""

    # 1) QA 포함/정확 매칭 → 2) 임베딩 매칭
    answer = None
    try:
        if db is not None and utter:
            # (1) 포함/정확 매칭
            try:
                rows = db.get_qa_data()
                for r in rows:
                    q = (r.get("question") or "").strip()
                    if q and (utter in q or q in utter):
                        answer = (r.get("answer") or "").strip()
                        break
            except Exception as e:
                app.logger.error(f"[DB QUERY ERROR] {type(e).__name__}: {e}")

            # (2) 임베딩 매칭
            if not answer:
                try:
                    answer = semantic_answer(utter, db.db_path, threshold=0.75)
                except Exception as e:
                    app.logger.error(f"[SEMANTIC ERROR] {type(e).__name__}: {e}")
    except Exception as e:
        app.logger.error(f"[MAIN QA BLOCK ERROR] {type(e).__name__}: {e}")

    # 3) QA가 없으면 링크추천으로 위임 (이 엔드포인트가 200이면 카드, 204면 폴백 처리)
    if not answer and utter:
        try:
            return link_reco_internal(utter)  # 200(listCard) 또는 204(No Content)
        except Exception as e:
            app.logger.error(f"[LINK RECO DELEGATE ERROR] {type(e).__name__}: {e}")

    # 4) 최종 폴백(텍스트)
    if not answer:
        answer = (
            "원하시는 정보를 정확히 찾지 못했어요.\n"
            "아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂"
        )

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": answer}}],
            "quickReplies": QUICK_REPLIES
        }
    }), 200


# -----------------------------
# 앱 실행 (로컬)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

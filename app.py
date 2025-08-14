# app.py
import os
import json
import sqlite3
import numpy as np
from flask import Flask, request, jsonify
from openai import OpenAI

# 우리 프로젝트의 DB 유틸
from database import DatabaseManager, db_diagnostics  # database.py에 있어야 함

app = Flask(__name__)

# === OpenAI (환경변수 OPENAI_API_KEY 사용) ===
client = OpenAI()

# === 임베딩 유틸 ===
def _cos(a, b):
    a = np.array(a); b = np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def _embed_query(text: str):
    return client.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding

def semantic_answer(utter: str, db_path: str, threshold: float = 0.75):
    """
    qa_embeddings 테이블의 벡터와 비교해 가장 유사한 qa_data.answer 반환.
    threshold 이상일 때만 채택.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
      SELECT qa_data.id, qa_data.question, qa_data.answer, qa_embeddings.vector
      FROM qa_data
      JOIN qa_embeddings ON qa_embeddings.qa_id = qa_data.id
    """)
    rows = cur.fetchall()
    con.close()
    if not rows:
        return None

    uvec = _embed_query(utter)
    best_ans, best_s = None, -1.0
    for qa_id, q, a, vjson in rows:
        try:
            v = json.loads(vjson)
            s = _cos(uvec, v)
            if s > best_s:
                best_ans, best_s = a, s
        except Exception:
            continue

    # 디버깅용 로그: 최고 유사도 점수 확인
    app.logger.info(f"[SEMANTIC] utter='{utter}' best_score={best_s:.3f} threshold={threshold}")
    return best_ans if best_s >= threshold else None


# === DB 매니저 초기화 (실패해도 앱은 떠 있게) ===
try:
    db = DatabaseManager()   # database.py에서 절대경로로 school_data.db 참조
except Exception as e:
    db = None
    app.logger.error(f"[DB INIT ERROR] {type(e).__name__}: {e}")


# === /health: 진단 정보 노출 (500 방지) ===
@app.route("/health", methods=["GET"])
def health():
    try:
        diag = db_diagnostics()
    except Exception as e:
        diag = {"error": f"db_diagnostics error: {type(e).__name__}: {e}"}

    connected = bool(diag.get("exists")) and diag.get("integrity") == "ok"
    return jsonify({
        "status": "healthy",
        "database": "connected" if connected else "disconnected",
        "diag": diag
    }), 200


# === 루트 GET: 간단 핑 ===
@app.route("/", methods=["GET"])
def index():
    return jsonify({"ok": True, "message": "Flask server is running"}), 200


# === 카카오 오픈빌더 스킬 엔드포인트 ===
@app.route("/", methods=["POST"])
def kakao_skill():
    # 요청 파싱
    try:
        body = request.get_json(silent=True) or {}
        utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    except Exception:
        utter = ""

    answer = None

    # 1) DB에서 정확/포함 매칭 (가벼운 1차 매칭)
    if db is not None and utter:
        try:
            rows = db.get_qa_data()
            for r in rows:
                q = (r.get("question") or "").strip()
                if q and (utter in q or q in utter):
                    answer = (r.get("answer") or "").strip()
                    break
        except Exception as e:
            app.logger.error(f"[DB QUERY ERROR] {type(e).__name__}: {e}")

    # 2) 임베딩 유사도 검색 (못 찾았을 때)
    if not answer and utter:
        try:
            answer = semantic_answer(utter, db.db_path, threshold=0.75)
        except Exception as e:
            app.logger.error(f"[SEMANTIC ERROR] {type(e).__name__}: {e}")

    # 3) 폴백 응답
    if not answer:
        if utter:
            answer = (
                "원하시는 정보를 정확히 찾지 못했어요.\n"
                "아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂"
            )
        else:
            answer = "무엇을 도와드릴까요? 🙂"

    # 4) 🔒 퀵리플라이: 사용자 고정 목록 (절대 수정하지 않음)
    quick_replies = [
        {"label": "📅 학사일정",           "action": "message", "messageText": "📅 학사일정"},
        {"label": "📋 늘봄/방과후",        "action": "message", "messageText": "📋 늘봄/방과후"},
        {"label": "📖 수업시간/시정표(초등)", "action": "message", "messageText": "📖 수업시간/시정표(초등)"},
        {"label": "📚 교과서",             "action": "message", "messageText": "📚 교과서"},
        {"label": "🏠 전입/전출",          "action": "message", "messageText": "🏠 전입/전출"},
        {"label": "📋 증명서/서류",        "action": "message", "messageText": "📋 증명서/서류"},
        {"label": "📞 연락처/상담",        "action": "message", "messageText": "📞 연락처/상담"},
        {"label": "🍽️ 급식",              "action": "message", "messageText": "🍽️ 급식"},
        {"label": "🎶 기타",               "action": "message", "messageText": "🎶 기타"},
        {"label": "🧸 유치원",             "action": "message", "messageText": "🧸 유치원"},
    ]

    # 카카오 응답 포맷
    response = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": answer}}],
            "quickReplies": quick_replies
        }
    }
    return jsonify(response), 200


# === 로컬 실행용 ===
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

import os
import sqlite3
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "school_data.db"

# -----------------------------
# 유틸 함수
# -----------------------------
def get_db_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def search_qa(user_text, top_k=3):
    """qa_data 테이블에서 단순 키워드 검색"""
    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id, question, answer, category FROM qa_data WHERE question LIKE ? ORDER BY id LIMIT ?",
        (f"%{user_text}%", top_k),
    )
    rows = cur.fetchall()
    con.close()
    return rows

# -----------------------------
# 기본 엔드포인트 (/)
# -----------------------------
@app.route("/", methods=["POST"])
def kakao_skill():
    data = request.get_json()
    user_text = data.get("userRequest", {}).get("utterance", "").strip()
    print(f"[DEBUG] utterance={user_text}")

    # 🔹 2-a: 환경변수 기반 답변 제어
    budget_ms = int(os.getenv("KAKAO_BUDGET_MS", "2000"))
    disable_link_reco = os.getenv("DISABLE_LINK_RECO", "0") == "1"

    # DB 검색
    results = search_qa(user_text, top_k=3)

    if results:
        top = results[0]
        text = top["answer"]
    else:
        # 🔹 2-b: 기본 답변 개선
        if disable_link_reco:
            text = (
                "원하시는 정보를 정확히 찾지 못했어요.\n"
                "아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂"
            )
        else:
            text = (
                "원하시는 정보를 찾지 못했어요.\n"
                "학교 홈페이지 주요 메뉴에서 확인해보시길 권장드려요."
            )

    response = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}],
            "quickReplies": [
                {"action": "message", "label": "📅 학사일정", "messageText": "📅 학사일정"},
                {"action": "message", "label": "📋 늘봄/방과후", "messageText": "📋 늘봄/방과후"},
                {"action": "message", "label": "📖 수업시간/시정표(초등)", "messageText": "📖 수업시간/시정표(초등)"},
                {"action": "message", "label": "📚 교과서", "messageText": "📚 교과서"},
                {"action": "message", "label": "🏠 전입/전출", "messageText": "🏠 전입/전출"},
                {"action": "message", "label": "📋 증명서/서류", "messageText": "📋 증명서/서류"},
                {"action": "message", "label": "📞 연락처/상담", "messageText": "📞 연락처/상담"},
                {"action": "message", "label": "🍽️ 급식", "messageText": "🍽️ 급식"},
                {"action": "message", "label": "🎶 기타", "messageText": "🎶 기타"},
                {"action": "message", "label": "🧸 유치원", "messageText": "🧸 유치원"},
            ],
        },
    }
    return jsonify(response)


# -----------------------------
# /link_reco (홈페이지 링크 추천)
# -----------------------------
@app.route("/link_reco", methods=["POST"])
def link_reco():
    data = request.get_json()
    user_text = data.get("userRequest", {}).get("utterance", "").strip()
    print(f"[DEBUG] link_reco utterance={user_text}")

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT url, title, snippet, score FROM web_data ORDER BY score DESC LIMIT 1"
    )
    row = cur.fetchone()
    con.close()

    if row:
        items = [
            {
                "title": row["title"],
                "description": f"{row['snippet']} · 관련도 {row['score']:.2f}",
                "link": {"web": row["url"]},
            }
        ]
        response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "listCard": {
                            "header": {"title": "가장 관련있는 학교 홈페이지 안내"},
                            "items": items,
                        }
                    }
                ],
                "quickReplies": [
                    {"action": "message", "label": "📅 학사일정", "messageText": "📅 학사일정"},
                    {"action": "message", "label": "📋 늘봄/방과후", "messageText": "📋 늘봄/방과후"},
                    {"action": "message", "label": "📖 수업시간/시정표(초등)", "messageText": "📖 수업시간/시정표(초등)"},
                    {"action": "message", "label": "📚 교과서", "messageText": "📚 교과서"},
                    {"action": "message", "label": "🏠 전입/전출", "messageText": "🏠 전입/전출"},
                    {"action": "message", "label": "📋 증명서/서류", "messageText": "📋 증명서/서류"},
                    {"action": "message", "label": "📞 연락처/상담", "messageText": "📞 연락처/상담"},
                    {"action": "message", "label": "🍽️ 급식", "messageText": "🍽️ 급식"},
                    {"action": "message", "label": "🎶 기타", "messageText": "🎶 기타"},
                    {"action": "message", "label": "🧸 유치원", "messageText": "🧸 유치원"},
                ],
            },
        }
    else:
        response = {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "관련 링크를 찾을 수 없어요."}}],
            },
        }

    return jsonify(response)


# -----------------------------
# /health (상태 확인)
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    exists = os.path.exists(DB_PATH)
    diag = {"exists": exists}
    if exists:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("PRAGMA integrity_check;")
        diag["integrity"] = cur.fetchone()[0]
        diag["path"] = os.path.abspath(DB_PATH)
        diag["size"] = os.path.getsize(DB_PATH)
        con.close()

    return jsonify({"status": "healthy" if exists else "no-db", "database": "connected" if exists else "missing", "diag": diag})


# -----------------------------
# 실행
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

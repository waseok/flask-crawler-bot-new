import os
import sqlite3
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "school_data.db"

# -----------------------------
# 공통 Quick Replies (고정)
# -----------------------------
QUICK_REPLIES = [
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
]

# -----------------------------
# 공통 헬퍼: 항상 200 JSON 보장
# -----------------------------
def _kakao_ok(text: str):
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}],
            "quickReplies": QUICK_REPLIES
        }
    }), 200

# -----------------------------
# DB 유틸
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
# 기본 엔드포인트 (QA 기본) — 절대 안 망가지게 방어
# -----------------------------
@app.post("/")
def kakao_skill():
    data = request.get_json(silent=True) or {}
    user_text = (data.get("userRequest", {}) or {}).get("utterance", "")
    user_text = (user_text or "").strip()
    print(f"[DEBUG] utterance={user_text}")

    # 환경변수 (필요시 제어)
    budget_ms = int(os.getenv("KAKAO_BUDGET_MS", "2000"))
    disable_link_reco = os.getenv("DISABLE_LINK_RECO", "0") == "1"

    # 빈 본문/발화도 항상 200
    if not user_text:
        return _kakao_ok("무엇을 도와드릴까요? 아래 메뉴를 눌러주세요 🙂")

    # DB 검색
    try:
        results = search_qa(user_text, top_k=3)
    except Exception as e:
        print(f"[ERROR][QA] {type(e).__name__}: {e}")
        results = []

    if results:
        top = results[0]
        text = top["answer"]
    else:
        # 기본 답변(안전 폴백)
        if disable_link_reco:
            text = ("원하시는 정보를 정확히 찾지 못했어요.\n"
                    "아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂")
        else:
            text = ("원하시는 정보를 찾지 못했어요.\n"
                    "학교 홈페이지 주요 메뉴에서 확인해보시길 권장드려요.")

    return _kakao_ok(text)

# -----------------------------
# /link_reco (홈페이지 링크 추천) — 항상 200 JSON
# -----------------------------
@app.post("/link_reco")
def link_reco():
    data = request.get_json(silent=True) or {}
    user_text = (data.get("userRequest", {}) or {}).get("utterance")
    user_text = (user_text or "").strip()
    print(f"[DEBUG] link_reco utterance={user_text}")

    # ① 본문/발화 없음 → 오픈빌더 ‘테스트’ 대비 즉시 200
    if not user_text:
        return _kakao_ok("스킬 서버 연결 확인: OK")

    # ② DB에서 추천(간단 버전: 점수 상위 3개)
    try:
        con = get_db_connection()
        cur = con.cursor()
        # user_text를 활용한 간단 필터(가능하면 LIKE로 1차 필터)
        cur.execute("""
            SELECT url, title, snippet, score
            FROM web_data
            WHERE (title LIKE ? OR snippet LIKE ?)
            ORDER BY score DESC
            LIMIT 3
        """, (f"%{user_text}%", f"%{user_text}%"))
        rows = cur.fetchall()
        # 필터로 안 잡히면 전체 상위 3개라도
        if not rows:
            cur.execute("SELECT url, title, snippet, score FROM web_data ORDER BY score DESC LIMIT 3")
            rows = cur.fetchall()
        con.close()
    except Exception as e:
        print(f"[ERROR][LINK_RECO] {type(e).__name__}: {e}")
        rows = []

    # ③ 후보 없으면 200 텍스트 폴백
    if not rows:
        return _kakao_ok(f"‘{user_text}’ 관련 링크를 찾지 못했어요. 다른 키워드로 시도해 주세요 🙂")

    # ④ listCard 구성 (최대 3개)
    items = []
    for r in rows:
        items.append({
            "title": r["title"],
            "description": f"{(r['snippet'] or '').strip()} · 관련도 {float(r['score']):.2f}",
            "link": {"web": r["url"]},
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
    }), 200

# -----------------------------
# /kakao_echo (진단용)
# -----------------------------
@app.post("/kakao_echo")
def kakao_echo():
    body = request.get_json(silent=True) or {}
    utter = (body.get("userRequest", {}) or {}).get("utterance")
    return jsonify({
        "version":"2.0",
        "template":{"outputs":[{"simpleText":{"text":f"받은 키: {list(body.keys())}, utterance: {utter}"}}]}
    }), 200

# -----------------------------
# /health (상태 확인)
# -----------------------------
@app.get("/health")
def health():
    exists = os.path.exists(DB_PATH)
    diag = {"exists": exists}
    if exists:
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute("PRAGMA integrity_check;")
            diag["integrity"] = cur.fetchone()[0]
            diag["path"] = os.path.abspath(DB_PATH)
            diag["size"] = os.path.getsize(DB_PATH)
            con.close()
        except Exception as e:
            diag["error"] = f"{type(e).__name__}: {e}"

    return jsonify({
        "status": "healthy" if exists else "no-db",
        "database": "connected" if exists else "missing",
        "diag": diag
    }), 200

# -----------------------------
# 전역 에러 핸들러: 어떤 예외도 200 JSON 폴백
# -----------------------------
@app.errorhandler(Exception)
def handle_any_error(e):
    # 서버 에러가 나도 카카오에 200 + simpleText 보장
    return _kakao_ok("잠시 응답이 지연되었어요. 다시 한번 물어봐 주세요 🙂")

# -----------------------------
# 로컬 실행
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

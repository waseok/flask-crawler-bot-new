import os
import re
import sqlite3
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
# OpenAI는 향후 확장용(지금 로직엔 필수 아님)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "school_data.db"

# ------------------------------------------------------
# 고정 Quick Replies (수정 금지)
# ------------------------------------------------------
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

# 공지/가정통신문 보너스 단어 (환경변수로 커스터마이즈 가능)
BOARD_BONUS_WORDS = os.getenv(
    "BOARD_BONUS_WORDS", "가정통신문,공지,알림,notice,안내,보건"
).split(",")

# ------------------------------------------------------
# 공통 헬퍼 (항상 200 JSON 보장)
# ------------------------------------------------------
def _kakao_ok(text: str):
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}],
            "quickReplies": QUICK_REPLIES
        }
    }), 200

# ------------------------------------------------------
# DB 유틸
# ------------------------------------------------------
def get_db_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def search_qa(user_text: str, top_k: int = 3):
    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id, question, answer, category "
        "FROM qa_data "
        "WHERE question LIKE ? "
        "ORDER BY id LIMIT ?",
        (f"%{user_text}%", top_k),
    )
    rows = cur.fetchall()
    con.close()
    return rows

# ------------------------------------------------------
# 기본 QA 엔드포인트 (절대 깨지지 않게 방어)
# ------------------------------------------------------
@app.post("/")
def kakao_skill():
    data = request.get_json(silent=True) or {}
    user_text = (data.get("userRequest", {}) or {}).get("utterance", "")
    user_text = (user_text or "").strip()
    print(f"[DEBUG] utterance={user_text}")

    # 비어도 항상 200
    if not user_text:
        return _kakao_ok("무엇을 도와드릴까요? 아래 메뉴를 눌러주세요 🙂")

    # DB 검색 (키워드형)
    try:
        results = search_qa(user_text, top_k=3)
    except Exception as e:
        print(f"[ERROR][QA] {type(e).__name__}: {e}")
        results = []

    if results:
        top = results[0]
        text = top["answer"]
    else:
        text = (
            "원하시는 정보를 정확히 찾지 못했어요.\n"
            "아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂"
        )

    return _kakao_ok(text)

# ------------------------------------------------------
# 텀 추출 (LIKE 검색용)
# ------------------------------------------------------
def _extract_terms(text: str):
    """한/영/숫자 토큰 중 2글자 이상만 중복 제거하여 사용"""
    if not text:
        return []
    toks = re.split(r"[^\w가-힣]+", text.strip())
    seen, out = set(), []
    for t in toks:
        if len(t) >= 2 and t not in seen:
            seen.add(t)
            out.append(t)
    return out or [text.strip()]

# ------------------------------------------------------
# 링크 추천 (LIKE + 가중치) — 항상 200 JSON
# ------------------------------------------------------
@app.post("/link_reco")
def link_reco():
    data = request.get_json(silent=True) or {}
    user_text = (data.get("userRequest", {}) or {}).get("utterance")
    user_text = (user_text or "").strip()
    print(f"[DEBUG] link_reco utterance={user_text}")

    # 테스트/검증: 본문 없을 때도 200
    if not user_text:
        return _kakao_ok("스킬 서버 연결 확인: OK")

    terms = _extract_terms(user_text)  # 예: ["감염병"]
    if not terms:
        return _kakao_ok(f"‘{user_text}’ 관련 링크를 찾지 못했어요. 다른 키워드로 시도해 주세요 🙂")

    # WHERE (title LIKE ? OR snippet LIKE ?) OR ... (발화 토큰별)
    where_blocks = ["(title LIKE ? OR snippet LIKE ?)"] * len(terms)
    where_clause = " OR ".join(where_blocks)
    like_params = []
    for t in terms:
        like_params.extend([f"%{t}%", f"%{t}%"])

    # 키워드 가중치: 제목 매칭 +2, 스니펫 매칭 +1 (토큰별 합산)
    kw_score_parts = []
    kw_params = []
    for t in terms:
        kw_score_parts.append("CASE WHEN instr(title, ?) > 0 THEN 2 ELSE 0 END")
        kw_score_parts.append("CASE WHEN instr(snippet, ?) > 0 THEN 1 ELSE 0 END")
        kw_params.extend([t, t])

    # 게시판/공지 보너스: 제목 또는 URL에 특정 단어 포함 시 +0.5
    board_bonus_cond = " OR ".join([f"title LIKE ? OR url LIKE ?" for _ in BOARD_BONUS_WORDS])
    board_params = []
    for w in BOARD_BONUS_WORDS:
        board_params.extend([f"%{w}%", f"%{w}%"])

    sql = f"""
        SELECT url, title, snippet, score,
               (
                 {" + ".join(kw_score_parts)}
                 + 0.5 * CASE WHEN ({board_bonus_cond}) THEN 1 ELSE 0 END
               ) AS rel
        FROM web_data
        WHERE {where_clause}
        ORDER BY rel DESC, score DESC
        LIMIT 3
    """

    # 질의 & 결과
    rows = []
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute(sql, tuple(kw_params + board_params + like_params))
        rows = cur.fetchall()
        con.close()
    except Exception as e:
        print(f"[ERROR][LINK_RECO LIKE] {type(e).__name__}: {e}")
        rows = []

    # 후보 없으면 폴백 텍스트
    if not rows:
        return _kakao_ok(f"‘{user_text}’ 관련 링크를 찾지 못했어요. 다른 키워드로 시도해 주세요 🙂")

    # listCard 구성 (최대 3개)
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
                    "header": {"title": f"‘{user_text}’ 관련 안내"},
                    "items": items
                }
            }],
            "quickReplies": QUICK_REPLIES
        }
    }), 200

# ------------------------------------------------------
# 진단용 에코
# ------------------------------------------------------
@app.post("/kakao_echo")
def kakao_echo():
    body = request.get_json(silent=True) or {}
    utter = (body.get("userRequest", {}) or {}).get("utterance")
    return jsonify({
        "version":"2.0",
        "template":{"outputs":[{"simpleText":{"text":f"받은 키: {list(body.keys())}, utterance: {utter}"}}]}
    }), 200

# ------------------------------------------------------
# 헬스체크
# ------------------------------------------------------
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

# ------------------------------------------------------
# 전역 에러 핸들러 (혹시 모를 예외도 200 폴백)
# ------------------------------------------------------
@app.errorhandler(Exception)
def handle_any_error(e):
    print(f"[UNCAUGHT] {type(e).__name__}: {e}")
    return _kakao_ok("잠시 응답이 지연되었어요. 다시 한번 물어봐 주세요 🙂")

# ------------------------------------------------------
# 로컬 실행
# ------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

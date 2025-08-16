import os
import json
import sqlite3
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from flask import Flask, request, jsonify
from openai import OpenAI

# 프로젝트 내 DB 유틸 (database.py)
from database import DatabaseManager, db_diagnostics  # database.py에 있어야 함

app = Flask(__name__)

# -----------------------------
# OpenAI (환경변수 OPENAI_API_KEY 사용)
# -----------------------------
client = OpenAI()  # api_key는 환경변수에서 자동으로 읽힘

# -----------------------------
# 퀵리플라이: 전역 상수(절대 수정 금지 요청 반영)
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
# 임베딩/유사도 유틸
# -----------------------------
def _cos(a, b):
    a = np.array(a); b = np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def _embed_query(text: str):
    return client.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding

def semantic_answer(utter: str, db_path: str, threshold: float = 0.75):
    """
    qa_embeddings 테이블 벡터와 비교해 가장 유사한 qa_data.answer 반환.
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

    app.logger.info(f"[SEMANTIC] utter='{utter}' best_score={best_s:.3f} threshold={threshold}")
    return best_ans if best_s >= threshold else None

# -----------------------------
# 링크 추천용 헬퍼
# -----------------------------
def _normalize_url(u: str) -> str:
    """쿼리/해시 제거해서 중복 URL 합치기"""
    s = urlsplit(u or "")
    return urlunsplit((s.scheme, s.netloc, s.path, "", ""))

def _make_snippet(content: str, keywords: list[str], width: int = 90) -> str:
    """본문에서 키워드 주변을 잘라 한 줄 스니펫 생성"""
    if not content:
        return ""
    text = content.replace("\n", " ").replace("\r", " ")
    for kw in [k for k in keywords if k and len(k) >= 2]:
        idx = text.find(kw)
        if idx != -1:
            start = max(0, idx - width//2)
            end = min(len(text), idx + len(kw) + width//2)
            return text[start:end].strip()
    return text[:width].strip()

def _title_overlap_boost(title: str, url: str, keywords: list[str]) -> float:
    """제목/URL에 키워드가 있으면 가중치(최대 +0.10)"""
    if not keywords:
        return 0.0
    hay = f"{title or ''} {url or ''}".lower()
    hits = sum(1 for k in keywords if k and len(k) >= 2 and k.lower() in hay)
    return min(0.10, 0.03 * hits)  # 1개 +0.03, 2개 +0.06, 3개 이상 +0.10

# -----------------------------
# DB 매니저 초기화(실패해도 앱은 뜸)
# -----------------------------
try:
    db = DatabaseManager()   # database.py에서 절대경로로 school_data.db 참조
except Exception as e:
    db = None
    app.logger.error(f"[DB INIT ERROR] {type(e).__name__}: {e}")

# -----------------------------
# /health: 진단
# -----------------------------
@app.get("/health")
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

# -----------------------------
# GET 루트 핑
# -----------------------------
@app.get("/")
def index():
    return jsonify({"ok": True, "message": "Flask server is running"}), 200

# -----------------------------
# 카카오 오픈빌더 메인 스킬(기존 폴백 흐름 유지)
# -----------------------------
@app.post("/")
def kakao_skill():
    # 요청 파싱
    try:
        body = request.get_json(silent=True) or {}
        utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    except Exception:
        utter = ""

    answer = None

    # 1) DB에서 가벼운 포함/정확 매칭
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

    # 2) 임베딩 유사도 매칭
    if not answer and utter:
        try:
            answer = semantic_answer(utter, db.db_path, threshold=0.75)
        except Exception as e:
            app.logger.error(f"[SEMANTIC ERROR] {type(e).__name__}: {e}")

    # 3) 폴백 메시지
    if not answer:
        if utter:
            answer = (
                "원하시는 정보를 정확히 찾지 못했어요.\n"
                "아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂"
            )
        else:
            answer = "무엇을 도와드릴까요? 🙂"

    response = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": answer}}],
            "quickReplies": QUICK_REPLIES
        }
    }
    return jsonify(response), 200

# -----------------------------
# 링크 추천 전용 스킬: /link_reco
# (오픈빌더에서 별도 스킬로 연결. 실패 시 폴백으로 돌아가게 204 사용)
# -----------------------------
@app.get("/link_reco")
def link_reco_ping():
    return jsonify({"ok": True, "hint": "POST JSON required"}), 200

@app.post("/link_reco")
def link_reco():
    body = request.get_json(silent=True) or {}
    utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    if not utter or db is None:
        return ("", 204)

    # 간단 키워드 추출(조사/종결어 제거)
    stopwords = ["안내", "해주세요", "해줘", "알려줘", "알려주세요",
                 "인가요", "있나요", "어디", "어떻게", "요", "좀",
                 "을", "를", "은", "는", "이", "가", "에", "로", "에서", "에게"]
    raw_tokens = utter.replace("/", " ").split()
    keywords = [t for t in raw_tokens if t not in stopwords]

    try:
        # 1) 페이지 + 임베딩 로드
        con = sqlite3.connect(db.db_path)
        cur = con.cursor()
        cur.execute("""
          SELECT pages.id, pages.title, pages.url, pages.content, page_embeddings.vector
          FROM pages
          JOIN page_embeddings ON page_embeddings.page_id = pages.id
        """)
        rows = cur.fetchall()
        con.close()
        if not rows:
            return ("", 204)

        # 2) 쿼리 임베딩
        qv = _embed_query(utter)

        # 3) 유사도(본문) + 제목/URL 키워드 가산점
        scored = []
        for pid, title, url, content, vjson in rows:
            try:
                v = json.loads(vjson)
                base = _cos(qv, v)                              # 본문 유사도
                boost = _title_overlap_boost(title or "", url or "", keywords)  # 최대 +0.10
                score = base + boost
                scored.append((score, base, title, url, content))
            except Exception:
                continue

        # 4) 상위 후보 → URL 중복 제거 → 3개 선택
        scored.sort(reverse=True, key=lambda x: x[0])
        seen, picked = set(), []
        for score, base, title, url, content in scored[:10]:
            key = _normalize_url(url or "")
            if not key or key in seen:
                continue
            seen.add(key)
            picked.append((score, base, title, url, content))
            if len(picked) == 3:
                break

        if not picked:
            return ("", 204)

        # 5) 임계값(정밀도) 컷: 본문 유사도(base) 기준
        THRESH = 0.70  # 운영 권장: 0.70~0.75
        GOOD = [p for p in picked if p[1] >= THRESH]
        # 초기 테스트에서 너무 안 나오면 0.60까지 1회 완화
        if not GOOD:
            GOOD = [p for p in picked if p[1] >= 0.60]
            if not GOOD:
                return ("", 204)

        # 6) 카드 구성(스니펫 포함)
        items = []
        for score, base, title, url, content in GOOD:
            snippet = _make_snippet(content or "", keywords, width=90)
            desc = f"{(snippet or '관련 내용 미리보기').strip()}  · 관련도 {base:.2f}"
            items.append({
                "title": (title or url)[:50],
                "description": desc[:120],
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
        }), 200

    except Exception as e:
        app.logger.error(f"[LINK_RECO ERROR] {type(e).__name__}: {e}")
        return ("", 204)

# -----------------------------
# 임시 통계 라우트(운영 중 점검용)
# -----------------------------
@app.get("/stats_pages")
def stats_pages():
    try:
        path = db.db_path if db else None
        if not path:
            return jsonify({"error": "db not initialized"}), 200
        con = sqlite3.connect(path)
        cur = con.cursor()
        out = {}
        for t in ("pages", "page_embeddings", "qa_data", "qa_embeddings"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                out[t] = cur.fetchone()[0]
            except Exception:
                out[t] = "N/A"
        con.close()
        return jsonify(out), 200
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 200

# -----------------------------
# 로컬 실행용
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

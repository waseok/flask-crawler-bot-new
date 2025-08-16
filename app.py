import os
import json
import sqlite3
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from flask import Flask, request, jsonify
from openai import OpenAI

# database.py 에 아래가 있어야 합니다:
# - class DatabaseManager: db_path 제공, get_qa_data() 제공
# - function db_diagnostics(): DB 상태 리턴
from database import DatabaseManager, db_diagnostics

app = Flask(__name__)

# -----------------------------
# OpenAI (환경변수 OPENAI_API_KEY 사용)
# -----------------------------
client = OpenAI()  # 키는 환경변수에서 자동으로 읽음

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

def semantic_answer(utter: str, db_path: str, threshold: float = 0.75):
    """qa_embeddings 벡터와 비교해 가장 유사한 qa_data.answer 반환(임계값 이상일 때만)."""
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
# 링크추천 헬퍼
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
# 헬스/핑/통계 (안전 가드)
# -----------------------------
@app.get("/ping")
def ping():
    return jsonify({"ok": True}), 200

@app.get("/health")
def health():
    try:
        diag = db_diagnostics()
    except Exception as e:
        diag = {"error": f"{type(e).__name__}: {e}"}
    connected = bool(diag.get("exists")) and diag.get("integrity") == "ok"
    return jsonify({
        "status": "healthy",
        "database": "connected" if connected else "disconnected",
        "diag": diag
    }), 200

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

@app.get("/")
def index():
    return jsonify({"ok": True, "message": "Flask server is running"}), 200

# -----------------------------
# 링크 추천 내부 로직 (조인 + 중복 제거 + 스니펫)
# -----------------------------
def link_reco_internal(user_text: str):
    # --- 키워드 추출(간단 불용어 제거) ---
    stopwords = ["안내","해주세요","해줘","알려줘","알려주세요","인가요","있나요","어디","어떻게","요","좀",
                 "을","를","은","는","이","가","에","로","에서","에게"]
    raw_tokens = user_text.replace("/", " ").split()
    keywords = [t for t in raw_tokens if t not in stopwords]

    if db is None or not user_text:
        return ("", 204)

    # --- pages + page_embeddings 조인으로 로드 ---
    con = sqlite3.connect(db.db_path)
    cur = con.cursor()
    cur.execute("""
      SELECT p.id, p.title, p.url, p.content, e.vector
      FROM pages p
      JOIN page_embeddings e ON e.page_id = p.id
    """)
    rows = cur.fetchall()
    con.close()
    if not rows:
        return ("", 204)

    # --- 쿼리 임베딩 ---
    q_emb = _embed_query(user_text)

    # --- 본문 유사도 + 제목/URL 가산점 ---
    scored = []
    for pid, title, url, content, vjson in rows:
        try:
            v = json.loads(vjson)
            base = _cos(q_emb, v)  # 본문 유사도
            boost = _title_overlap_boost(title or "", url or "", keywords)  # 최대 +0.10
            score = base + boost
            scored.append((score, base, title, url, content))
        except Exception:
            continue

    if not scored:
        return ("", 204)

    # --- 상위 후보 → 중복URL 제거 → 최대 3개 ---
    scored.sort(reverse=True, key=lambda x: x[0])

    def _normalize(u: str) -> str:
        s = urlsplit(u or "")
        return urlunsplit((s.scheme, s.netloc, s.path, "", ""))

    seen, picked = set(), []
    for score, base, title, url, content in scored[:10]:
        key = _normalize(url)
        if not key or key in seen:
            continue
        seen.add(key)
        picked.append((score, base, title, url, content))
        if len(picked) == 3:
            break

    if not picked:
        return ("", 204)

    # --- 임계값(본문 base 기준). 운영은 0.70~0.75 권장. 초기엔 0.60으로 확인 가능.
    THRESH = float(os.getenv("RECO_THRESH", "0.70"))
    good = [p for p in picked if p[1] >= THRESH]
    if not good:
        # 초기 확인을 위해 한 번 더 완화(원치 않으면 이 블록 삭제)
        fallback_thresh = 0.60
        good = [p for p in picked if p[1] >= fallback_thresh]
        if not good:
            return ("", 204)

    # --- 카드 아이템(스니펫 포함) 구성 ---
    items = []
    for score, base, title, url, content in good:
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

# -----------------------------
# 공개 링크추천 엔드포인트(원하면 오픈빌더에서 직접 사용)
# -----------------------------
@app.post("/link_reco")
def link_reco():
    body = request.get_json(silent=True) or {}
    utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    return link_reco_internal(utter)

# -----------------------------
# 메인 스킬: ①QA → ②링크추천 → ③텍스트 폴백 (안전 가드)
# -----------------------------
@app.post("/")
def main_skill():
    try:
        body = request.get_json(silent=True) or {}
        utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    except Exception:
        utter = ""

    # 1) QA 포함/정확 → 임베딩
    answer = None
    try:
        if db is not None and utter:
            # (1) 포함/정확
            try:
                rows = db.get_qa_data()
                for r in rows:
                    q = (r.get("question") or "").strip()
                    if q and (utter in q or q in utter):
                        answer = (r.get("answer") or "").strip()
                        break
            except Exception as e:
                app.logger.error(f"[DB QUERY ERROR] {type(e).__name__}: {e}")

            # (2) 임베딩
            if not answer:
                try:
                    answer = semantic_answer(utter, db.db_path, threshold=0.75)
                except Exception as e:
                    app.logger.error(f"[SEMANTIC ERROR] {type(e).__name__}: {e}")
    except Exception as e:
        app.logger.error(f"[MAIN QA BLOCK ERROR] {type(e).__name__}: {e}")

    # 2) QA가 없으면 링크추천으로 위임(카드 or 204)
    if not answer and utter:
        try:
            return link_reco_internal(utter)  # 200(listCard) or 204
        except Exception as e:
            app.logger.error(f"[LINK RECO DELEGATE ERROR] {type(e).__name__}: {e}")

    # 3) 최종 폴백(텍스트)
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
# 로컬 실행
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

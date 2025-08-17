import os
import json
import time
import sqlite3
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from flask import Flask, request, jsonify
from openai import OpenAI

# database.py 쪽에서 제공(이미 갖고 있음)
# - class DatabaseManager: db_path, get_qa_data()
# - function db_diagnostics()
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
    {"label": "📅 학사일정", "action": "message", "messageText": "📅 학사일정"},
    {"label": "📋 늘봄/방과후", "action": "message", "messageText": "📋 늘봄/방과후"},
    {"label": "📖 수업시간/시정표(초등)", "action": "message", "messageText": "📖 수업시간/시정표(초등)"},
    {"label": "📚 교과서", "action": "message", "messageText": "📚 교과서"},
    {"label": "🏠 전입/전출", "action": "message", "messageText": "🏠 전입/전출"},
    {"label": "📋 증명서/서류", "action": "message", "messageText": "📋 증명서/서류"},
    {"label": "📞 연락처/상담", "action": "message", "messageText": "📞 연락처/상담"},
    {"label": "🍽️ 급식", "action": "message", "messageText": "🍽️ 급식"},
    {"label": "🎶 기타", "action": "message", "messageText": "🎶 기타"},
    {"label": "🧸 유치원", "action": "message", "messageText": "🧸 유치원"},
]

# -----------------------------
# 시간/타임아웃 가드 (카카오 3~5초 내 응답)
# -----------------------------
KAKAO_BUDGET_MS = int(os.getenv("KAKAO_BUDGET_MS", "2800"))  # 기본 2.8초 안에 끝내기

def budget_left(start_mono: float) -> float:
    """남은 시간(초)"""
    return KAKAO_BUDGET_MS / 1000.0 - (time.monotonic() - start_mono)

# -----------------------------
# 코사인/임베딩 유틸
# -----------------------------
def _cos(a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(np.dot(a, b) / denom)

def _embed_query(text: str):
    return client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

def semantic_answer(utter: str, db_path: str, threshold: float = 0.75):
    """qa_embeddings와 코사인 유사도 비교해 threshold 이상일 때 answer 반환."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        cur.execute("""
          SELECT qa_data.id, qa_data.question, qa_data.answer, qa_embeddings.vector
          FROM qa_data
          JOIN qa_embeddings ON qa_embeddings.qa_id = qa_data.id
        """)
        rows = cur.fetchall()
    finally:
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
                best_s, best_ans = s, (a or "").strip()
        except Exception:
            continue
    app.logger.info(f"[SEMANTIC] utter='{utter}' score={best_s:.3f} thr={threshold}")
    return best_ans if best_s >= threshold else None

# -----------------------------
# 링크 추천 내부 로직
# -----------------------------
def _normalize_url(u: str) -> str:
    s = urlsplit(u or "")
    return urlunsplit((s.scheme, s.netloc, s.path, "", ""))

def _make_snippet(content: str, keywords: list[str], width: int = 90) -> str:
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
    if not keywords:
        return 0.0
    hay = f"{title or ''} {url or ''}".lower()
    hits = sum(1 for k in keywords if k and len(k) >= 2 and k.lower() in hay)
    return min(0.10, 0.03 * hits)  # 최대 +0.10

def link_reco_internal(user_text: str):
    # 키워드 토큰
    stopwords = ["안내","해주세요","해줘","알려줘","알려주세요","인가요","있나요","어디","어떻게","요","좀",
                 "을","를","은","는","이","가","에","로","에서","에게"]
    raw_tokens = (user_text or "").replace("/", " ").split()
    keywords = [t for t in raw_tokens if t and t not in stopwords]

    # DB에서 페이지+임베딩 로드
    try:
        con = sqlite3.connect(db.db_path)
        cur = con.cursor()
        cur.execute("""
          SELECT p.id, p.title, p.url, p.content, e.vector
          FROM pages p
          JOIN page_embeddings e ON e.page_id = p.id
        """)
        rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        try:
            con.close()
        except Exception:
            pass

    if not rows or not user_text:
        return ("", 204)

    # 쿼리 임베딩
    q_emb = _embed_query(user_text)

    # 유사도 + 가산점
    scored = []
    for pid, title, url, content, vjson in rows:
        try:
            v = json.loads(vjson)
            base = _cos(q_emb, v)
            boost = _title_overlap_boost(title or "", url or "", keywords)
            score = base + boost
            scored.append((score, base, title, url, content))
        except Exception:
            continue

    if not scored:
        return ("", 204)

    # 상위 후보 → URL 중복 제거 → 최대 3개
    scored.sort(reverse=True, key=lambda x: x[0])
    seen, picked = set(), []
    for score, base, title, url, content in scored[:12]:
        key = _normalize_url(url)
        if not key or key in seen:
            continue
        seen.add(key)
        picked.append((score, base, title, url, content))
        if len(picked) == 3:
            break

    if not picked:
        return ("", 204)

    # 임계값 (본문 유사도 base). 환경변수로 조절 가능.
    env_thr = float(os.getenv("RECO_THRESH", "0.70"))
    good = [p for p in picked if p[1] >= env_thr]
    if not good:
        # 너무 빡세면 완화(초기 운영 편의). 원치 않으면 아래 3줄 제거.
        fallback_thr = 0.60
        good = [p for p in picked if p[1] >= fallback_thr]
        if not good:
            return ("", 204)

    # 카드 아이템
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
# DB 초기화 (실패해도 앱은 뜸)
# -----------------------------
try:
    db = DatabaseManager()
except Exception as e:
    db = None
    app.logger.error(f"[DB INIT ERROR] {type(e).__name__}: {e}")

# -----------------------------
# 헬스/핑/통계
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
# 링크 추천 엔드포인트(절대 204 내지 않게)
# -----------------------------
@app.post("/link_reco")
def link_reco():
    body = request.get_json(silent=True) or {}
    utter = (body.get("userRequest", {}).get("utterance") or "").strip()

    # 바디가 없거나 비어도 200 텍스트 폴백
    if not utter:
        return jsonify({
            "version":"2.0",
            "template":{
                "outputs":[{"simpleText":{"text":"무엇을 찾고 싶으신가요? 예) 교실 배치도, 시설 대관, 급식표"}}],
                "quickReplies": QUICK_REPLIES
            }
        }), 200

    resp = link_reco_internal(utter)  # (json,200) 또는 ("",204)
    # 결과 없을 때도 200으로 폴백
    if isinstance(resp, tuple) and len(resp) == 2 and resp[1] == 204:
        return jsonify({
            "version":"2.0",
            "template":{
                "outputs":[{"simpleText":{"text":f"‘{utter}’ 관련 링크를 찾지 못했어요.\n키워드를 바꿔 다시 물어봐 주세요 🙂"}}],
                "quickReplies": QUICK_REPLIES
            }
        }), 200
    return resp

# -----------------------------
# 메인 스킬: ①정확/포함 → ②임베딩(시간 남을 때) → ③링크추천(시간 남을 때) → ④텍스트 폴백
# -----------------------------
@app.post("/")
def main_skill():
    t0 = time.monotonic()
    body = request.get_json(silent=True) or {}
    utter = (body.get("userRequest", {}).get("utterance") or "").strip()

    # 바디 없으면 즉시 폴백(카카오 전송테스트 커버)
    if not utter:
        return jsonify({
            "version":"2.0",
            "template":{
                "outputs":[{"simpleText":{"text":"무엇을 도와드릴까요? 아래 메뉴를 눌러주세요 🙂"}}],
                "quickReplies": QUICK_REPLIES
            }
        }), 200

    answer = None

    # (1) 초고속 정확/포함 매칭 (DB 조회만, 외부호출 없음)
    try:
        if db is not None:
            rows = db.get_qa_data()
            for r in rows:
                q = (r.get("question") or "").strip()
                if q and (utter in q or q in utter):
                    answer = (r.get("answer") or "").strip()
                    break
    except Exception as e:
        app.logger.error(f"[DB EXACT] {type(e).__name__}: {e}")

    # (2) 임베딩 매칭: 남은 시간이 충분할 때만
    try:
        if not answer and budget_left(t0) > 1.2:
            try:
                ans = semantic_answer(utter, db.db_path, threshold=0.75)
                if ans:
                    answer = ans
            except Exception as e:
                app.logger.error(f"[SEMANTIC] {type(e).__name__}: {e}")
    except Exception as e:
        app.logger.error(f"[BUDGET GUARD] {type(e).__name__}: {e}")

    # (3) QA 없으면 링크추천: 남은 시간이 있을 때만, 없으면 바로 폴백
    if not answer:
        if budget_left(t0) > 1.0:
            try:
                resp = link_reco_internal(utter)
                # 내부가 204면 카카오 에러 되니 여기서 텍스트 폴백으로 전환
                if isinstance(resp, tuple) and len(resp) == 2 and resp[1] == 204:
                    raise RuntimeError("no link candidates")
                return resp  # listCard 200
            except Exception as e:
                app.logger.info(f"[LINK RECO SKIP] {type(e).__name__}: {e}")

        # (4) 최종 텍스트 폴백 (항상 200)
        answer = "원하시는 정보를 정확히 찾지 못했어요.\n아래 메뉴를 눌러보시거나, 더 구체적으로 물어봐 주세요 🙂"

    return jsonify({
        "version":"2.0",
        "template":{
            "outputs":[{"simpleText":{"text":answer}}],
            "quickReplies": QUICK_REPLIES
        }
    }), 200

# -----------------------------
# 전역 에러 핸들러: 어떤 예외도 200 JSON 폴백으로
# -----------------------------
@app.errorhandler(Exception)
def handle_any_error(e):
    app.logger.error(f"[UNHANDLED] {type(e).__name__}: {e}")
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {"text": "잠시 응답이 지연되었어요. 다시 한번 물어봐 주세요 🙂"}
            }],
            "quickReplies": QUICK_REPLIES
        }
    }), 200

# -----------------------------
# 로컬 실행
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

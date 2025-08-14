# app.py
import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- DB 초기화 (에러가 나도 서버가 뜨도록 방어) ---
db = None
try:
    from database import DatabaseManager  # database.py에 있는 클래스
    db = DatabaseManager()                # school_data.db가 같은 폴더에 있어야 함
except Exception as e:
    # DB 초기화 실패 시에도 앱은 살아 있게 두고, /health에서 원인 표시
    db = None
    app.logger.error(f"[DB INIT ERROR] {type(e).__name__}: {e}")


# --- 가장 안전한 /health 엔드포인트 ---
@app.route("/health", methods=["GET"])
def health():
    """
    서버/DB 상태를 JSON으로 반환.
    - database.py의 db_diagnostics()를 안전하게 호출
    - 어떤 예외가 나도 500이 아닌 200으로 JSON을 돌려줌 (운영 확인 용도)
    """
    try:
        # 순환/초기화 이슈 피하려고 함수 내부에서 임포트
        from database import db_diagnostics
        try:
            diag = db_diagnostics()
        except Exception as e:
            diag = {"error": f"db_diagnostics error: {type(e).__name__}: {e}"}
    except Exception as e:
        diag = {"error": f"import error: {type(e).__name__}: {e}"}

    connected = bool(diag.get("exists")) and diag.get("integrity") == "ok"
    return jsonify({
        "status": "healthy",
        "database": "connected" if connected else "disconnected",
        "diag": diag
    }), 200


# --- (선택) 루트 GET: 간단 핑 ---
@app.route("/", methods=["GET"])
def index():
    return jsonify({"ok": True, "message": "Flask server is running"}), 200


# --- 카카오 오픈빌더 스킬용 루트 POST (안전한 최소본) ---
@app.route("/", methods=["POST"])
def kakao_skill():
    """
    오픈빌더 API 스킬에서 호출하는 엔드포인트.
    - 요청 바디에서 발화(utterance)를 꺼내고
    - 간단히 응답(JSON, version 2.0)을 반환
    - DB 사용 시에도 예외를 삼켜서 500이 나지 않게 처리
    """
    try:
        body = request.get_json(silent=True, force=False) or {}
        utter = (body.get("userRequest", {}).get("utterance") or "").strip()
    except Exception:
        body, utter = {}, ""

    answer = None

    # 1) DB가 있으면 간단 조회(필요 없으면 이 블록 제거해도 됨)
    if db is not None and utter:
        try:
            # 아주 단순한 contains 매칭 (프로덕션에선 적합한 검색 로직으로 교체)
            rows = db.get_qa_data()  # [{'question':..., 'answer':...}, ...]
            for r in rows:
                q = (r.get("question") or "").strip()
                if q and (utter in q or q in utter):
                    answer = (r.get("answer") or "").strip()
                    break
        except Exception as e:
            app.logger.error(f"[DB QUERY ERROR] {type(e).__name__}: {e}")

    # 2) 폴백 응답
    if not answer:
        # 사용자가 보기 좋게 기본 안내
        if utter:
            answer = f"'{utter}'에 대한 준비된 답을 찾지 못했어요.\n아래 메뉴로 계속해 보세요!"
        else:
            answer = "무엇을 도와드릴까요?\n예) 학사일정, 오늘 급식, 가정통신문"

    # 카카오 응답 포맷 (SimpleText + QuickReplies)
    response = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": answer}}],
            "quickReplies": [
                {"label": "학사일정", "action": "message", "messageText": "학사일정"},
                {"label": "오늘 급식", "action": "message", "messageText": "오늘 급식"},
                {"label": "가정통신문", "action": "message", "messageText": "가정통신문"},
            ]
        }
    }
    return jsonify(response), 200


# --- (선택) 간단 통계: 테이블 개수만 반환 (문제 생겨도 500 방지) ---
@app.route("/stats", methods=["GET"])
def stats():
    info = {"ok": True, "tables": {}, "error": None}
    try:
        if db is None:
            raise RuntimeError("DB is not initialized")
        # 각 테이블 개수 집계 (필요 없으면 제거 가능)
        try:
            from sqlite3 import connect
            conn = connect(db.db_path)
            cur = conn.cursor()
            for t in ("qa_data", "conversation_history", "meals", "notices"):
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    info["tables"][t] = cur.fetchone()[0]
                except Exception:
                    info["tables"][t] = "N/A"
            conn.close()
        except Exception as e:
            info["error"] = f"stats error: {type(e).__name__}: {e}"
    except Exception as e:
        info["error"] = f"init error: {type(e).__name__}: {e}"
    return jsonify(info), 200


# --- 앱 실행 (로컬 테스트용) ---
if __name__ == "__main__":
    # Render에서는 gunicorn을 쓰는 게 일반적이지만,
    # 로컬에선 아래로 실행해도 됩니다.
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

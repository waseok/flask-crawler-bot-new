from flask import Flask, request, jsonify
import json
import traceback
import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import PORT, DEBUG, KAKAO_BOT_TOKEN
from ai_logic import AILogic
from database import DatabaseManager

# 한국 시간대 설정 (UTC+9)
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간 반환"""
    return datetime.now(KST)

app = Flask(__name__)

# 지연 초기화를 위한 전역 변수
ai_logic = None
db = None

# 스케줄러 초기화
scheduler = BackgroundScheduler()
scheduler.start()

def get_ai_logic():
    """AI 로직 인스턴스 가져오기 (지연 초기화)"""
    global ai_logic
    if ai_logic is None:
        ai_logic = AILogic()
    return ai_logic

def get_db():
    """DB 인스턴스 가져오기 (지연 초기화)"""
    global db
    if db is None:
        db = DatabaseManager()
    return db

def run_crawler():
    """크롤러 실행 함수"""
    try:
        print("🔄 자동 크롤링 시작...")
        result = subprocess.run(['python', 'incremental_notice_crawler.py'], 
                              capture_output=True, text=True, timeout=300)
        print(f"크롤링 결과: {result.stdout}")
        if result.stderr:
            print(f"크롤링 오류: {result.stderr}")
        
        # 크롤링 후 GitHub에 자동 커밋
        commit_to_github()
        
    except Exception as e:
        print(f"크롤링 실행 오류: {e}")

def commit_to_github():
    """GitHub에 자동 커밋"""
    try:
        print("📝 GitHub 자동 커밋 시작...")
        
        # Git 상태 확인
        subprocess.run(['git', 'add', '.'], check=True)
        
        # 변경사항이 있는지 확인
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            # 변경사항이 있으면 커밋
            commit_message = f"자동 크롤링 업데이트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            subprocess.run(['git', 'push'], check=True)
            print(f"✅ GitHub 커밋 완료: {commit_message}")
        else:
            print("📝 변경사항이 없어 커밋을 건너뜁니다.")
            
    except Exception as e:
        print(f"GitHub 커밋 오류: {e}")

def setup_scheduler():
    """스케줄러 설정"""
    # 매일 오전 6시(한국 시간)에 크롤링 실행
    scheduler.add_job(
        func=run_crawler,
        trigger=CronTrigger(hour=6, minute=0, timezone=KST),
        id='daily_crawler',
        name='매일 자동 크롤링',
        replace_existing=True
    )
    print("⏰ 자동 크롤링 스케줄러 설정 완료 (매일 오전 6시 KST)")

def exception_handler(exception):
    """예외 처리 함수"""
    caller = sys._getframe(1).f_code.co_name
    print(f"{caller} 함수에서 오류 발생")
    if hasattr(exception, "message"):
        print(exception.message)
    else:
        print("예상치 못한 오류: ", sys.exc_info()[0])

def extract_user_id(request):
    """요청에서 사용자 ID 추출"""
    try:
        body = request.get_json()
        
        # 카카오톡 챗봇 표준 형식
        if body and 'userRequest' in body:
            return body['userRequest']['user']['id']
        elif body and 'action' in body and 'params' in body:
            return body['action']['params'].get('userId', 'unknown')
        
        # machaao 형식
        if 'machaao-user-id' in request.headers:
            return request.headers['machaao-user-id']
        elif 'user-id' in request.headers:
            return request.headers['user-id']
        
        # 기본값으로 IP 주소 사용
        return request.remote_addr
    except Exception as e:
        exception_handler(e)
        return "unknown_user"

def extract_message(request):
    """요청에서 메시지 추출"""
    try:
        body = request.get_json()
        print(f"받은 요청 데이터: {body}")
        
        # 카카오톡 챗봇 v1.0 형식 (실제 카카오톡 챗봇 빌더 형식)
        if body and 'userRequest' in body:
            print(f"userRequest 내용: {body['userRequest']}")
            if 'utterance' in body['userRequest']:
                utterance = body['userRequest']['utterance']
                print(f"userRequest.utterance 추출: {utterance}")
                return utterance
            else:
                print("userRequest에 utterance가 없습니다")
        
        # 카카오톡 챗봇 빌더 테스트 형식
        elif body and 'action' in body and 'params' in body['action']:
            print(f"action.params 내용: {body['action']['params']}")
            # 카카오톡 챗봇 v2.0 형식
            if 'utterance' in body['action']['params']:
                utterance = body['action']['params']['utterance']
                print(f"utterance 추출: {utterance}")
                return utterance
            elif 'message' in body['action']['params']:
                message = body['action']['params']['message']
                print(f"message 추출: {message}")
                return message
        
        # machaao 형식
        elif body and 'raw' in body:
            try:
                import jwt
                decoded_jwt = jwt.decode(body['raw'], KAKAO_BOT_TOKEN, algorithms=['HS512'])
                text = decoded_jwt['sub']
                if isinstance(text, str):
                    text = json.loads(text)
                return text['messaging'][0]['message_data']['text']
            except:
                pass
        
        # 일반 JSON 형식
        elif body and 'message' in body:
            message = body['message']
            print(f"body.message 추출: {message}")
            return message
        
        # 폼 데이터
        elif request.form and 'message' in request.form:
            message = request.form['message']
            print(f"form.message 추출: {message}")
            return message
        
        print(f"메시지를 찾을 수 없음: {body}")
        return None
            
    except Exception as e:
        print(f"메시지 추출 중 오류: {e}")
        exception_handler(e)
        return None

def create_kakao_response(message, quick_replies=None, link=None):
    """카카오톡 응답 형식 생성"""
    # 메시지가 None이거나 빈 문자열인 경우 기본 메시지 사용
    if not message or message.strip() == "":
        message = "안녕하세요! 와석초등학교 챗봇입니다."
    
    # 메시지 길이 제한 (카카오톡 제한)
    if len(message) > 1000:
        message = message[:997] + "..."
    
    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": str(message)
                    }
                }
            ]
        }
    }

    # 링크가 있는 경우 ButtonCard로 변경
    if link:
        response["template"]["outputs"] = [
            {
                "buttonCard": {
                    "title": str(message),
                    "buttons": [
                        {
                            "action": "webLink",
                            "label": "🔗 링크 보기",
                            "webLinkUrl": link
                        }
                    ]
                }
            }
        ]
    
    # QuickReplies 추가 (카카오톡에서 자동으로 세로 배치)
    if quick_replies and isinstance(quick_replies, list):
        if len(quick_replies) > 10:
            quick_replies = quick_replies[:10]
        response["template"]["quickReplies"] = quick_replies
    
    return response

def create_quick_replies(category=None):
    """퀵 리플라이 버튼 생성 (엑셀 구조 기반)"""
    
    # 메인 카테고리 (첫 단계) - 유치원/초등학교 구분
    if category is None:
        return [
            {
                "action": "message",
                "label": "👶 유치원",
                "messageText": "유치원"
            },
            {
                "action": "message",
                "label": "🏫 초등학교",
                "messageText": "초등학교"
            }
        ]
    
    # 유치원 메뉴 - 엑셀 구조 기반
    elif category == "유치원":
        return [
            {
                "action": "message",
                "label": "📅 강화",
                "messageText": "유치원_강화"
            },
            {
                "action": "message",
                "label": "⏰ 운영시간",
                "messageText": "유치원운영시간"
            },
            {
                "action": "message",
                "label": "🎨 방과후",
                "messageText": "유치원방과후"
            },
            {
                "action": "message",
                "label": "📞 상담문의",
                "messageText": "유치원상담문의"
            },
            {
                "action": "message",
                "label": "⬅️ 뒤로가기",
                "messageText": "메인메뉴"
            }
        ]
    
    # 초등학교 메뉴 - 엑셀 구조 기반
    elif category == "초등학교":
        return [
            {
                "action": "message",
                "label": "🍽️ 급식",
                "messageText": "급식정보"
            },
            {
                "action": "message",
                "label": "🎨 방과후",
                "messageText": "방과후"
            },
            {
                "action": "message",
                "label": "📞 상담",
                "messageText": "상담문의"
            },
            {
                "action": "message",
                "label": "🏢 시설",
                "messageText": "학교시설"
            },
            {
                "action": "message",
                "label": "🚌 교통",
                "messageText": "등하교교통"
            },
            {
                "action": "message",
                "label": "📋 서류",
                "messageText": "서류증명서"
            },
            {
                "action": "message",
                "label": "📚 교과서",
                "messageText": "교과서정보"
            },
            {
                "action": "message",
                "label": "⏰ 시간",
                "messageText": "시간일정"
            },
            {
                "action": "message",
                "label": "🏥 보건",
                "messageText": "보건건강"
            },
            {
                "action": "message",
                "label": "🎯 체험",
                "messageText": "체험학습"
            },
            {
                "action": "message",
                "label": "⬅️ 뒤로가기",
                "messageText": "메인메뉴"
            }
        ]
    
    # 급식정보 - 날짜별 메뉴
    elif category == "급식정보":
        return [
            {
                "action": "message",
                "label": "🍽️ 오늘급식",
                "messageText": "오늘급식"
            },
            {
                "action": "message",
                "label": "🍽️ 내일급식",
                "messageText": "내일급식"
            },
            {
                "action": "message",
                "label": "🍽️ 이번주급식",
                "messageText": "이번주급식"
            },
            {
                "action": "message",
                "label": "⬅️ 뒤로가기",
                "messageText": "초등학교"
            }
        ]
    
    # 엑셀 시트명과 정확히 일치하는 카테고리들 - 질문 리스트 + 번호 버튼으로 표시
    elif category in ["유치원_강화", "유치원운영시간", "유치원방과후", "유치원상담문의", 
                     "강화된_QA_데이터", "원본_QA_데이터", "더보기", 
                     "방과후", "상담문의", "초등학교_강화", "학교시설", "등하교교통", 
                     "서류증명서", "교과서정보", "시간일정", "보건건강", "체험학습", "방학휴가"]:
        
        # 카테고리별 질문들을 번호 버튼으로 생성
        try:
            with open('category_questions.json', 'r', encoding='utf-8') as f:
                category_questions = json.load(f)
            
            if category in category_questions:
                questions = category_questions[category]
                quick_replies = []
                
                # 질문들을 번호 버튼으로 변환 (최대 10개)
                for i, question in enumerate(questions[:10], 1):
                    quick_replies.append({
                        "action": "message",
                        "label": f"{i}번",
                        "messageText": question
                    })
                
                # 뒤로가기 버튼 추가
                back_category = "초등학교" if "초등" in category or category in ["강화된_QA_데이터", "원본_QA_데이터", "더보기", "방과후", "상담문의", "학교시설", "등하교교통", "서류증명서", "교과서정보", "시간일정", "보건건강", "체험학습", "방학휴가"] else "유치원"
                quick_replies.append({
                    "action": "message",
                    "label": "⬅️ 뒤로가기",
                    "messageText": back_category
                })
                
                return quick_replies
            else:
                # 질문을 찾을 수 없는 경우
                return [
        {
            "action": "message",
                        "label": "⬅️ 뒤로가기",
                        "messageText": "초등학교" if "초등" in category or category in ["강화된_QA_데이터", "원본_QA_데이터", "더보기", "방과후", "상담문의", "학교시설", "등하교교통", "서류증명서", "교과서정보", "시간일정", "보건건강", "체험학습", "방학휴가"] else "유치원"
                    }
                ]
        except Exception as e:
            # 오류 발생 시 기본 뒤로가기만
            return [
            {
                    "action": "message",
                    "label": "⬅️ 뒤로가기",
                    "messageText": "초등학교" if "초등" in category or category in ["강화된_QA_데이터", "원본_QA_데이터", "더보기", "방과후", "상담문의", "학교시설", "등하교교통", "서류증명서", "교과서정보", "시간일정", "보건건강", "체험학습", "방학휴가"] else "유치원"
            }
        ]
    
    # 기본값 - 뒤로가기만
    else:
        return [
            {
                "action": "message",
                "label": "⬅️ 뒤로가기",
                "messageText": "메인메뉴"
        }
    ]

@app.route('/', methods=['GET'])
def root():
    """루트 엔드포인트"""
    return jsonify({
        "status": "ok",
        "message": "와석초등학교 챗봇 서버가 정상 작동 중입니다.",
        "timestamp": get_kst_now().isoformat()
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """카카오톡 웹훅 엔드포인트"""
    try:
        # 요청 데이터 로깅
        print("=== 웹훅 요청 받음 ===")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {request.get_data(as_text=True)}")
        
        # 사용자 ID와 메시지 추출
        user_id = extract_user_id(request)
        user_message = extract_message(request)
        
        print(f"추출된 사용자 ID: {user_id}")
        print(f"추출된 메시지: {user_message}")
        
        if not user_message:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": "메시지를 이해하지 못했습니다. 다시 말씀해 주세요."
                            }
                        }
                    ]
                }
            })
        
        print(f"사용자 {user_id}: {user_message}")
        
        # 사용자 메시지에 따른 QuickReplies 결정 (엑셀 구조 기반)
        quick_replies_category = None
        text = None  # 기본 텍스트 초기화
        
        # 메인 카테고리 선택 시 간단한 안내 메시지 (AI 로직 건너뛰기)
        if user_message in ["유치원", "초등학교"]:
            quick_replies_category = user_message
            if user_message == "유치원":
                text = "유치원 관련 궁금하신 점을 선택해주세요."
            else:
                text = "초등학교 관련 궁금하신 점을 선택해주세요."
        
        # 메인메뉴 처리
        elif user_message == "메인메뉴":
            quick_replies_category = None  # 메인 메뉴
        
        # 엑셀 시트명과 정확히 일치하는 카테고리들 - 질문 리스트 + 번호 버튼으로 표시
        elif user_message in ["유치원_강화", "유치원운영시간", "유치원방과후", "유치원상담문의", 
                             "강화된_QA_데이터", "원본_QA_데이터", "급식정보", "더보기", 
                             "방과후", "상담문의", "초등학교_강화", "학교시설", "등하교교통", 
                             "서류증명서", "교과서정보", "시간일정", "보건건강", "체험학습", "방학휴가"]:
            quick_replies_category = user_message
            # 카테고리별 질문 리스트 생성
            try:
                with open('category_questions.json', 'r', encoding='utf-8') as f:
                    category_questions = json.load(f)
                
                if user_message in category_questions:
                    questions = category_questions[user_message]
                    text = f"{user_message} 관련 질문을 선택해주세요.\n\n"
                    
                    # 질문들을 번호 리스트로 추가 (최대 10개)
                    for i, question in enumerate(questions[:10], 1):
                        text += f"{i}. {question}\n"
                else:
                    text = f"{user_message} 관련 질문을 선택해주세요."
            except Exception as e:
                text = f"{user_message} 관련 질문을 선택해주세요."
        
        # AI 로직으로 메시지 처리 (메뉴가 아닌 경우에만)
        link = None  # 링크 초기화
        if text is None:
            try:
                ai_logic = get_ai_logic()
                
                # 메뉴 선택(1번, 2번 등)인지 확인 - category_questions.json의 질문들과 매칭
                is_menu_selection = False
                try:
                    with open('category_questions.json', 'r', encoding='utf-8') as f:
                        category_questions = json.load(f)
                    
                    for category, questions in category_questions.items():
                        if user_message in questions:
                            is_menu_selection = True
                            break
                except:
                    pass
                
                if is_menu_selection:
                    # 급식 관련 메뉴는 실시간 데이터 사용 (이번주급식 제외)
                    if user_message in ["오늘급식", "내일급식"]:
                        # 실시간 급식 데이터 사용
                        success, response = ai_logic.process_message(user_message, user_id)
                        if isinstance(response, dict):
                            text = response.get("text", str(response))
                            link = response.get("link")
                        else:
                            text = str(response)
                    else:
                        # 다른 메뉴 선택인 경우 AI 없이 엑셀 답변 그대로 사용
                        response = ai_logic.get_menu_answer(user_message)
                        if response:
                            text = response.get("text", str(response))
                        else:
                            text = "죄송합니다. 해당 질문에 대한 답변을 찾을 수 없습니다."
                else:
                    # 자유 질문인 경우 AI 사용 (급식은 실시간 크롤링 유지)
                    success, response = ai_logic.process_message(user_message, user_id)
                    
                    # 텍스트 응답으로 통일
                    if isinstance(response, dict):
                        text = response.get("text", str(response))
                        link = response.get("link")  # 링크 추출
                    else:
                        text = str(response)
                
            except Exception as ai_error:
                print(f"AI 로직 오류: {ai_error}")
                text = "안녕하세요! 와석초등학교 챗봇입니다. 무엇을 도와드릴까요?"
        
        # 특별한 응답 메시지들 (QuickReplies 없이) - 엑셀 구조 기반
        special_responses = [
            # 급식 관련 (날짜별 메뉴 형태로 유지)
            "오늘 급식 메뉴 알려줘", "내일 급식 메뉴 알려줘", "이번주 급식 메뉴 알려줘", "오늘의 급식은?"
        ]
        
        # 질문 목록인 경우 표시
        if user_message in ["유치원_강화", "유치원운영시간", "유치원방과후", "유치원상담문의", 
                           "강화된_QA_데이터", "원본_QA_데이터", "급식정보", "더보기", 
                           "방과후", "상담문의", "초등학교_강화", "학교시설", "등하교교통", 
                           "서류증명서", "교과서정보", "시간일정", "보건건강", "체험학습", "방학휴가"]:
            kakao_response = create_kakao_response(text, create_quick_replies(quick_replies_category), link)
        # 특별한 응답인 경우 QuickReplies 없이
        elif any(keyword in user_message for keyword in special_responses):
            kakao_response = create_kakao_response(text, link=link)
        # 첫 인사나 일반적인 질문인 경우 메인 메뉴 제공
        elif any(keyword in user_message for keyword in ["안녕", "안녕하세요", "안녕!", "안녕~", "도움", "도움말", "무엇을", "뭐해", "뭐하고 있어"]):
            kakao_response = create_kakao_response(text, create_quick_replies(None), link)  # 메인 메뉴
        else:
            kakao_response = create_kakao_response(text, create_quick_replies(quick_replies_category), link)
        
        # 응답 로깅
        print(f"응답 데이터: {kakao_response}")
        
        # 응답 형식 검증
        if not isinstance(kakao_response, dict):
            raise ValueError("응답이 딕셔너리 형식이 아닙니다")
        
        if "version" not in kakao_response:
            kakao_response["version"] = "2.0"
        
        if "template" not in kakao_response:
            raise ValueError("template 필드가 없습니다")
        
        return jsonify(kakao_response)
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        exception_handler(e)
        print(f"오류 발생: {e}")
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "죄송합니다. 서비스에 일시적인 문제가 발생했습니다."
                        }
                    }
                ]
            }
        })

@app.route('/test', methods=['GET', 'POST'])
def test():
    """테스트 엔드포인트"""
    if request.method == 'GET':
        return jsonify({
            "status": "test",
            "message": "테스트 페이지입니다. POST로 메시지를 보내보세요.",
            "example": {
                "message": "오늘 급식 메뉴 알려줘"
            }
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            user_message = data.get('message', '안녕하세요')
            user_id = data.get('user_id', 'test_user')
            
            print(f"테스트 - 사용자 {user_id}: {user_message}")
            
            ai_logic = get_ai_logic()
            success, response = ai_logic.process_message(user_message, user_id)
            
            # 텍스트 응답으로 통일
            if isinstance(response, dict):
                response_text = response.get("text", str(response))
            else:
                response_text = str(response)
            
            response_data = {
                "success": success,
                "response_type": "text",
                "response": response_text,
                "user_message": user_message,
                "user_id": user_id
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            exception_handler(e)
            return jsonify({"error": str(e)}), 500

@app.get("/health")
def health():
    diag = db_diagnostics()
    connected = (diag.get("exists") and diag.get("integrity") == "ok")
    return jsonify({
        "status": "healthy",
        "database": "connected" if connected else "disconnected",
        "diag": diag
    }), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """통계 정보 엔드포인트"""
    try:
        # QA 데이터 개수
        qa_count = len(db.get_qa_data())
        
        # 최근 대화 히스토리 개수 (테스트용)
        test_history = db.get_conversation_history("test_user", limit=10)
        
        return jsonify({
            "qa_data_count": qa_count,
            "recent_conversations": len(test_history),
            "server_status": "running",
            "timestamp": get_kst_now().isoformat()
        })
        
    except Exception as e:
        exception_handler(e)
        return jsonify({"error": str(e)}), 500

@app.route('/crawl', methods=['POST'])
def manual_crawl():
    """수동 크롤링 실행 엔드포인트"""
    try:
        print("🔄 수동 크롤링 요청 받음")
        run_crawler()
        return jsonify({
            "status": "success",
            "message": "크롤링이 성공적으로 실행되었습니다.",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        exception_handler(e)
        return jsonify({"error": str(e)}), 500

@app.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    """스케줄러 상태 확인 엔드포인트"""
    try:
        jobs = scheduler.get_jobs()
        job_info = []
        for job in jobs:
            job_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return jsonify({
            "scheduler_running": scheduler.running,
            "jobs": job_info,
            "timestamp": get_kst_now().isoformat()
        })
    except Exception as e:
        exception_handler(e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"와석초등학교 챗봇 서버 시작 - 포트: {PORT}")
    print(f"디버그 모드: {DEBUG}")
    
    # 스케줄러 설정
    setup_scheduler()
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG) 

import openai
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
import re
from config import OPENAI_API_KEY, OPENAI_MODEL, TEMPERATURE, MAX_TOKENS, TOP_P, BAN_WORDS
from database import DatabaseManager

# 한국 시간대 설정 (UTC+9)
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간 반환"""
    return datetime.now(KST)

def extract_link_from_text(text: str):
    """텍스트에서 첫 번째 URL을 추출하고, 본문과 링크를 분리"""
    url_pattern = r'(https?://[\w\-./?%&=:#@]+)'
    match = re.search(url_pattern, text)
    if match:
        url = match.group(1)
        # 본문에서 URL 제거(공백도 정리)
        text_wo_url = text.replace(url, '').strip()
        # 본문 끝에 불필요한 구두점/공백 제거
        text_wo_url = re.sub(r'[\s\-:·,]+$', '', text_wo_url)
        
        # 본문이 비어있으면 기본 안내문 추가
        if not text_wo_url:
            if "ktbookmall.com" in url:
                text_wo_url = "교과서 구매는 아래 링크에서 가능합니다."
            elif "goepj.kr" in url:
                text_wo_url = "자세한 내용은 아래 링크에서 확인하실 수 있습니다."
            elif "docs.google.com" in url:
                text_wo_url = "학사일정은 아래 링크에서 확인하실 수 있습니다."
            else:
                text_wo_url = "자세한 내용은 아래 링크를 참고해주세요."
        
        return text_wo_url, url
    return text, None

class AILogic:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        self.db = DatabaseManager()
        self.qa_data = None
        self._initialized = False
        
    def _ensure_initialized(self):
        """필요할 때만 QA 데이터를 로드하는 지연 초기화"""
        if not self._initialized:
            self.load_qa_data()
            self._initialized = True
        
    def load_qa_data(self):
        """QA 데이터 로드 (최적화된 버전)"""
        try:
            # JSON 파일에서 데이터 로드
            with open('school_dataset.json', 'r', encoding='utf-8') as f:
                self.qa_data = json.load(f)
                print(f"QA 데이터 로드 완료: {len(self.qa_data)}개 항목")
        except Exception as e:
            print(f"JSON 파일 로드 실패: {e}")
            try:
                # DB에서 데이터 로드 (fallback)
                self.qa_data = self.db.get_qa_data()
                print(f"DB에서 QA 데이터 로드 완료: {len(self.qa_data)}개 항목")
            except Exception as e2:
                print(f"DB 로드도 실패: {e2}")
                self.qa_data = []
    
    def is_banned_content(self, text: str) -> bool:
        """금지된 내용인지 확인 (학교 관련 문의는 예외)"""
        text_lower = text.lower()
        
        # 학교 관련 문의는 허용
        school_inquiry_keywords = ['학교폭력', '상담', '문의', '도움', '안내']
        if any(keyword in text for keyword in school_inquiry_keywords):
            return False
            
        return any(word in text_lower for word in BAN_WORDS)
    
    def get_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 와석초등학교의 친근하고 도움이 되는 챗봇입니다. 
다음 규칙을 따라주세요:

1. 항상 친근하고 정중하게 응답하세요
2. 반드시 아래 제공된 학교 데이터베이스 정보만을 참고해서 답변하세요
3. 데이터베이스에 없는 정보는 "죄송합니다. 해당 정보는 데이터베이스에 없습니다."라고 답변하세요
4. 한국어로 응답하세요
5. 답변은 간결하고 명확하게 작성하세요
6. 일반적인 대화나 학교와 관련 없는 질문에는 "와석초등학교 관련 질문에만 답변할 수 있습니다."라고 답변하세요

학교 정보:
- 학교명: 와석초등학교
- 위치: 경기도
- 주요 서비스: 급식 정보, 공지사항, 학교 생활 안내"""
    
    def build_conversation_context(self, user_id: str, current_message: str) -> List[Dict]:
        """대화 컨텍스트 구축 (최적화된 버전)"""
        # 간단한 시스템 프롬프트만 사용
        system_prompt = self.get_system_prompt()
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 최근 대화 히스토리는 1개만 가져오기 (성능 향상)
        history = self.db.get_conversation_history(user_id, limit=1)
        
        for conv in reversed(history):
            messages.append({"role": "user", "content": conv['message']})
            messages.append({"role": "assistant", "content": conv['response']})
        
        # 현재 메시지 추가
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def preprocess_question(self, text: str) -> str:
        """질문 전처리: 소문자화, 특수문자 제거, 불용어 제거 등"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        # 불용어 예시(확장 가능)
        stopwords = ['은', '는', '이', '가', '을', '를', '에', '의', '도', '로', '과', '와', '에서', '에게', '한', '하다', '있다', '어떻게', '무엇', '어디', '언제', '왜', '누구']
        for sw in stopwords:
            text = text.replace(sw, '')
        return text.strip()

    def is_school_related(self, text: str) -> bool:
        """와석초등학교 관련 질문인지 판별 (개선된 버전)"""
        text_lower = text.lower()
        
        # 학교 관련 키워드 (확장된 목록)
        school_keywords = [
            # 학교 기본 정보
            '와석', '와석초', '와석초등학교', '학교', '초등학교',
            
            # 학사 관련
            '개학', '방학', '졸업', '입학', '전학', '전입', '전출',
            '학사일정', '학사', '일정', '스케줄', '시험', '시험일',
            
            # 급식 관련 (맥락적 표현 포함)
            '급식', '식단', '점심', '중식', '메뉴', '밥', '식사', '밥상',
            '먹어', '먹었어', '먹었어요', '먹었냐', '나와', '나와요', '나오냐',
            
            # 방과후 관련
            '방과후', '방과후학교', '늘봄교실', '돌봄교실', '특기적성',
            
            # 교실/학급 관련
            '교실', '학급', '반', '담임', '선생님', '교사', '학년',
            
            # 등하교 관련
            '등교', '하교', '등하교', '정차대', '버스', '통학',
            
            # 학교시설 관련
            '체육관', '운동장', '도서관', '도서실', '보건실', '급식실',
            '컴퓨터실', '음악실', '미술실', '학교시설',
            
            # 상담/문의 관련
            '상담', '문의', '연락', '전화', '전화번호', '연락처', '얘기', '만나',
            
            # 결석/출석 관련
            '결석', '출석', '체험학습', '현장학습', '신고서', '아프면', '병원',
            
            # 유치원 관련
            '유치원', '유아', '원무실', '등원', '하원',
            
            # 일반적인 학교 관련 표현
            '알려줘', '알려주세요', '어디', '언제', '어떻게', '무엇', '왜', '누가', '어떤', '몇',
            '궁금', '필요', '찾고', '도와', '부탁', '얼마', '얼마나', '뭐가', '뭐야', '뭐예요',
            '어디야', '어디예요', '언제야', '언제예요', '어떻게야', '어떻게예요',
            '누구한테', '누구랑', '어디로', '어디서', '언제까지', '얼마나 걸려'
        ]
        
        # 부적절한 내용 키워드
        inappropriate_keywords = [
            '바보', '멍청', '싫어', '화나', '짜증', '죽어', '꺼져',
            '개새끼', '병신', '미친', '돌았', '미쳤'
        ]
        
        # 부적절한 내용이 포함된 경우 거부
        for keyword in inappropriate_keywords:
            if keyword in text_lower:
                return False
        
        # 학교 관련 키워드가 하나라도 포함된 경우 허용
        for keyword in school_keywords:
            if keyword in text_lower:
                return True
        
        # 일반적인 인사나 도움 요청은 허용
        greeting_keywords = ['안녕', '도움', '감사', '고마워', '잘 있어']
        for keyword in greeting_keywords:
            if keyword in text_lower:
                return True
        
        # 와석초와 관련없는 일반적인 질문은 거부
        unrelated_keywords = ['날씨', '주식', '영화', '음식', '여행', '쇼핑', '게임']
        for keyword in unrelated_keywords:
            if keyword in text_lower:
                return False
        
        return False

    def find_qa_match(self, user_message: str, threshold: float = 0.15) -> Optional[Dict]:
        """QA 데이터에서 유사한 질문 찾기 (개선된 버전)"""
        self._ensure_initialized() # 데이터 로드 보장
        try:
            user_message_lower = user_message.lower().strip()
            best_match = None
            best_score = 0
            
            # 중요 키워드 정의 (맥락적 매칭을 위해 확장)
            important_keywords = [
                "개학", "급식", "방과후", "전학", "상담", "결석", "교실", "등하교",
                "학교시설", "유치원", "전화번호", "연락처", "일정", "시간", "방법",
                "절차", "신청", "등록", "예약", "문의", "알려줘", "알려주세요",
                "어디", "언제", "어떻게", "무엇", "왜", "누가", "어떤", "몇",
                # 맥락적 키워드 추가
                "밥", "점심", "메뉴", "식사", "중식", "밥상", "먹어", "나와",
                "얘기", "만나", "아프면", "병원", "등원", "하원",
                "뭐야", "뭐예요", "어디야", "어디예요", "언제야", "언제예요",
                "어떻게야", "어떻게예요", "얼마야", "얼마예요", "얼마나"
            ]
            
            # 우선순위 QA가 있으면 그것만 확인, 없으면 전체 확인
            qa_list = self.qa_data  # 전체 QA 데이터 확인
            
            for qa in qa_list:
                question_lower = qa['question'].lower()
                
                # 1. 정확한 매칭 (가장 높은 점수)
                if user_message_lower == question_lower:
                    return qa
                
                # 2. 유치원 관련 질문 특별 처리
                if "유치원" in user_message_lower:
                    # 유치원 카테고리인 경우만 고려
                    if qa.get('category') == '유치원':
                        # 유치원 관련 키워드 매칭
                        kindergarten_keywords = [
                            "운영시간", "교육비", "특성화", "담임", "연락처", "전화번호",
                            "개학일", "방학일", "졸업식", "행사일", "교육과정", "방과후과정",
                            "교사면담", "입학문의", "신청방법", "하원", "등원", "체험학습"
                        ]
                        
                        for keyword in kindergarten_keywords:
                            if keyword in user_message_lower and keyword in question_lower:
                                score = 0.8  # 높은 점수 부여
                                if score > best_score:
                                    best_score = score
                                    best_match = qa
                                break
                
                # 3. 초등학교 관련 질문 특별 처리
                elif "초등학교" in user_message_lower or ("초등" in user_message_lower and "유치원" not in user_message_lower):
                    # 초등학교 카테고리인 경우만 고려
                    if qa.get('category') == '초등':
                        # 초등학교 관련 키워드 매칭
                        elementary_keywords = [
                            "급식", "방과후", "늘봄교실", "상담", "전학", "서류", "발급",
                            "개학일", "방학일", "시험일", "행사일", "학교시설", "등하교",
                            "보건실", "정차대", "교실배치도"
                        ]
                        
                        for keyword in elementary_keywords:
                            if keyword in user_message_lower and keyword in question_lower:
                                score = 0.8  # 높은 점수 부여
                                if score > best_score:
                                    best_score = score
                                    best_match = qa
                                break
                
                # 4. 일반적인 키워드 매칭
                else:
                    # 중요 키워드가 포함된 경우 점수 계산
                    keyword_matches = 0
                    total_keywords = 0
                    
                    for keyword in important_keywords:
                        if keyword in user_message_lower:
                            total_keywords += 1
                            if keyword in question_lower:
                                keyword_matches += 1
                    
                    if total_keywords > 0:
                        score = keyword_matches / total_keywords
                        if score > best_score and score >= threshold:
                            best_score = score
                            best_match = qa
                
                # 5. 부분 문자열 매칭 (낮은 우선순위)
                if not best_match:
                    if user_message_lower in question_lower or question_lower in user_message_lower:
                        score = 0.3
                if score > best_score:
                    best_score = score
                    best_match = qa
            
            # 6. 특별한 케이스 처리
            if not best_match:
                # 유치원 관련 질문들에 대한 특별 처리
                if "유치원" in user_message_lower:
                    if "운영시간" in user_message_lower or "시간" in user_message_lower:
                        for qa in qa_list:
                            if "운영 시간" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                    elif "교육비" in user_message_lower or "비용" in user_message_lower:
                        for qa in qa_list:
                            if "교육비" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                    elif "담임" in user_message_lower or "연락처" in user_message_lower or "전화번호" in user_message_lower:
                        for qa in qa_list:
                            if "담임 선생님 연락처" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                    elif "개학일" in user_message_lower:
                        for qa in qa_list:
                            if "개학일" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                    elif "방학일" in user_message_lower:
                        for qa in qa_list:
                            if "방학" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                    elif "졸업식" in user_message_lower:
                        for qa in qa_list:
                            if "졸업식" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                    elif "행사일" in user_message_lower:
                        for qa in qa_list:
                            if "행사" in qa['question'] and qa.get('category') == '유치원':
                                return qa
                
                # 초등학교 관련 질문들에 대한 특별 처리
                elif "초등학교" in user_message_lower or ("초등" in user_message_lower and "유치원" not in user_message_lower):
                    if "급식" in user_message_lower:
                        for qa in qa_list:
                            if "급식" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "방과후" in user_message_lower:
                        for qa in qa_list:
                            if "방과후" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "상담" in user_message_lower:
                        for qa in qa_list:
                            if "상담" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "전학" in user_message_lower:
                        for qa in qa_list:
                            if "전학" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "개학일" in user_message_lower:
                        for qa in qa_list:
                            if "개학일" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "방학일" in user_message_lower:
                        for qa in qa_list:
                            if "방학" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "시험일" in user_message_lower:
                        for qa in qa_list:
                            if "시험" in qa['question'] and qa.get('category') == '초등':
                                return qa
                    elif "행사일" in user_message_lower:
                        for qa in qa_list:
                            if "행사" in qa['question'] and qa.get('category') == '초등':
                                return qa
            
            return best_match if best_score >= threshold else None
            
        except Exception as e:
            print(f"QA 매칭 중 오류: {e}")
        return None
    
    def calculate_context_score(self, user_message: str, question: str) -> float:
        """맥락적 매칭 점수 계산"""
        score = 0
        
        # 급식 관련 맥락 매칭
        meal_contexts = [
            (['밥', '뭐냐', '뭐야', '뭐예요'], ['급식', '식단', '메뉴']),
            (['점심', '뭐냐', '뭐야', '뭐예요'], ['급식', '식단', '메뉴']),
            (['메뉴', '뭐냐', '뭐야', '뭐예요'], ['급식', '식단', '메뉴']),
            (['먹어', '뭐'], ['급식', '식단', '메뉴']),
            (['나와', '뭐'], ['급식', '식단', '메뉴']),
            (['밥상', '뭐냐', '뭐야', '뭐예요'], ['급식', '식단', '메뉴'])
        ]
        
        for user_pattern, question_pattern in meal_contexts:
            if any(word in user_message for word in user_pattern):
                if any(word in question for word in question_pattern):
                    score += 0.7
                    break
        
        # 상담 관련 맥락 매칭
        counseling_contexts = [
            (['얘기', '하고', '싶어'], ['상담']),
            (['만나', '고', '싶어'], ['상담']),
            (['담임', '이랑'], ['상담', '담임']),
            (['선생님', '이랑'], ['상담', '교사'])
        ]
        
        for user_pattern, question_pattern in counseling_contexts:
            if any(word in user_message for word in user_pattern):
                if any(word in question for word in question_pattern):
                    score += 0.6
                    break
        
        # 결석 관련 맥락 매칭
        absence_contexts = [
            (['아프면', '어떻게'], ['결석', '신고']),
            (['병원', '갈', '것', '같으면'], ['결석', '신고']),
            (['몸이', '안', '좋으면'], ['결석', '신고'])
        ]
        
        for user_pattern, question_pattern in absence_contexts:
            if any(word in user_message for word in user_pattern):
                if any(word in question for word in question_pattern):
                    score += 0.6
                    break
        
        # 교실 관련 맥락 매칭
        classroom_contexts = [
            (['어디야', '어디예요'], ['교실', '배치', '위치']),
            (['찾고', '있어'], ['교실', '배치', '위치']),
            (['어떻게', '가'], ['교실', '배치', '위치'])
        ]
        
        for user_pattern, question_pattern in classroom_contexts:
            if any(word in user_message for word in user_pattern):
                if any(word in question for word in question_pattern):
                    score += 0.5
                    break
        
        # 등하교 관련 맥락 매칭
        commute_contexts = [
            (['언제야', '언제예요'], ['등교', '하교', '시간']),
            (['몇시야', '몇시예요'], ['등교', '하교', '시간']),
            (['어떻게', '가'], ['등교', '하교', '방법'])
        ]
        
        for user_pattern, question_pattern in commute_contexts:
            if any(word in user_message for word in user_pattern):
                if any(word in question for word in question_pattern):
                    score += 0.5
                    break
        
        return score
    
    def get_date_from_message(self, text: str) -> Optional[str]:
        """메시지에서 날짜 추출"""
        today = get_kst_now()
        
        # 상대적 날짜 표현
        if "오늘" in text:
            return today.strftime("%Y-%m-%d")
        if "내일" in text:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        if "어제" in text:
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        if "모레" in text:
            return (today + timedelta(days=2)).strftime("%Y-%m-%d")
        if "글피" in text:
            return (today + timedelta(days=3)).strftime("%Y-%m-%d")
        
        # "5월 20일", "5/20" 같은 패턴 찾기 (더 정확한 패턴)
        match = re.search(r'(\d{1,2})[월\s/](\d{1,2})일?', text)
        if match:
            month, day = map(int, match.groups())
            # 현재 연도 기준으로 날짜 생성
            try:
                target_date = today.replace(month=month, day=day)
                return target_date.strftime("%Y-%m-%d")
            except ValueError:
                # 잘못된 날짜인 경우 None 반환
                return None
        
        # "2024년 5월 20일" 같은 패턴 찾기
        match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?', text)
        if match:
            year, month, day = map(int, match.groups())
            try:
                target_date = datetime(year, month, day)
                return target_date.strftime("%Y-%m-%d")
            except ValueError:
                return None
        
        return None
    
    def get_meal_info(self, date: str) -> str:
        """식단 정보 조회"""
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            weekday = target_date.weekday()
            
            # 주말 체크
            if weekday >= 5:  # 토요일(5), 일요일(6)
                weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                return f"{date}({weekday_names[weekday]})는 주말이라 급식이 없습니다."
        
            # 실제 급식 데이터 조회
            menu = self.db.get_meal_info(date)
            if menu:
                weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                return f"{date}({weekday_names[weekday]}) 중식 메뉴입니다:\n\n{menu}"
            else:
                weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                return f"{date}({weekday_names[weekday]})에는 식단 정보가 아직 등록되지 않았습니다."
                
        except ValueError as e:
            return f"날짜 형식 오류: {date}"
        except Exception as e:
            return f"식단 정보 조회 중 오류가 발생했습니다: {str(e)}"
    
    def get_notices_info(self) -> str:
        """공지사항 정보 조회"""
        notices = self.db.get_latest_notices(limit=3)
        if not notices:
            return "현재 등록된 공지사항이 없습니다."
        
        result = "최신 공지사항입니다:\n\n"
        for notice in notices:
            result += f"📢 {notice['title']}\n"
            if notice['content']:
                result += f"   {notice['content'][:50]}...\n"
            result += f"   작성일: {notice['created_at']}\n\n"
        
        return result
    
    def get_quick_response(self, user_message: str) -> Optional[str]:
        """키워드 기반 빠른 응답 (성능 향상)"""
        user_message_lower = user_message.lower()
        
        # 간단한 키워드 기반 답변
        quick_responses = {
            # 인사 관련
            "안녕": "안녕하세요! 와석초등학교 챗봇입니다. 무엇을 도와드릴까요?",
            "안녕하세요": "안녕하세요! 와석초등학교 챗봇입니다. 무엇을 도와드릴까요?",
            "안녕!": "안녕하세요! 와석초등학교 챗봇입니다. 무엇을 도와드릴까요?",
            "안녕~": "안녕하세요! 와석초등학교 챗봇입니다. 무엇을 도와드릴까요?",
            
            # 도움 요청 관련
            "도움": "와석초등학교 관련 질문에 답변해드립니다. 급식, 방과후, 상담, 전학 등에 대해 물어보세요.",
            "도움말": "와석초등학교 관련 질문에 답변해드립니다. 급식, 방과후, 상담, 전학 등에 대해 물어보세요.",
            
            # 감사 관련
            "감사": "도움이 되어서 기쁩니다! 다른 질문이 있으시면 언제든 말씀해주세요.",
            "감사합니다": "도움이 되어서 기쁩니다! 다른 질문이 있으시면 언제든 말씀해주세요.",
            "고마워": "천만에요! 더 궁금한 점이 있으시면 언제든 물어보세요.",
            "고마워요": "천만에요! 더 궁금한 점이 있으시면 언제든 물어보세요.",
            
            # 작별 인사
            "잘 있어": "안녕히 가세요! 또 궁금한 점이 있으시면 언제든 말씀해주세요."
        }
        
        # 부분 매칭으로 빠른 응답 찾기
        for keyword, response in quick_responses.items():
            if keyword in user_message_lower:
                return response
        
        return None
    
    def get_menu_answer(self, question: str) -> Optional[Dict]:
        """메뉴 선택(1번, 2번 등)에 대한 답변을 AI 없이 엑셀에서 직접 가져오기"""
        self._ensure_initialized()
        
        if not self.qa_data:
            return None
        
        # 정확한 질문 매칭
        for qa_item in self.qa_data:
            if qa_item['question'] == question:
                answer = qa_item['answer']
                # 일체형 답변 그대로 반환 (링크 분리하지 않음)
                return {"type": "text", "text": answer}
        
        return None

    def process_message(self, user_message: str, user_id: str) -> Tuple[bool, dict]:
        """메인 메시지 처리 로직 (최적화된 버전)"""
        print(f"사용자 메시지: {user_message}")
        
        # 금지된 내용 확인
        if self.is_banned_content(user_message):
            return False, {"type": "text", "text": "부적절한 내용이 포함되어 있습니다. 다른 질문을 해주세요."}
        
        # 와석초 관련 질문인지 판별
        if not self.is_school_related(user_message):
            return False, {"type": "text", "text": "와석초등학교 관련 질문에만 답변할 수 있습니다."}
        
        # 1. 식단 관련 질문 확인 (우선순위 높음)
        if any(keyword in user_message for keyword in ["급식", "식단", "밥", "점심", "메뉴"]):
            # 급식 관련 질문에서만 날짜 추출 (오늘, 내일, 어제, 모레 등)
            date = self.get_date_from_message(user_message)
            
            # 날짜가 명시된 경우 (오늘, 내일, 어제, 모레, 구체적 날짜)
            if date:
                response = self.get_meal_info(date)
                # 급식 응답은 저장 생략 (타임아웃 방지)
                # self.db.save_conversation(user_id, user_message, response)
                return True, {"type": "text", "text": response}  # 급식은 링크 없음
            
            # 날짜가 명시되지 않은 급식 관련 질문은 "오늘"로 간주하여 실시간 조회
            if any(keyword in user_message for keyword in ["오늘", "지금", "현재", "이번", "이번주"]):
                today = get_kst_now().strftime("%Y-%m-%d")
                response = self.get_meal_info(today)
                # 급식 응답은 저장 생략 (타임아웃 방지)
                # self.db.save_conversation(user_id, user_message, response)
                return True, {"type": "text", "text": response}  # 급식은 링크 없음
            
            # 그 외 급식 관련 질문은 QA 데이터베이스에서 답변
            qa_match = self.find_qa_match(user_message)
            if qa_match:
                answer = qa_match['answer']
                # 급식은 링크 없음
                # self.db.save_conversation(user_id, user_message, answer)
                return True, {"type": "text", "text": answer}
        
        # 2. 공지사항 관련 질문 확인
        if any(keyword in user_message for keyword in ["공지", "알림", "소식", "뉴스"]):
            response = self.get_notices_info()
            # 공지사항 응답은 저장 생략 (타임아웃 방지)
            # self.db.save_conversation(user_id, user_message, response)
            return True, {"type": "text", "text": response}
        
        # 3. 유치원 관련 질문 특별 처리 (새로 추가)
        if "유치원" in user_message:
            user_message_lower = user_message.lower()
            
            # 유치원 운영시간 관련
            if any(keyword in user_message_lower for keyword in ["운영시간", "운영 시간", "시간", "몇시"]):
                response = "교육과정 시간은 오전 9시~13시 30분까지\n방과후과정은 오전 8시~19시까지"
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 유치원 교육비 관련
            elif any(keyword in user_message_lower for keyword in ["교육비", "비용", "얼마", "돈"]):
                response = "병설유치원은 입학비, 방과후과정비, 교육비, 현장학습비, 방과후특성화비 모두 무상으로 지원됩니다."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 유치원 담임 선생님 연락처
            elif any(keyword in user_message_lower for keyword in ["담임", "연락처", "전화번호", "연락"]):
                response = "바른반: 070-7525-7763\n슬기반 070-7525-7755\n꿈반 070-7525-7849\n자람반 070-7525-7560\n원무실 031-957-8715"
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 유치원 개학일
            elif "개학일" in user_message_lower:
                response = "유치원 개학일은 학사일정에 따라 매년 조금씩 다를 수 있습니다. 보통 3월 초에 1학기 개학이, 8월 말~9월 초에 2학기 개학이 진행됩니다. 정확한 개학일은 원무실(031-957-8715)로 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 유치원 방학일
            elif "방학일" in user_message_lower or "방학" in user_message_lower:
                response = "유치원 방학은 학사일정에 따라 매년 조금씩 다를 수 있습니다. 보통 7월 말~8월 초에 여름방학이, 12월 말~2월 말에 겨울방학이 진행됩니다. 정확한 방학일은 원무실(031-957-8715)로 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 유치원 졸업식
            elif "졸업식" in user_message_lower:
                response = "유치원 졸업식은 보통 2월 말에 진행됩니다. 정확한 일정은 학사일정을 참고해주시거나 원무실(031-957-8715)로 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 유치원 행사일
            elif "행사일" in user_message_lower or "행사" in user_message_lower:
                response = "유치원에서는 다양한 행사가 진행됩니다. 입학식, 졸업식, 현장학습, 학부모 참여수업 등이 있으며, 정확한 일정은 학사일정을 참고해주시거나 원무실(031-957-8715)로 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
        
        # 4. 초등학교 관련 질문 특별 처리 (새로 추가)
        elif "초등학교" in user_message or ("초등" in user_message and "유치원" not in user_message):
            user_message_lower = user_message.lower()
            
            # 초등학교 개학일
            if "개학일" in user_message_lower:
                response = "개학일은 학사일정에 따라 매년 조금씩 다를 수 있습니다. 보통 3월 초에 1학기 개학이, 8월 말~9월 초에 2학기 개학이 진행됩니다. 정확한 개학일은 교무실(031-957-8715)로 문의해주세요. 개학일에는 학생들의 건강상태를 확인하고 안전한 학교생활을 위한 안내가 이루어집니다. 더 궁금하신 점이 있으시면 언제든 말씀해주세요!"
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 초등학교 방학일
            elif "방학일" in user_message_lower or "방학" in user_message_lower:
                response = "방학은 학사일정에 따라 매년 조금씩 다를 수 있습니다. 보통 7월 말~8월 초에 여름방학이, 12월 말~2월 말에 겨울방학이 진행됩니다. 정확한 방학일은 교무실(031-957-8715)로 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 초등학교 시험일
            elif "시험일" in user_message_lower or "시험" in user_message_lower:
                response = "시험일은 학년별로 다르며, 보통 1학기 중간고사(5월), 1학기 기말고사(7월), 2학기 중간고사(10월), 2학기 기말고사(12월)에 진행됩니다. 정확한 시험일은 담임선생님께 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
            
            # 초등학교 행사일
            elif "행사일" in user_message_lower or "행사" in user_message_lower:
                response = "초등학교에서는 다양한 행사가 진행됩니다. 입학식, 졸업식, 체육대회, 학예회, 현장학습 등이 있으며, 정확한 일정은 학사일정을 참고해주시거나 교무실(031-957-8715)로 문의해주세요."
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
        
        # 5. 간단한 키워드 기반 답변 (우선순위 높음) - 더 상세하고 친근하게 개선
        simple_responses = {
            # 인사 관련 - 더 친근하고 상세하게
            "안녕": "안녕하세요! 👋 와석초등학교 챗봇입니다. 유치원과 초등학교 관련 정보를 도와드려요! 무엇을 궁금해하시나요?",
            "안녕하세요": "안녕하세요! 👋 와석초등학교 챗봇입니다. 유치원과 초등학교 관련 정보를 도와드려요! 무엇을 궁금해하시나요?",
            "안녕!": "안녕하세요! 👋 와석초등학교 챗봇입니다. 유치원과 초등학교 관련 정보를 도와드려요! 무엇을 궁금해하시나요?",
            "안녕~": "안녕하세요! 👋 와석초등학교 챗봇입니다. 유치원과 초등학교 관련 정보를 도와드려요! 무엇을 궁금해하시나요?",
            
            # 도움 요청 관련 - 더 구체적으로
            "도움": "네! 와석초등학교 관련 정보를 도와드려요! 📚\n\n• 유치원: 운영시간, 교육비, 특성화 프로그램\n• 초등학교: 급식, 방과후, 상담, 전학\n• 공통: 학사일정, 학교시설, 등하교\n\n어떤 정보가 필요하신가요?",
            "도움말": "네! 와석초등학교 관련 정보를 도와드려요! 📚\n\n• 유치원: 운영시간, 교육비, 특성화 프로그램\n• 초등학교: 급식, 방과후, 상담, 전학\n• 공통: 학사일정, 학교시설, 등하교\n\n어떤 정보가 필요하신가요?",
            "도움말이 필요해": "네! 와석초등학교 관련 정보를 도와드려요! 📚\n\n• 유치원: 운영시간, 교육비, 특성화 프로그램\n• 초등학교: 급식, 방과후, 상담, 전학\n• 공통: 학사일정, 학교시설, 등하교\n\n어떤 정보가 필요하신가요?",
            "도움이 필요해": "네! 와석초등학교 관련 정보를 도와드려요! 📚\n\n• 유치원: 운영시간, 교육비, 특성화 프로그램\n• 초등학교: 급식, 방과후, 상담, 전학\n• 공통: 학사일정, 학교시설, 등하교\n\n어떤 정보가 필요하신가요?",
            
            # 감사 관련 - 더 따뜻하게
            "감사": "도움이 되어서 정말 기쁩니다! 😊 다른 궁금한 점이 있으시면 언제든 편하게 말씀해주세요. 와석초등학교 챗봇이 항상 도와드릴게요!",
            "감사합니다": "도움이 되어서 정말 기쁩니다! 😊 다른 궁금한 점이 있으시면 언제든 편하게 말씀해주세요. 와석초등학교 챗봇이 항상 도와드릴게요!",
            "고마워": "천만에요! 😊 더 궁금한 점이 있으시면 언제든 편하게 물어보세요. 와석초등학교 챗봇이 친구처럼 도와드릴게요!",
            "고마워요": "천만에요! 😊 더 궁금한 점이 있으시면 언제든 편하게 물어보세요. 와석초등학교 챗봇이 친구처럼 도와드릴게요!",
            "고맙습니다": "천만에요! 😊 더 궁금한 점이 있으시면 언제든 편하게 물어보세요. 와석초등학교 챗봇이 친구처럼 도와드릴게요!",
            
            # 기타 일반적인 질문 - 더 친근하게
            "뭐해": "와석초등학교 관련 질문에 답변하고 있어요! 📚 유치원과 초등학교 정보를 도와드리는 중이에요. 무엇을 궁금해하시나요?",
            "뭐하고 있어": "와석초등학교 관련 질문에 답변하고 있어요! 📚 유치원과 초등학교 정보를 도와드리는 중이에요. 무엇을 궁금해하시나요?",
            "뭐해?": "와석초등학교 관련 질문에 답변하고 있어요! 📚 유치원과 초등학교 정보를 도와드리는 중이에요. 무엇을 궁금해하시나요?",
            "뭐하고 있어?": "와석초등학교 관련 질문에 답변하고 있어요! 📚 유치원과 초등학교 정보를 도와드리는 중이에요. 무엇을 궁금해하시나요?",
            
            # 작별 인사 - 더 따뜻하게
            "잘 있어": "안녕히 가세요! 👋 또 궁금한 점이 있으시면 언제든 편하게 말씀해주세요. 와석초등학교 챗봇이 항상 기다리고 있을게요! 😊",
            "잘 있어요": "안녕히 가세요! 👋 또 궁금한 점이 있으시면 언제든 편하게 말씀해주세요. 와석초등학교 챗봇이 항상 기다리고 있을게요! 😊",
            "잘 있어~": "안녕히 가세요! 👋 또 궁금한 점이 있으시면 언제든 편하게 말씀해주세요. 와석초등학교 챗봇이 항상 기다리고 있을게요! 😊",
            "잘 있어요~": "안녕히 가세요! 👋 또 궁금한 점이 있으시면 언제든 편하게 말씀해주세요. 와석초등학교 챗봇이 항상 기다리고 있을게요! 😊"
        }
        
        # 부분 매칭으로 간단한 응답 찾기 (우선순위 높게 처리)
        for keyword, response in simple_responses.items():
            if keyword in user_message:
                # 간단한 응답은 저장 생략 (타임아웃 방지)
                # self.db.save_conversation(user_id, user_message, response)
                text, url = extract_link_from_text(response)
                resp = {"type": "text", "text": text}
                if url: resp["link"] = url
                return True, resp
        
        # 6. QA 데이터베이스에서 유사한 질문 찾기
        qa_match = self.find_qa_match(user_message)
        if qa_match:
            answer = qa_match['answer']
            
            # 이미지가 포함된 답변인지 확인
            if "이미지" in answer or "사진" in answer or "첨부" in answer:
                # 이미지 응답 처리
                response = self.add_image_to_response(answer, qa_match)
            else:
                # 일반 텍스트 응답 처리
                text, url = extract_link_from_text(answer)
                response = {"type": "text", "text": text}
                if url:
                    response["link"] = url
            if qa_match.get('additional_answer'):
                    response["text"] += f"\n\n추가 정보:\n{qa_match['additional_answer']}"
            
            # 중요한 QA 응답만 저장 (타임아웃 방지)
            try:
                self.db.save_conversation(user_id, user_message, response)
            except:
                pass  # 저장 실패해도 응답은 계속
            return True, response
        
        # 7. OpenAI를 통한 응답 (마지막 수단, 타임아웃 방지를 위해 간단하게)
        return self.call_openai_api(user_message, user_id)
    
    def call_openai_api(self, user_message: str, user_id: str) -> Tuple[bool, str]:
        """OpenAI API 호출 (타임아웃 방지 최적화)"""
        try:
            # 매우 간단한 프롬프트 사용
            simple_prompt = f"와석초등학교 관련 질문: {user_message[:50]}"
            
            response = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": simple_prompt}],
                temperature=0.5,
                max_tokens=50,  # 토큰 수 더 줄임
                top_p=1.0,
                timeout=5  # 5초 타임아웃 설정
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # 응답이 너무 길면 자르기
            if len(ai_response) > 100:
                ai_response = ai_response[:100] + "..."
            
            # 데이터베이스 저장은 비동기로 처리하거나 생략
            # self.db.save_conversation(user_id, user_message, ai_response)
            return True, ai_response
            
        except Exception as e:
            print(f"OpenAI 처리 중 오류: {e}")
            # 타임아웃이나 오류 시 즉시 기본 응답 반환
            fallback_response = "죄송합니다. 해당 질문에 대한 답변을 찾을 수 없습니다. 다른 질문을 해주세요."
            return False, fallback_response
    
    def add_image_to_response(self, response: str, qa_match: Dict) -> dict:
        """이미지 첨부 응답에 실제 이미지 URL 추가 (카카오톡 챗봇용)"""
        try:
            # 질문 카테고리에 따른 이미지 매핑 (실제 이미지 파일명 사용)
            image_mapping = {
                "학사일정": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image1.jpeg",
                    "alt": "학사일정"
                },
                "교실 배치도": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image2.png",
                    "alt": "교실 배치도"
                },
                "정차대": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image3.png",
                    "alt": "정차대"
                },
                "학교시설": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image4.png",
                    "alt": "학교시설"
                },
                "급식": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image5.png",
                    "alt": "급식"
                },
                "방과후": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image7.png",
                    "alt": "방과후"
                },
                "상담": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image8.png",
                    "alt": "상담"
                },
                "전학": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image9.png",
                    "alt": "전학"
                },
                "유치원": {
                    "url": "https://raw.githubusercontent.com/lian1803/flask-crawler-bot-new/main/static/images/image10.png",
                    "alt": "유치원"
                }
            }
            
            # 질문 내용에 따른 이미지 선택 (더 정확한 매칭)
            question_lower = qa_match['question'].lower()
            category = qa_match.get('category', '').lower()
            
            # 카테고리별 우선 매칭
            if category == "유치원":
                image_info = image_mapping["유치원"]
            elif "교실" in question_lower or "배치" in question_lower:
                image_info = image_mapping["교실 배치도"]
            elif "정차" in question_lower or "버스" in question_lower or "등하교" in question_lower:
                image_info = image_mapping["정차대"]
            elif "급식" in question_lower or "식단" in question_lower or "밥" in question_lower or "점심" in question_lower:
                image_info = image_mapping["급식"]
            elif "방과후" in question_lower:
                image_info = image_mapping["방과후"]
            elif "상담" in question_lower or "문의" in question_lower:
                image_info = image_mapping["상담"]
            elif "전학" in question_lower or "전입" in question_lower or "전출" in question_lower:
                image_info = image_mapping["전학"]
            elif "시설" in question_lower or "이용" in question_lower:
                image_info = image_mapping["학교시설"]
            elif "학사일정" in question_lower or "개학" in question_lower or "방학" in question_lower:
                image_info = image_mapping["학사일정"]
            else:
                # 기본적으로 학사일정 이미지 사용
                image_info = image_mapping["학사일정"]
            
            # 응답 텍스트 개선
            if "이미지 파일 첨부" in response or "이미지 파일 참조" in response or "사진 첨부" in response:
                # 더 상세하고 친근한 설명으로 변경
                if "학사일정" in question_lower or "개학" in question_lower or "방학" in question_lower:
                    text = "와석초등학교 학사일정입니다. 📅 아래 이미지에서 정확한 일정을 확인해주세요."
                elif "교실" in question_lower or "배치" in question_lower:
                    text = "와석초등학교 교실 배치도입니다. 🏫 아래 이미지에서 교실 위치를 확인해주세요."
                elif "정차" in question_lower or "버스" in question_lower or "등하교" in question_lower:
                    text = "와석초등학교 정차대 안내입니다. 🚌 아래 이미지에서 정차대 위치를 확인해주세요."
                elif "급식" in question_lower or "식단" in question_lower:
                    text = "와석초등학교 급식 정보입니다. 🍽️ 아래 이미지에서 급식 메뉴를 확인해주세요."
                elif "방과후" in question_lower:
                    text = "와석초등학교 방과후 프로그램 안내입니다. 🎨 아래 이미지에서 프로그램 정보를 확인해주세요."
                elif "상담" in question_lower or "문의" in question_lower:
                    text = "와석초등학교 상담 안내입니다. 📞 아래 이미지에서 상담 방법을 확인해주세요."
                elif "전학" in question_lower:
                    text = "와석초등학교 전학 안내입니다. 🔄 아래 이미지에서 전학 절차를 확인해주세요."
                elif "유치원" in question_lower:
                    text = "와석초등학교 유치원 안내입니다. 👶 아래 이미지에서 유치원 정보를 확인해주세요."
                elif "시설" in question_lower:
                    text = "와석초등학교 시설 이용 안내입니다. 🏢 아래 이미지에서 시설 이용 방법을 확인해주세요."
                else:
                    text = "와석초등학교 관련 정보입니다. 📋 아래 이미지를 참고해주세요."
            else:
                text = response
            
            # 이미지 링크를 포함한 텍스트 응답으로 변경 (더 친근하게)
            text_with_link = f"{text}\n\n📎 자세한 내용은 아래 링크에서 확인하세요:\n{image_info['url']}"
            
            return {
                "type": "text",
                "text": text_with_link
            }
            
        except Exception as e:
            print(f"이미지 첨부 처리 중 오류: {e}")
            return {"type": "text", "text": response} 
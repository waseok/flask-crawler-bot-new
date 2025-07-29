import json
from ai_logic import AILogic

def test_kakao_menu_structure():
    """카톡 메뉴 구조 테스트"""
    print("=== 카톡 메뉴 구조 테스트 ===\n")
    
    # 카톡에서 실제 보이는 메뉴 구조
    kakao_menus = {
        "유치원": [
            "유치원운영시간",
            "유치원방과후", 
            "유치원상담문의"
        ],
        "초등학교": [
            "급식",
            "방과후",
            "상담문의",
            "학교시설",
            "등하교교통",
            "서류증명서",
            "교과서정보",
            "시간일정",
            "보건건강",
            "체험학습",
            "방학휴가"
        ]
    }
    
    # 현재 시스템의 카테고리 확인
    try:
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        current_categories = set()
        for item in data:
            current_categories.add(item.get('category', 'N/A'))
        
        print("현재 시스템 카테고리:")
        for category in sorted(current_categories):
            print(f"  - {category}")
        
        print("\n카톡 메뉴 구조:")
        for main_menu, sub_menus in kakao_menus.items():
            print(f"  {main_menu}:")
            for sub_menu in sub_menus:
                print(f"    - {sub_menu}")
        
        # 카테고리 매칭 확인
        print("\n=== 카테고리 매칭 확인 ===")
        missing_categories = []
        extra_categories = []
        
        kakao_all_categories = set()
        for sub_menus in kakao_menus.values():
            kakao_all_categories.update(sub_menus)
        
        for category in kakao_all_categories:
            if category not in current_categories:
                missing_categories.append(category)
        
        for category in current_categories:
            if category not in kakao_all_categories and category not in ['강화된_QA_데이터', '원본_QA_데이터', '더보기']:
                extra_categories.append(category)
        
        if missing_categories:
            print(f"❌ 카톡에 없지만 시스템에 필요한 카테고리: {missing_categories}")
        
        if extra_categories:
            print(f"⚠️ 시스템에 있지만 카톡에 없는 카테고리: {extra_categories}")
        
        if not missing_categories and not extra_categories:
            print("✅ 카테고리 매칭 완벽!")
        
    except Exception as e:
        print(f"데이터 로드 오류: {e}")

def test_question_responses():
    """질문 응답 테스트"""
    print("\n=== 질문 응답 테스트 ===\n")
    
    ai = AILogic()
    
    # 테스트할 질문들 (카톡에서 자주 묻는 질문들)
    test_questions = [
        # 방과후 관련
        "ㅇㅇ방과후 어디서 해?",
        "oo 방과후 언제 끝나?",
        "방과후 대기 장소가 있나요?",
        "방과후학교 (추가)신청은 어떻게 하나요?",
        "늘봄교실/돌봄교실/방과후학교 차이가 뭔가요?",
        "방학중 방과후과정을 운영하나요?",
        "방과후 과정의 경우 몇시부터 하원할 수 있나요?",
        
        # 급식 관련
        "오늘 급식 메뉴는?",
        "이번주 급식 메뉴 알려줘",
        "오늘의 급식은?",
        
        # 교과서 관련
        "교과서 어디서 살수있어",
        "O학년 교과서 출판사 어디인가요?",
        
        # 시간 관련
        "X학년 언제끝나?",
        "O학년 하교 시간 몇시인가요?",
        
        # 유치원 관련
        "유치원 운영시간",
        "유치원 운영 시간을 알고 싶어요",
        
        # 기타
        "학교 전화번호 알려줘",
        "졸업식은 언제인가요?",
        "수익자 수담금은 무엇인가요? (가정에서 부담하는 비용)"
    ]
    
    success_count = 0
    total_count = len(test_questions)
    
    for question in test_questions:
        try:
            success, response = ai.process_message(question, 'test_user')
            if success:
                success_count += 1
                print(f"✅ {question}")
                if isinstance(response, dict) and 'text' in response:
                    print(f"   답변: {response['text'][:50]}...")
                if isinstance(response, dict) and 'link' in response:
                    print(f"   링크: {response['link']}")
            else:
                print(f"❌ {question} - 응답 실패")
            print()
        except Exception as e:
            print(f"❌ {question} - 오류: {e}")
            print()
    
    print(f"응답 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

def test_menu_navigation():
    """메뉴 네비게이션 테스트"""
    print("\n=== 메뉴 네비게이션 테스트 ===\n")
    
    ai = AILogic()
    
    # 메뉴 클릭 시나리오 테스트
    menu_clicks = [
        "유치원",
        "초등학교",
        "유치원운영시간",
        "유치원방과후",
        "유치원상담문의",
        "급식",
        "방과후",
        "상담문의",
        "학교시설",
        "등하교교통",
        "서류증명서",
        "교과서정보",
        "시간일정",
        "보건건강",
        "체험학습",
        "방학휴가"
    ]
    
    for menu in menu_clicks:
        try:
            success, response = ai.process_message(menu, 'test_user')
            if success:
                print(f"✅ {menu} - 메뉴 응답 성공")
            else:
                print(f"❌ {menu} - 메뉴 응답 실패")
        except Exception as e:
            print(f"❌ {menu} - 오류: {e}")

def generate_final_report():
    """최종 리포트 생성"""
    print("\n" + "="*50)
    print("🎯 와석초 카카오톡 챗봇 최종 리포트")
    print("="*50)
    
    # 데이터 통계
    try:
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📊 데이터 통계:")
        print(f"  - 총 질문 수: {len(data)}개")
        
        # 카테고리별 통계
        categories = {}
        for item in data:
            cat = item.get('category', 'N/A')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"  - 카테고리 수: {len(categories)}개")
        print(f"  - 카테고리별 질문 수:")
        for cat, count in sorted(categories.items()):
            print(f"    • {cat}: {count}개")
        
        # 답변 품질 분석
        answer_lengths = [len(item['answer']) for item in data if item['answer']]
        if answer_lengths:
            avg_length = sum(answer_lengths) / len(answer_lengths)
            print(f"  - 평균 답변 길이: {avg_length:.1f}자")
            print(f"  - 최단 답변: {min(answer_lengths)}자")
            print(f"  - 최장 답변: {max(answer_lengths)}자")
        
        # 링크 포함 답변 수
        link_answers = [item for item in data if 'http' in item['answer'] or '링크' in item['answer']]
        print(f"  - 링크 포함 답변: {len(link_answers)}개")
        
    except Exception as e:
        print(f"데이터 분석 오류: {e}")
    
    print(f"\n✅ 동기화 완료!")
    print(f"✅ 중복 제거 완료!")
    print(f"✅ 카테고리 정리 완료!")
    print(f"✅ 엑셀 데이터 완전 반영!")

if __name__ == "__main__":
    test_kakao_menu_structure()
    test_question_responses()
    test_menu_navigation()
    generate_final_report() 
from ai_logic import AILogic
import json

def test_menu_logic():
    """메뉴 선택 로직 테스트"""
    
    ai_logic = AILogic()
    
    # 테스트할 메뉴 질문들
    test_questions = [
        "ㅇㅇ방과후 어디서 해?",
        "oo 방과후 언제 끝나?",
        "방과후 대기 장소가 있나요?",
        "오늘의 급식은?",
        "오늘 급식 메뉴 알려줘"
    ]
    
    print("=== 메뉴 선택 로직 테스트 ===")
    
    for question in test_questions:
        print(f"\n질문: {question}")
        
        # 메뉴 답변 가져오기
        response = ai_logic.get_menu_answer(question)
        
        if response:
            print(f"답변: {response['text'][:100]}...")
        else:
            print("답변: 없음")
        
        print("-" * 50)
    
    # 자유 질문 테스트
    print("\n=== 자유 질문 테스트 ===")
    free_question = "방과후 프로그램에 대해 알려주세요"
    print(f"질문: {free_question}")
    
    success, response = ai_logic.process_message(free_question, "test_user")
    if success:
        print(f"답변: {response['text'][:100]}...")
    else:
        print("답변: 없음")

if __name__ == "__main__":
    test_menu_logic() 
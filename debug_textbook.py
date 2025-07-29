from ai_logic import AILogic
import json

print("=== 교과서 매칭 디버깅 ===")

# AI 로직 테스트
ai = AILogic()

# process_message 직접 호출
success, response = ai.process_message("교과서정보", "test_user")
print(f"process_message 결과: success={success}")
print(f"response: {response}")

# 각 단계별 확인
print("\n=== 단계별 확인 ===")

# 1. 금지된 내용 확인
print("1. 금지된 내용 확인:")
banned = ai.is_banned_content("교과서정보")
print(f"  금지됨: {banned}")

# 2. 학교 관련 확인
print("2. 학교 관련 확인:")
school_related = ai.is_school_related("교과서정보")
print(f"  학교 관련: {school_related}")

# 3. 급식 관련 확인
print("3. 급식 관련 확인:")
meal_keywords = ["급식", "식단", "밥", "점심", "메뉴"]
has_meal = any(keyword in "교과서정보" for keyword in meal_keywords)
print(f"  급식 관련: {has_meal}")

# 4. 공지사항 관련 확인
print("4. 공지사항 관련 확인:")
notice_keywords = ["공지", "알림", "소식", "뉴스"]
has_notice = any(keyword in "교과서정보" for keyword in notice_keywords)
print(f"  공지사항 관련: {has_notice}")

# 5. 유치원 관련 확인
print("5. 유치원 관련 확인:")
has_kindergarten = "유치원" in "교과서정보"
print(f"  유치원 관련: {has_kindergarten}")

# 6. 간단한 응답 확인
print("6. 간단한 응답 확인:")
simple_keywords = ["안녕", "도움", "감사", "고마워", "뭐해", "잘 있어"]
has_simple = any(keyword in "교과서정보" for keyword in simple_keywords)
print(f"  간단한 응답: {has_simple}")

# 7. QA 매칭 확인
print("7. QA 매칭 확인:")
qa_match = ai.find_qa_match("교과서정보")
print(f"  QA 매칭: {qa_match is not None}")

# 8. 카테고리 매칭 확인
print("8. 카테고리 매칭 확인:")
ai._ensure_initialized()
if "교과서" in "교과서정보":
    for qa_item in ai.qa_data:
        category = qa_item.get('category', '').lower()
        if '교과서' in category:
            print(f"  카테고리 매칭됨: {category}")
            break
    else:
        print("  카테고리 매칭 안됨")
else:
    print("  교과서 키워드 매칭 안됨") 
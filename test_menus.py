from ai_logic import AILogic

ai = AILogic()

print('=== 메뉴 테스트 ===')
tests = ['급식', '방과후', '상담문의', '교과서정보']

for test in tests:
    success, response = ai.process_message(test, "test_user")
    if success:
        text = response.get("text", "실패")
        print(f'{test}: {text[:50]}...')
    else:
        print(f'{test}: 실패')
    print() 
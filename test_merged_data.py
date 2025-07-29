from ai_logic import AILogic

ai = AILogic()

print('=== 통합된 데이터 테스트 ===')
tests = ['방과후', '유치원', '급식', '교과서정보']

for test in tests:
    success, response = ai.process_message(test, "test_user")
    if success:
        text = response.get("text", "실패")
        print(f'{test}: {text[:100]}...')
        if 'link' in response:
            print(f'  링크: {response["link"]}')
    else:
        print(f'{test}: 실패')
    print() 
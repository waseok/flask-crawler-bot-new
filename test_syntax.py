import ast

try:
    with open('ai_logic.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    ast.parse(content)
    print("✅ 문법 오류 없음")
except SyntaxError as e:
    print(f"❌ 문법 오류: {e}")
    print(f"라인 {e.lineno}: {e.text}")
except Exception as e:
    print(f"❌ 기타 오류: {e}") 
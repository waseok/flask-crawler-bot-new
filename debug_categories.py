import json

# 데이터 로드
with open('school_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("교과서 관련 카테고리:")
for item in data:
    if '교과서' in item.get('category', ''):
        print(f"카테고리: {item.get('category', 'N/A')}")
        print(f"질문: {item['question']}")
        print(f"답변: {item['answer'][:50]}...")
        print()

print("모든 카테고리:")
categories = set()
for item in data:
    categories.add(item.get('category', 'N/A'))

for cat in sorted(categories):
    print(f"- {cat}") 
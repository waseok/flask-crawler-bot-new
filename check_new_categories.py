import json

# 데이터 로드
with open('school_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("새로 통합된 데이터 카테고리:")
categories = {}
for item in data:
    cat = item.get('category', 'N/A')
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(item['question'])

print(f"총 {len(data)}개 항목, {len(categories)}개 카테고리")
print()

for cat, questions in sorted(categories.items()):
    print(f"=== {cat} ===")
    print(f"질문 수: {len(questions)}")
    for i, q in enumerate(questions[:3]):  # 처음 3개만
        print(f"  {i+1}. {q}")
    if len(questions) > 3:
        print(f"  ... 외 {len(questions)-3}개")
    print() 
import json

def check_data_consistency():
    """category_questions.json과 school_dataset.json의 일치성 확인"""
    
    try:
        # category_questions.json 로드
        with open('category_questions.json', 'r', encoding='utf-8') as f:
            category_questions = json.load(f)
        
        # school_dataset.json 로드
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            school_dataset = json.load(f)
        
        print("=== 데이터 일치성 확인 ===")
        
        # school_dataset에서 질문 목록 추출
        school_questions = {item['question']: item for item in school_dataset}
        
        total_missing = 0
        total_found = 0
        
        for category, questions in category_questions.items():
            print(f"\n📁 {category}:")
            missing_count = 0
            found_count = 0
            
            for question in questions:
                if question in school_questions:
                    found_count += 1
                    print(f"  ✅ {question}")
                else:
                    missing_count += 1
                    print(f"  ❌ {question} (school_dataset.json에 없음)")
            
            total_missing += missing_count
            total_found += found_count
            print(f"  📊 찾음: {found_count}, 없음: {missing_count}")
        
        print(f"\n=== 전체 결과 ===")
        print(f"총 질문 수: {total_found + total_missing}")
        print(f"찾은 질문: {total_found}")
        print(f"없는 질문: {total_missing}")
        print(f"일치율: {total_found/(total_found + total_missing)*100:.1f}%")
        
        if total_missing == 0:
            print("🎉 모든 질문이 일치합니다!")
        else:
            print("⚠️ 일부 질문이 school_dataset.json에 없습니다.")
        
        return True
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = check_data_consistency()
    if success:
        print("\n✅ 데이터 일치성 확인 완료!")
    else:
        print("\n❌ 확인 실패") 
import json
import re

def categorize_questions():
    """질문들을 카톡 메뉴 카테고리에 맞게 분류"""
    print("=== 카테고리 구조 수정 ===\n")
    
    # 카톡 메뉴 구조
    kakao_categories = {
        "유치원운영시간": ["운영시간", "운영 시간", "유치원 운영"],
        "유치원방과후": ["유치원 방과후", "유치원 돌봄", "유치원 늘봄"],
        "유치원상담문의": ["유치원 상담", "유치원 문의", "유치원 연락"],
        "급식": ["급식", "식단", "메뉴", "오늘 급식", "이번주 급식"],
        "방과후": ["방과후", "늘봄", "돌봄", "방과후학교"],
        "상담문의": ["상담", "문의", "연락", "담임", "전화"],
        "학교시설": ["시설", "건물", "교실", "체육관", "도서관", "분실물"],
        "등하교교통": ["등교", "하교", "버스", "교통", "픽업"],
        "서류증명서": ["서류", "증명서", "재학증명서", "생활기록부"],
        "교과서정보": ["교과서", "출판사", "구매", "도서"],
        "시간일정": ["시간", "일정", "하교시간", "시정표"],
        "보건건강": ["보건", "건강", "결석", "질병", "감염병"],
        "체험학습": ["체험학습", "현장학습", "교외체험"],
        "방학휴가": ["방학", "휴가", "방학중", "휴업일"]
    }
    
    # 데이터 로드
    with open('school_dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"총 질문 수: {len(data)}")
    
    # 카테고리별로 분류
    categorized_data = []
    uncategorized = []
    
    for item in data:
        question = item['question'].lower()
        answer = item['answer']
        
        # 카테고리 매칭
        matched_category = None
        for category, keywords in kakao_categories.items():
            for keyword in keywords:
                if keyword in question:
                    matched_category = category
                    break
            if matched_category:
                break
        
        if matched_category:
            item['category'] = matched_category
            categorized_data.append(item)
        else:
            # 매칭되지 않은 질문들은 적절한 카테고리로 수동 분류
            if any(word in question for word in ["유치원", "유아"]):
                item['category'] = "유치원상담문의"
            elif any(word in question for word in ["학교", "전화", "번호"]):
                item['category'] = "상담문의"
            elif any(word in question for word in ["졸업", "학사일정"]):
                item['category'] = "시간일정"
            elif any(word in question for word in ["수익자", "비용", "교육비"]):
                item['category'] = "상담문의"
            else:
                item['category'] = "상담문의"  # 기본값
            categorized_data.append(item)
    
    # 카테고리별 통계
    category_stats = {}
    for item in categorized_data:
        cat = item['category']
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    print("\n카테고리별 분류 결과:")
    for category, count in sorted(category_stats.items()):
        print(f"  {category}: {count}개")
    
    # JSON 파일로 저장
    with open('school_dataset_categorized.json', 'w', encoding='utf-8') as f:
        json.dump(categorized_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n카테고리 분류 완료: school_dataset_categorized.json")
    print(f"총 질문 수: {len(categorized_data)}")
    
    return categorized_data

def backup_and_replace():
    """백업 후 새로운 데이터로 교체"""
    import shutil
    from datetime import datetime
    
    # 백업
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"school_dataset_backup_{timestamp}.json"
    shutil.copy('school_dataset.json', backup_file)
    print(f"백업 완료: {backup_file}")
    
    # 교체
    shutil.copy('school_dataset_categorized.json', 'school_dataset.json')
    print("데이터 교체 완료")

if __name__ == "__main__":
    categorized_data = categorize_questions()
    backup_and_replace()
    print("\n✅ 카테고리 구조 수정 완료!") 
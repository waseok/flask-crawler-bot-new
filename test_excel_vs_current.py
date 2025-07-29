import pandas as pd
import json
import re
from collections import defaultdict

def load_excel_data():
    """엑셀 파일에서 질문 데이터 로드"""
    try:
        # 엑셀 파일 읽기
        excel_file = "와석초_개선된QA_데이터_20250718_091247.xlsx"
        xl = pd.ExcelFile(excel_file)
        
        excel_questions = []
        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if '질문' in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row['질문']):
                            excel_questions.append({
                                'question': str(row['질문']).strip(),
                                'answer': str(row['답변']).strip() if '답변' in df.columns and pd.notna(row['답변']) else '',
                                'sheet': sheet_name
                            })
            except Exception as e:
                print(f"시트 {sheet_name} 읽기 오류: {e}")
        
        return excel_questions
    except Exception as e:
        print(f"엑셀 파일 읽기 오류: {e}")
        return []

def load_current_data():
    """현재 시스템의 JSON 데이터 로드"""
    try:
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"JSON 파일 읽기 오류: {e}")
        return []

def normalize_text(text):
    """텍스트 정규화 (공백, 특수문자 제거)"""
    if not text:
        return ""
    # 공백 제거, 소문자 변환
    normalized = re.sub(r'\s+', '', text.lower())
    # 특수문자 제거
    normalized = re.sub(r'[^\w가-힣]', '', normalized)
    return normalized

def compare_questions():
    """엑셀과 현재 시스템의 질문 비교"""
    print("=== 엑셀 vs 현재 시스템 질문 비교 ===\n")
    
    # 데이터 로드
    excel_data = load_excel_data()
    current_data = load_current_data()
    
    print(f"엑셀 질문 수: {len(excel_data)}")
    print(f"현재 시스템 질문 수: {len(current_data)}")
    print()
    
    # 엑셀 질문 정규화
    excel_normalized = {}
    for item in excel_data:
        norm_question = normalize_text(item['question'])
        if norm_question:
            excel_normalized[norm_question] = item
    
    # 현재 시스템 질문 정규화
    current_normalized = {}
    for item in current_data:
        norm_question = normalize_text(item['question'])
        if norm_question:
            current_normalized[norm_question] = item
    
    # 공통 질문 찾기
    common_questions = set(excel_normalized.keys()) & set(current_normalized.keys())
    excel_only = set(excel_normalized.keys()) - set(current_normalized.keys())
    current_only = set(current_normalized.keys()) - set(excel_normalized.keys())
    
    print(f"공통 질문 수: {len(common_questions)}")
    print(f"엑셀에만 있는 질문 수: {len(excel_only)}")
    print(f"현재 시스템에만 있는 질문 수: {len(current_only)}")
    print()
    
    # 엑셀에만 있는 질문들 출력
    if excel_only:
        print("=== 엑셀에만 있는 질문들 ===")
        for norm_q in sorted(list(excel_only)[:20]):  # 처음 20개만
            original_q = excel_normalized[norm_q]['question']
            sheet = excel_normalized[norm_q]['sheet']
            print(f"[{sheet}] {original_q}")
        if len(excel_only) > 20:
            print(f"... 외 {len(excel_only) - 20}개 더")
        print()
    
    # 현재 시스템에만 있는 질문들 출력
    if current_only:
        print("=== 현재 시스템에만 있는 질문들 ===")
        for norm_q in sorted(list(current_only)[:20]):  # 처음 20개만
            original_q = current_normalized[norm_q]['question']
            category = current_normalized[norm_q].get('category', 'N/A')
            print(f"[{category}] {original_q}")
        if len(current_only) > 20:
            print(f"... 외 {len(current_only) - 20}개 더")
        print()
    
    # 카테고리별 분석
    print("=== 카테고리별 분석 ===")
    excel_categories = defaultdict(int)
    current_categories = defaultdict(int)
    
    for item in excel_data:
        excel_categories[item['sheet']] += 1
    
    for item in current_data:
        current_categories[item.get('category', 'N/A')] += 1
    
    print("엑셀 카테고리별 질문 수:")
    for category, count in sorted(excel_categories.items()):
        print(f"  {category}: {count}")
    
    print("\n현재 시스템 카테고리별 질문 수:")
    for category, count in sorted(current_categories.items()):
        print(f"  {category}: {count}")
    
    # 답변 길이 비교
    print("\n=== 답변 길이 비교 ===")
    excel_answers = [len(item['answer']) for item in excel_data if item['answer']]
    current_answers = [len(item['answer']) for item in current_data if item['answer']]
    
    if excel_answers:
        print(f"엑셀 답변 평균 길이: {sum(excel_answers) / len(excel_answers):.1f}자")
        print(f"엑셀 답변 최대 길이: {max(excel_answers)}자")
        print(f"엑셀 답변 최소 길이: {min(excel_answers)}자")
    
    if current_answers:
        print(f"현재 시스템 답변 평균 길이: {sum(current_answers) / len(current_answers):.1f}자")
        print(f"현재 시스템 답변 최대 길이: {max(current_answers)}자")
        print(f"현재 시스템 답변 최소 길이: {min(current_answers)}자")

def test_specific_questions():
    """특정 질문들에 대한 응답 테스트"""
    print("\n=== 특정 질문 응답 테스트 ===")
    
    # 테스트할 질문들
    test_questions = [
        "ㅇㅇ방과후 어디서 해?",
        "oo 방과후 언제 끝나?",
        "방과후 대기 장소가 있나요?",
        "방과후학교 (추가)신청은 어떻게 하나요?",
        "늘봄교실/돌봄교실/방과후학교 차이가 뭔가요?",
        "방학중 방과후과정을 운영하나요?",
        "방과후 과정의 경우 몇시부터 하원할 수 있나요?",
        "오늘 급식 메뉴는?",
        "교과서 어디서 살수있어",
        "X학년 언제끝나?"
    ]
    
    current_data = load_current_data()
    current_normalized = {}
    for item in current_data:
        norm_question = normalize_text(item['question'])
        if norm_question:
            current_normalized[norm_question] = item
    
    for question in test_questions:
        norm_q = normalize_text(question)
        if norm_q in current_normalized:
            answer = current_normalized[norm_q]['answer']
            category = current_normalized[norm_q].get('category', 'N/A')
            print(f"✅ [{category}] {question}")
            print(f"   답변: {answer[:100]}...")
        else:
            print(f"❌ {question} - 매칭되는 답변 없음")
        print()

if __name__ == "__main__":
    compare_questions()
    test_specific_questions() 
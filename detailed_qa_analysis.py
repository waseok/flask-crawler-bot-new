import pandas as pd
import json
import re
from collections import defaultdict

def load_excel_data():
    """엑셀 파일에서 질문 데이터 로드"""
    try:
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

def analyze_missing_questions():
    """엑셀에만 있는 질문들 상세 분석"""
    print("=== 엑셀에만 있는 질문들 상세 분석 ===\n")
    
    excel_data = load_excel_data()
    current_data = load_current_data()
    
    # 현재 시스템 질문 정규화
    current_questions = set()
    for item in current_data:
        question = item['question'].strip().lower()
        current_questions.add(question)
    
    # 엑셀에만 있는 질문들 찾기
    missing_questions = []
    for item in excel_data:
        question = item['question'].strip().lower()
        if question not in current_questions:
            missing_questions.append(item)
    
    print(f"엑셀에만 있는 질문 수: {len(missing_questions)}")
    print()
    
    # 카테고리별로 분류
    missing_by_category = defaultdict(list)
    for item in missing_questions:
        missing_by_category[item['sheet']].append(item)
    
    for category, questions in missing_by_category.items():
        print(f"=== {category} ({len(questions)}개) ===")
        for item in questions:
            print(f"질문: {item['question']}")
            if item['answer']:
                print(f"답변: {item['answer'][:100]}...")
            print()
    
    return missing_questions

def analyze_duplicate_questions():
    """중복 질문 분석"""
    print("=== 중복 질문 분석 ===\n")
    
    current_data = load_current_data()
    
    # 질문별로 그룹화
    question_groups = defaultdict(list)
    for item in current_data:
        question = item['question'].strip().lower()
        question_groups[question].append(item)
    
    # 중복이 있는 질문들 찾기
    duplicates = {q: items for q, items in question_groups.items() if len(items) > 1}
    
    print(f"중복 질문 수: {len(duplicates)}")
    print()
    
    for question, items in list(duplicates.items())[:10]:  # 처음 10개만
        print(f"질문: {question}")
        for i, item in enumerate(items, 1):
            print(f"  {i}. 카테고리: {item.get('category', 'N/A')}")
            print(f"     답변: {item['answer'][:50]}...")
        print()

def analyze_answer_quality():
    """답변 품질 분석"""
    print("=== 답변 품질 분석 ===\n")
    
    current_data = load_current_data()
    
    # 답변 길이별 분류
    short_answers = []  # 50자 이하
    medium_answers = []  # 51-150자
    long_answers = []  # 151자 이상
    
    for item in current_data:
        answer_length = len(item['answer'])
        if answer_length <= 50:
            short_answers.append(item)
        elif answer_length <= 150:
            medium_answers.append(item)
        else:
            long_answers.append(item)
    
    print(f"짧은 답변 (50자 이하): {len(short_answers)}개")
    print(f"중간 답변 (51-150자): {len(medium_answers)}개")
    print(f"긴 답변 (151자 이상): {len(long_answers)}개")
    print()
    
    # 짧은 답변들 출력
    print("=== 짧은 답변들 (50자 이하) ===")
    for item in short_answers[:10]:  # 처음 10개만
        print(f"질문: {item['question']}")
        print(f"답변: {item['answer']}")
        print(f"카테고리: {item.get('category', 'N/A')}")
        print()
    
    # 링크가 포함된 답변들
    link_answers = []
    for item in current_data:
        if 'http' in item['answer'] or '링크' in item['answer']:
            link_answers.append(item)
    
    print(f"링크가 포함된 답변: {len(link_answers)}개")
    print()

def test_ai_logic_responses():
    """AI 로직 응답 테스트"""
    print("=== AI 로직 응답 테스트 ===\n")
    
    try:
        from ai_logic import AILogic
        ai = AILogic()
        
        test_questions = [
            "ㅇㅇ방과후 어디서 해?",
            "oo 방과후 언제 끝나?",
            "방과후 대기 장소가 있나요?",
            "오늘 급식 메뉴는?",
            "교과서 어디서 살수있어",
            "X학년 언제끝나?",
            "학교 전화번호 알려줘",
            "유치원 운영시간",
            "방학중 방과후과정을 운영하나요?"  # 엑셀에만 있는 질문
        ]
        
        for question in test_questions:
            try:
                success, response = ai.process_message(question, 'test_user')
                print(f"질문: {question}")
                print(f"성공: {success}")
                if success and isinstance(response, dict):
                    if 'text' in response:
                        print(f"답변: {response['text'][:100]}...")
                    if 'link' in response:
                        print(f"링크: {response['link']}")
                else:
                    print(f"응답: {response}")
                print()
            except Exception as e:
                print(f"질문: {question}")
                print(f"오류: {e}")
                print()
    
    except ImportError:
        print("AI 로직 모듈을 불러올 수 없습니다.")

if __name__ == "__main__":
    analyze_missing_questions()
    analyze_duplicate_questions()
    analyze_answer_quality()
    test_ai_logic_responses() 
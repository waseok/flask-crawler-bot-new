import pandas as pd
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime

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
                                'category': sheet_name
                            })
            except Exception as e:
                print(f"시트 {sheet_name} 읽기 오류: {e}")
        
        return excel_questions
    except Exception as e:
        print(f"엑셀 파일 읽기 오류: {e}")
        return []

def normalize_text(text):
    """텍스트 정규화"""
    if not text:
        return ""
    normalized = re.sub(r'\s+', '', text.lower())
    normalized = re.sub(r'[^\w가-힣]', '', normalized)
    return normalized

def remove_duplicates(questions):
    """중복 질문 제거"""
    seen = set()
    unique_questions = []
    
    for item in questions:
        norm_question = normalize_text(item['question'])
        if norm_question not in seen:
            seen.add(norm_question)
            unique_questions.append(item)
        else:
            print(f"중복 제거: {item['question']} (카테고리: {item['category']})")
    
    return unique_questions

def sync_excel_to_system():
    """엑셀 데이터를 시스템에 동기화"""
    print("=== 엑셀 데이터 시스템 동기화 ===\n")
    
    # 엑셀 데이터 로드
    excel_data = load_excel_data()
    print(f"엑셀에서 로드된 질문 수: {len(excel_data)}")
    
    # 중복 제거
    unique_data = remove_duplicates(excel_data)
    print(f"중복 제거 후 질문 수: {len(unique_data)}")
    
    # 카테고리별 정리
    category_mapping = {
        '강화된_QA_데이터': '강화된_QA_데이터',
        '원본_QA_데이터': '원본_QA_데이터',
        '유치원_강화': '유치원_강화',
        '유치원운영시간': '유치원운영시간',
        '유치원방과후': '유치원방과후',
        '유치원상담문의': '유치원상담문의',
        '초등학교_강화': '초등학교_강화',
        '방과후': '방과후',
        '상담문의': '상담문의',
        '학교시설': '학교시설',
        '등하교교통': '등하교교통',
        '서류증명서': '서류증명서',
        '교과서정보': '교과서정보',
        '시간일정': '시간일정',
        '보건건강': '보건건강',
        '체험학습': '체험학습',
        '방학휴가': '방학휴가',
        '급식정보': '급식정보'
    }
    
    # 카테고리별 통계
    category_stats = defaultdict(int)
    for item in unique_data:
        category_stats[item['category']] += 1
    
    print("\n카테고리별 질문 수:")
    for category, count in sorted(category_stats.items()):
        print(f"  {category}: {count}")
    
    # JSON 파일로 저장
    output_file = 'school_dataset_synced.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n동기화 완료: {output_file}")
    print(f"총 질문 수: {len(unique_data)}")
    
    return unique_data

def backup_current_data():
    """현재 데이터 백업"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"school_dataset_backup_{timestamp}.json"
    
    try:
        shutil.copy('school_dataset.json', backup_file)
        print(f"현재 데이터 백업 완료: {backup_file}")
        return True
    except Exception as e:
        print(f"백업 실패: {e}")
        return False

def replace_current_data():
    """동기화된 데이터로 현재 데이터 교체"""
    try:
        shutil.copy('school_dataset_synced.json', 'school_dataset.json')
        print("현재 데이터 교체 완료")
        return True
    except Exception as e:
        print(f"데이터 교체 실패: {e}")
        return False

if __name__ == "__main__":
    # 백업
    if backup_current_data():
        # 동기화
        synced_data = sync_excel_to_system()
        
        # 교체
        if replace_current_data():
            print("\n✅ 엑셀 데이터 동기화 완료!")
        else:
            print("\n❌ 데이터 교체 실패")
    else:
        print("\n❌ 백업 실패로 동기화 중단") 
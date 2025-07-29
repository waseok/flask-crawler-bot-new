import pandas as pd
import json
import shutil
from datetime import datetime

def sync_final_excel():
    excel_file = '와석초_답변링크합침_최종.xlsx'
    
    try:
        print(f"최종 엑셀 파일 '{excel_file}'을 시스템에 동기화 중...")
        
        # 엑셀 파일 읽기
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        
        qa_data = []
        
        # 제외할 시트들
        exclude_sheets = ['강화된_QA_데이터', '원본_QA_데이터', '강화_통계', '크롤링_요약']
        
        for sheet_name, df in excel_data.items():
            if sheet_name in exclude_sheets:
                continue
                
            print(f"처리 중: {sheet_name}")
            
            # 열 이름 확인
            if '질문' not in df.columns or '답변' not in df.columns:
                print(f"  필요한 열이 없음: {df.columns.tolist()}")
                continue
            
            # 데이터 처리
            for _, row in df.iterrows():
                question = row['질문']
                answer = row['답변']
                
                if pd.isna(question) or str(question).strip() == '':
                    continue
                
                # 카테고리 매핑
                category = sheet_name
                
                qa_item = {
                    'question': str(question).strip(),
                    'answer': str(answer).strip() if not pd.isna(answer) else '',
                    'category': category
                }
                
                qa_data.append(qa_item)
        
        # 중복 제거
        unique_qa = []
        seen_questions = set()
        
        for item in qa_data:
            question = item['question']
            if question not in seen_questions:
                unique_qa.append(item)
                seen_questions.add(question)
        
        print(f"\n총 {len(qa_data)}개 QA 항목 중 {len(unique_qa)}개 고유 항목 추출")
        
        # 백업 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f'school_dataset_backup_{timestamp}.json'
        shutil.copy('school_dataset.json', backup_file)
        print(f"백업 생성: {backup_file}")
        
        # 새 데이터 저장
        with open('school_dataset.json', 'w', encoding='utf-8') as f:
            json.dump(unique_qa, f, ensure_ascii=False, indent=2)
        
        print(f"✅ school_dataset.json 업데이트 완료!")
        print(f"총 {len(unique_qa)}개 QA 항목 저장됨")
        
        return True
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = sync_final_excel()
    if success:
        print("\n✅ 최종 엑셀 동기화 완료!")
    else:
        print("\n❌ 동기화 실패") 
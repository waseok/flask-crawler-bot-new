#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
엑셀에서 링크 추출하여 JSON 데이터에 추가
"""

import pandas as pd
import json
import re

def extract_links_from_excel():
    """엑셀에서 링크 추출하여 JSON에 추가"""
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel('와석초_개선된QA_데이터_20250718_091247.xlsx')
        print(f"엑셀 데이터 로드 완료: {len(df)}개 행")
        
        # JSON 데이터 로드
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        print(f"JSON 데이터 로드 완료: {len(qa_data)}개 항목")
        
        # 엑셀의 질문-링크 매핑 생성
        excel_qa_links = {}
        for _, row in df.iterrows():
            question = row['질문']
            link = row['링크']
            if pd.notna(link) and link.strip():
                excel_qa_links[question] = link.strip()
        
        print(f"엑셀에서 {len(excel_qa_links)}개의 링크를 찾았습니다.")
        
        # JSON 데이터에 링크 추가
        updated_count = 0
        for qa in qa_data:
            question = qa['question']
            
            # 엑셀에서 해당 질문의 링크 찾기
            if question in excel_qa_links:
                link = excel_qa_links[question]
                answer = qa['answer']
                
                # 이미 링크가 있는지 확인
                if not re.search(r'https?://', answer):
                    # "아래 링크에서 확인하실 수 있습니다" 패턴 찾기
                    link_patterns = [
                        "아래 링크에서 확인하실 수 있습니다",
                        "아래 링크에서 확인하실 수 있습니다!",
                        "자세한 내용은 아래 링크에서 확인하실 수 있습니다",
                        "자세한 내용은 아래 링크에서 확인하실 수 있습니다!",
                        "급식 정보는 아래 링크에서 확인하실 수 있습니다",
                        "방과후 프로그램 정보는 아래 링크에서 확인하실 수 있습니다",
                        "방과후 프로그램 정보는 아래 링크에서 확인하실 수 있습니다!",
                        "자세한 내용은 아래 링크를 참고해주세요"
                    ]
                    
                    for pattern in link_patterns:
                        if pattern in answer:
                            # 링크 추가
                            answer = answer.replace(pattern, f"{pattern}\n\n{link}")
                            qa['answer'] = answer
                            updated_count += 1
                            print(f"링크 추가: {question[:30]}... -> {link}")
                            break
        
        # 수정된 데이터 저장
        if updated_count > 0:
            with open('school_dataset.json', 'w', encoding='utf-8') as f:
                json.dump(qa_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ {updated_count}개 답변에 링크가 추가되었습니다.")
            
            # 백업 생성
            import shutil
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"school_dataset_backup_with_links_{timestamp}.json"
            shutil.copy('school_dataset.json', backup_filename)
            print(f"💾 백업 파일 생성: {backup_filename}")
        else:
            print("🔍 추가할 링크가 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    extract_links_from_excel() 
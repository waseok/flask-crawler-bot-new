#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import json
import os
from datetime import datetime

def extract_clean_data():
    """정리된 엑셀 파일에서 QA 데이터 추출"""
    
    # 정리된 엑셀 파일 찾기
    excel_files = [f for f in os.listdir('.') if f.startswith('와석초_정리된QA_데이터_') and f.endswith('.xlsx')]
    
    if not excel_files:
        print("정리된 엑셀 파일을 찾을 수 없습니다.")
        return
    
    # 가장 최근 파일 선택
    excel_file = sorted(excel_files)[-1]
    print(f"엑셀 파일 읽는 중: {excel_file}")
    
    # 엑셀 파일의 모든 시트 읽기
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    qa_data = []
    
    # 각 시트 처리
    for sheet_name, df in excel_data.items():
        print(f"시트 처리 중: {sheet_name}")
        
        # 시트가 QA 데이터를 포함하는지 확인
        if '질문' in df.columns and '답변' in df.columns:
            for index, row in df.iterrows():
                question = str(row['질문']).strip()
                answer = str(row['답변']).strip()
                
                # 빈 데이터 제외
                if question and answer and question != 'nan' and answer != 'nan':
                    qa_item = {
                        'question': question,
                        'answer': answer,
                        'category': sheet_name
                    }
                    qa_data.append(qa_item)
                    print(f"  - {question[:30]}...")
    
    # JSON 파일로 저장 (기존 파일 덮어쓰기)
    output_file = 'school_dataset.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(qa_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n총 {len(qa_data)}개의 QA 데이터를 {output_file}에 저장했습니다.")
    
    # 카테고리별 통계
    categories = {}
    for item in qa_data:
        cat = item['category']
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    print("\n카테고리별 통계:")
    for cat, count in categories.items():
        print(f"  {cat}: {count}개")
    
    # 개학/방학/시험 관련 데이터가 남아있는지 확인
    check_keywords = ['개학', '방학', '시험', '졸업식', '입학식', '방학식']
    remaining_problematic = []
    
    for item in qa_data:
        question = item['question'].lower()
        answer = item['answer'].lower()
        
        for keyword in check_keywords:
            if keyword in question or keyword in answer:
                remaining_problematic.append(item)
                break
    
    if remaining_problematic:
        print(f"\n⚠️ 경고: {len(remaining_problematic)}개의 개학/방학/시험 관련 데이터가 여전히 남아있습니다:")
        for item in remaining_problematic[:5]:  # 처음 5개만 출력
            print(f"  - {item['question'][:50]}...")
        if len(remaining_problematic) > 5:
            print(f"  ... 외 {len(remaining_problematic)-5}개 더")
    else:
        print(f"\n✅ 모든 개학/방학/시험 관련 데이터가 성공적으로 제거되었습니다!")

if __name__ == "__main__":
    extract_clean_data() 
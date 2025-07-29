#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import json
import os

def create_category_questions():
    """각 카테고리별 질문 목록 생성"""
    
    # 엑셀 파일 찾기
    excel_files = [f for f in os.listdir('.') if f.startswith('와석초_') and f.endswith('.xlsx')]
    
    if not excel_files:
        print("엑셀 파일을 찾을 수 없습니다.")
        return
    
    # 가장 최근 파일 선택
    excel_file = sorted(excel_files)[-1]
    print(f"엑셀 파일 읽는 중: {excel_file}")
    
    # 엑셀 파일의 모든 시트 읽기
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    # 각 카테고리별 질문 목록 생성
    category_questions = {}
    
    for sheet_name, df in excel_data.items():
        if '질문' in df.columns and '답변' in df.columns:
            questions = []
            for index, row in df.dropna(subset=['질문', '답변']).iterrows():
                question = str(row['질문']).strip()
                if question and question != 'nan':
                    questions.append(question)
            
            if questions:
                category_questions[sheet_name] = questions
                print(f"{sheet_name}: {len(questions)}개 질문")
    
    # JSON 파일로 저장
    with open('category_questions.json', 'w', encoding='utf-8') as f:
        json.dump(category_questions, f, ensure_ascii=False, indent=2)
    
    print(f"\n총 {len(category_questions)}개 카테고리의 질문 목록을 category_questions.json에 저장했습니다.")
    
    return category_questions

if __name__ == "__main__":
    create_category_questions() 
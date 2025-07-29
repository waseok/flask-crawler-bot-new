#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def check_excel_sheets():
    """엑셀 파일의 모든 시트 확인"""
    
    # 엑셀 파일 찾기
    excel_files = [f for f in os.listdir('.') if f.startswith('와석초_') and f.endswith('.xlsx')]
    
    if not excel_files:
        print("엑셀 파일을 찾을 수 없습니다.")
        return
    
    # 가장 최근 파일 선택
    excel_file = sorted(excel_files)[-1]
    print(f"엑셀 파일 확인 중: {excel_file}")
    
    # 엑셀 파일의 모든 시트 읽기
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    print(f"\n=== 엑셀 파일 시트 분석 ===")
    print(f"총 시트 수: {len(excel_data)}")
    
    # 각 시트 분석
    for sheet_name, df in excel_data.items():
        print(f"\n시트: {sheet_name}")
        print(f"  컬럼: {list(df.columns)}")
        print(f"  행 수: {len(df)}")
        
        # QA 데이터가 있는지 확인
        if '질문' in df.columns and '답변' in df.columns:
            qa_count = len(df.dropna(subset=['질문', '답변']))
            print(f"  QA 데이터: {qa_count}개")
            
            # 샘플 질문들 출력
            if qa_count > 0:
                print(f"  샘플 질문들:")
                for i, row in df.dropna(subset=['질문', '답변']).head(3).iterrows():
                    question = str(row['질문'])[:50]
                    print(f"    - {question}...")
        else:
            print(f"  QA 데이터 없음")
    
    # 실제 QA 데이터가 있는 시트들만 필터링
    qa_sheets = {}
    for sheet_name, df in excel_data.items():
        if '질문' in df.columns and '답변' in df.columns:
            qa_count = len(df.dropna(subset=['질문', '답변']))
            if qa_count > 0:
                qa_sheets[sheet_name] = qa_count
    
    print(f"\n=== 실제 QA 데이터가 있는 시트들 ===")
    for sheet_name, count in qa_sheets.items():
        print(f"  {sheet_name}: {count}개")
    
    return qa_sheets

if __name__ == "__main__":
    check_excel_sheets() 
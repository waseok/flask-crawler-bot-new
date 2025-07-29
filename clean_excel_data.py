#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os
from datetime import datetime

def clean_excel_data():
    """엑셀 파일에서 개학, 방학, 시험 관련 데이터 제거"""
    
    # 기존 엑셀 파일 읽기
    excel_file = "와석초_강화된QA_데이터_20250718_084428.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"엑셀 파일을 찾을 수 없습니다: {excel_file}")
        return
    
    print("기존 엑셀 파일 읽는 중...")
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    # 제거할 키워드들
    remove_keywords = [
        '개학', '방학', '시험', '졸업식', '입학식', '방학식',
        '개학일', '방학일', '시험일', '졸업식일', '입학식일',
        '1학기', '2학기', '여름방학', '겨울방학', '봄방학',
        '중간고사', '기말고사', '시험기간', '시험일정'
    ]
    
    cleaned_data = {}
    total_removed = 0
    
    # 각 시트 처리
    for sheet_name, df in excel_data.items():
        print(f"시트 처리 중: {sheet_name}")
        
        if '질문' in df.columns and '답변' in df.columns:
            # 제거할 행 인덱스 찾기
            rows_to_remove = []
            
            for index, row in df.iterrows():
                question = str(row['질문']).lower()
                answer = str(row['답변']).lower()
                
                # 제거 키워드가 포함된 행 찾기
                for keyword in remove_keywords:
                    if keyword in question or keyword in answer:
                        rows_to_remove.append(index)
                        print(f"  제거: {row['질문'][:50]}...")
                        break
            
            # 제거할 행들 삭제
            if rows_to_remove:
                df_cleaned = df.drop(rows_to_remove)
                total_removed += len(rows_to_remove)
                print(f"  {len(rows_to_remove)}개 행 제거됨")
            else:
                df_cleaned = df
                print(f"  제거할 데이터 없음")
            
            cleaned_data[sheet_name] = df_cleaned
        else:
            # QA 데이터가 없는 시트는 그대로 복사
            cleaned_data[sheet_name] = df
    
    # 새로운 엑셀 파일 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_excel_file = f"와석초_정리된QA_데이터_{timestamp}.xlsx"
    
    with pd.ExcelWriter(new_excel_file, engine='openpyxl') as writer:
        for sheet_name, df in cleaned_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"\n정리 완료!")
    print(f"총 {total_removed}개의 개학/방학/시험 관련 데이터 제거됨")
    print(f"새 엑셀 파일: {new_excel_file}")
    
    return new_excel_file

if __name__ == "__main__":
    clean_excel_data() 
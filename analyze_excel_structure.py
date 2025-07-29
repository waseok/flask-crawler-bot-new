#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

def analyze_excel_structure():
    """엑셀 파일의 구조를 분석하여 카테고리별 메뉴 구조 파악"""
    
    # 정리된 엑셀 파일 찾기
    excel_files = [f for f in os.listdir('.') if f.startswith('와석초_정리된QA_데이터_') and f.endswith('.xlsx')]
    
    if not excel_files:
        print("정리된 엑셀 파일을 찾을 수 없습니다.")
        return
    
    # 가장 최근 파일 선택
    excel_file = sorted(excel_files)[-1]
    print(f"엑셀 파일 분석 중: {excel_file}")
    
    # 엑셀 파일의 모든 시트 읽기
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    
    print("\n=== 엑셀 파일 구조 분석 ===")
    print(f"총 시트 수: {len(excel_data)}")
    
    # QA 데이터가 있는 시트들만 필터링
    qa_sheets = {}
    
    for sheet_name, df in excel_data.items():
        if '질문' in df.columns and '답변' in df.columns:
            qa_count = len(df.dropna(subset=['질문', '답변']))
            qa_sheets[sheet_name] = qa_count
            print(f"  {sheet_name}: {qa_count}개 QA")
    
    print(f"\n=== QA 데이터가 있는 시트들 ===")
    for sheet_name, count in qa_sheets.items():
        print(f"  {sheet_name}: {count}개")
    
    # 메뉴 구조 제안
    print(f"\n=== 제안하는 카카오톡 메뉴 구조 ===")
    
    # 메인 카테고리 분류
    main_categories = {
        "유치원": [],
        "초등학교": []
    }
    
    for sheet_name in qa_sheets.keys():
        if "유치원" in sheet_name:
            main_categories["유치원"].append(sheet_name)
        else:
            main_categories["초등학교"].append(sheet_name)
    
    print("메인 메뉴:")
    print("  👶 유치원")
    print("  🏫 초등학교")
    
    print("\n유치원 서브 메뉴:")
    for sheet_name in main_categories["유치원"]:
        if sheet_name == "유치원운영시간":
            print(f"  ⏰ {sheet_name}")
        elif sheet_name == "유치원방과후":
            print(f"  🎨 {sheet_name}")
        elif sheet_name == "유치원상담문의":
            print(f"  📞 {sheet_name}")
        else:
            print(f"  📅 {sheet_name}")
    
    print("\n초등학교 서브 메뉴:")
    for sheet_name in main_categories["초등학교"]:
        if sheet_name == "급식정보":
            print(f"  🍽️ {sheet_name}")
        elif sheet_name == "방과후":
            print(f"  🎨 {sheet_name}")
        elif sheet_name == "상담문의":
            print(f"  📞 {sheet_name}")
        elif sheet_name == "더보기":
            print(f"  📋 {sheet_name}")
        else:
            print(f"  📅 {sheet_name}")
    
    return main_categories, qa_sheets

if __name__ == "__main__":
    analyze_excel_structure() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
현재 데이터베이스의 QA 데이터를 카테고리별로 구분하여 엑셀 파일로 내보내기
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os

def export_qa_to_excel():
    """QA 데이터를 카테고리별로 엑셀 파일로 내보내기"""
    
    print("📊 QA 데이터 엑셀 내보내기 시작...")
    
    # 데이터베이스 연결
    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    
    # 카테고리별 데이터 조회
    categories = ['초등', '유치원', '첨부파일']
    
    # ExcelWriter 객체 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"와석초_QA데이터_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        
        for category in categories:
            print(f"📝 {category} 카테고리 처리 중...")
            
            # 해당 카테고리의 데이터 조회
            cursor.execute('''
                SELECT id, question, answer, link, created_at 
                FROM qa_data 
                WHERE category = ? 
                ORDER BY id
            ''', (category,))
            
            results = cursor.fetchall()
            
            if results:
                # DataFrame 생성
                df = pd.DataFrame(results, columns=['ID', '질문', '답변', '링크', '생성일시'])
                
                # 시트에 저장
                df.to_excel(writer, sheet_name=category, index=False)
                
                print(f"  ✅ {category}: {len(results)}개 질문 추가")
            else:
                print(f"  ⚠️ {category}: 데이터 없음")
    
    conn.close()
    
    print(f"\n✅ 엑셀 파일 생성 완료!")
    print(f"📄 파일명: {excel_filename}")
    print(f"📁 저장 위치: {os.path.abspath(excel_filename)}")
    
    # 파일 크기 확인
    file_size = os.path.getsize(excel_filename)
    print(f"📏 파일 크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    return excel_filename

def show_qa_summary():
    """QA 데이터 요약 정보 표시"""
    
    print("\n📈 QA 데이터 요약:")
    
    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    
    # 전체 QA 수
    cursor.execute('SELECT COUNT(*) FROM qa_data')
    total_count = cursor.fetchone()[0]
    print(f"📊 전체 QA 수: {total_count}개")
    
    # 카테고리별 QA 수
    cursor.execute('''
        SELECT category, COUNT(*) 
        FROM qa_data 
        GROUP BY category 
        ORDER BY category
    ''')
    
    category_counts = cursor.fetchall()
    print(f"📋 카테고리별 분포:")
    for category, count in category_counts:
        print(f"   {category}: {count}개")
    
    # 링크가 있는 QA 수
    cursor.execute('SELECT COUNT(*) FROM qa_data WHERE link IS NOT NULL AND link != ""')
    link_count = cursor.fetchone()[0]
    print(f"🔗 링크 포함 QA: {link_count}개")
    
    conn.close()

if __name__ == "__main__":
    try:
        # QA 데이터 요약 표시
        show_qa_summary()
        
        # 엑셀 파일 생성
        excel_file = export_qa_to_excel()
        
        print(f"\n🎉 완료! 선생님께서 {excel_file} 파일을 편집하신 후")
        print("   다시 업로드하시면 데이터베이스가 자동으로 업데이트됩니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc() 
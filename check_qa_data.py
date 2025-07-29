#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_qa_data():
    """QA 데이터 확인"""
    
    conn = sqlite3.connect('school_data.db')
    cursor = conn.cursor()
    
    # 등하교/정차대/학교시설 관련 QA 확인
    keywords = ["등하교", "정차대", "학교시설"]
    
    for keyword in keywords:
        print(f"\n🔍 '{keyword}' 관련 QA:")
        cursor.execute('SELECT question, answer, link FROM qa_data WHERE question LIKE ? OR answer LIKE ?', 
                      (f'%{keyword}%', f'%{keyword}%'))
        results = cursor.fetchall()
        
        if results:
            for i, (question, answer, link) in enumerate(results, 1):
                print(f"  {i}. Q: {question}")
                print(f"     A: {answer}")
                print(f"     L: {link}")
                print()
        else:
            print(f"  ❌ '{keyword}' 관련 QA 없음")
    
    # 전체 QA 수 확인
    cursor.execute('SELECT COUNT(*) FROM qa_data')
    total = cursor.fetchone()[0]
    print(f"\n📊 전체 QA 수: {total}개")
    
    # 링크가 있는 QA 수 확인
    cursor.execute('SELECT COUNT(*) FROM qa_data WHERE link IS NOT NULL AND link != ""')
    link_count = cursor.fetchone()[0]
    print(f"🔗 링크 포함 QA: {link_count}개")
    
    # 자주 묻는 질문들 확인
    print(f"\n📋 자주 묻는 질문들 (메뉴에 추가할 후보):")
    cursor.execute('SELECT question FROM qa_data ORDER BY id LIMIT 20')
    frequent_questions = cursor.fetchall()
    
    for i, (question,) in enumerate(frequent_questions, 1):
        print(f"  {i}. {question}")
    
    conn.close()

if __name__ == "__main__":
    check_qa_data() 
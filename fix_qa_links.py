#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA 데이터 링크 수정 스크립트
"아래 링크에서 확인하실 수 있습니다" 텍스트에 실제 링크 추가
"""

import json
import re

# 와석초등학교 관련 실제 링크들
LINK_MAPPINGS = {
    # 학사일정 관련
    "학사일정은 아래 링크에서 확인하실 수 있습니다": "https://goepj.kr/",
    "학사일정은 아래 링크에서 확인하실 수 있습니다!": "https://goepj.kr/",
    
    # 급식 관련
    "급식 정보는 아래 링크에서 확인하실 수 있습니다": "https://goepj.kr/",
    
    # 교과서 관련
    "교과서 구매는 아래 링크에서 가능합니다": "https://ktbookmall.com/",
    "자세한 내용은 아래 링크에서 확인하실 수 있습니다!": "https://ktbookmall.com/",
    
    # 방과후 관련
    "방과후 프로그램 정보는 아래 링크에서 확인하실 수 있습니다": "https://goepj.kr/",
    "방과후 프로그램 정보는 아래 링크에서 확인하실 수 있습니다!": "https://goepj.kr/",
    
    # 일반적인 링크
    "자세한 내용은 아래 링크에서 확인하실 수 있습니다": "https://goepj.kr/",
    "자세한 내용은 아래 링크를 참고해주세요": "https://goepj.kr/"
}

def fix_qa_links():
    """QA 데이터의 링크 수정"""
    try:
        # QA 데이터 로드
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        print(f"QA 데이터 로드 완료: {len(qa_data)}개 항목")
        
        fixed_count = 0
        
        for qa in qa_data:
            answer = qa['answer']
            original_answer = answer
            
            # 링크 매핑 적용
            for text_pattern, url in LINK_MAPPINGS.items():
                if text_pattern in answer:
                    # 링크가 이미 있는지 확인
                    if not re.search(r'https?://', answer):
                        # 링크 추가
                        answer = answer.replace(text_pattern, f"{text_pattern}\n\n{url}")
                        fixed_count += 1
                        print(f"링크 추가: {qa['question'][:30]}...")
                        break
        
        # 수정된 데이터 저장
        if fixed_count > 0:
            with open('school_dataset.json', 'w', encoding='utf-8') as f:
                json.dump(qa_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ {fixed_count}개 답변에 링크가 추가되었습니다.")
            
            # 백업 생성
            import shutil
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"school_dataset_backup_before_links_{timestamp}.json"
            shutil.copy('school_dataset.json', backup_filename)
            print(f"💾 백업 파일 생성: {backup_filename}")
        else:
            print("🔍 수정할 링크가 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    fix_qa_links() 
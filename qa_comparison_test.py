#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA 데이터 비교 테스트 스크립트
현재 올라가 있는 질문/답변과 동일한 스크립트로 원래 답변과 비교
"""

import json
import requests
import time
from datetime import datetime

# 테스트할 질문 목록 (현재 QA 데이터에서 추출)
TEST_QUESTIONS = [
    "오늘의 급식은?",
    "오늘 급식 메뉴 알려줘", 
    "이번주 급식 메뉴 알려줘",
    "X학년 언제 끝나?",
    "교과서 어디서 살 수 있어요?",
    "O학년 교과서 출판사 어디인가요?",
    "체험학습보고서 양식 어디에 있나요?",
    "분실물 보관함은 어디있나요?",
    "전입, 전출 절차는어떻게 되나요?",
    "경조사로 인한 결석은 몇일까지 출석 인정되나요?",
    "3-5반 어디있어?",
    "학교 내선번호를 알고 싶어요",
    "주말에도 학교가 개방이 되나요?",
    "학교 시설을 사용하고 싶습니다. (체육관, 운동장 임대)",
    "갑자기 학생이 결석을 해야할 것 같은데 어떻게 해야하나요?",
    "재학증명서가 필요한데요?",
    "교사 면담 가능 시간",
    "교육비는 얼마인가요?",
    "유아학비 지원 기준은 무엇인가요?",
    "특수학급유아도 입학할 수 있나요?",
    "현장학습은 몇 번, 어디로 가나요?",
    "대기자는 어떻게 등록하나요?",
    "유아모집은 언제 시작하나요?",
    "ㅇㅇ방과후 어디서 해?",
    "oo 방과후 언제 끝나?",
    "방과후 대기 장소가 있나요?",
    "방과후학교 (추가)신청은 어떻게 하나요?",
    "늘봄 (추가)신청이 가능한가요?",
    "늘봄교실/돌봄교실/방과후학교 차이가 뭔가요?",
    "방학중 방과후과정을 운영하나요?",
    "담임 선생님과 직접 연락하고 싶은데 어떻게 하나요?",
    "생활기록부, 재학증명서는 어디서 발급 받을 수 있나요?",
    "담임선생님과 상담은 어떻게 할 수 있나요?",
    "전입/전출 시 필요한 서류가 있나요?",
    "담임선생님과 상담이 하고 싶어요",
    "학교폭력 관련하여 상담이 하고 싶어요",
    "와석초등학교로 전학을 오려고 하는데 어떻게 하면 되나요?",
    "전학 가려면 어떻게 해요?",
    "대회 참여를 위한 학교장 확인서는 어떻게 발급받나요?",
    "담임 선생님 연락처",
    "방과후 과정의 경우 몇시부터 하원할 수 있나요?",
    "유치원장 허가 교외 체험학습인정 일수",
    "유치원복을 입는 날이 정해져있나요?",
    "유치원 근처에 주,정차 할 수 있는 장소가 있나요?",
    "학원선생님과 하원이 가능한가요?",
    "유치원 운영 시간을 알고 싶어요"
]

def load_qa_data():
    """QA 데이터 로드"""
    try:
        with open('school_dataset.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"QA 데이터 로드 실패: {e}")
        return []

def find_qa_match(question, qa_data):
    """QA 데이터에서 질문 매칭"""
    for qa in qa_data:
        if qa['question'] == question:
            return qa
    return None

def test_chatbot_response(question):
    """챗봇 응답 테스트"""
    try:
        # 실제 챗봇 API 호출 (로컬 테스트용)
        url = "http://localhost:5000/webhook"
        payload = {
            "userRequest": {
                "utterance": question,
                "user": {
                    "id": "test_user_123"
                }
            }
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            # 카카오톡 응답 형식에서 텍스트 추출
            if 'template' in result and 'outputs' in result['template']:
                for output in result['template']['outputs']:
                    if 'simpleText' in output:
                        return output['simpleText']['text']
                    elif 'buttonCard' in output:
                        return output['buttonCard']['title']
            return "응답 형식 오류"
        else:
            return f"API 오류: {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return f"네트워크 오류: {e}"
    except Exception as e:
        return f"테스트 오류: {e}"

def compare_responses(original_answer, chatbot_response):
    """답변 비교"""
    # 간단한 유사도 체크
    original_words = set(original_answer.lower().split())
    chatbot_words = set(chatbot_response.lower().split())
    
    if len(original_words) == 0:
        return 0.0
    
    intersection = original_words.intersection(chatbot_words)
    similarity = len(intersection) / len(original_words)
    
    return similarity

def run_comparison_test():
    """전체 비교 테스트 실행"""
    print("=" * 80)
    print("QA 데이터 비교 테스트 시작")
    print("=" * 80)
    
    # QA 데이터 로드
    qa_data = load_qa_data()
    if not qa_data:
        print("❌ QA 데이터를 로드할 수 없습니다.")
        return
    
    print(f"✅ QA 데이터 로드 완료: {len(qa_data)}개 항목")
    
    # 결과 저장
    results = []
    total_similarity = 0.0
    successful_tests = 0
    
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}/{len(TEST_QUESTIONS)}] 테스트 중: {question}")
        
        # 원본 QA 데이터에서 답변 찾기
        qa_match = find_qa_match(question, qa_data)
        if not qa_match:
            print(f"❌ 원본 QA 데이터에서 질문을 찾을 수 없음: {question}")
            continue
        
        original_answer = qa_match['answer']
        print(f"📝 원본 답변: {original_answer[:100]}...")
        
        # 챗봇 응답 테스트
        chatbot_response = test_chatbot_response(question)
        print(f"🤖 챗봇 응답: {chatbot_response[:100]}...")
        
        # 답변 비교
        similarity = compare_responses(original_answer, chatbot_response)
        total_similarity += similarity
        successful_tests += 1
        
        print(f"📊 유사도: {similarity:.2f} ({similarity*100:.1f}%)")
        
        # 결과 저장
        result = {
            "question": question,
            "original_answer": original_answer,
            "chatbot_response": chatbot_response,
            "similarity": similarity,
            "category": qa_match.get('category', 'Unknown')
        }
        results.append(result)
        
        # API 호출 간격 조절
        time.sleep(1)
    
    # 전체 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    if successful_tests > 0:
        avg_similarity = total_similarity / successful_tests
        print(f"✅ 성공한 테스트: {successful_tests}/{len(TEST_QUESTIONS)}")
        print(f"📊 평균 유사도: {avg_similarity:.2f} ({avg_similarity*100:.1f}%)")
        
        # 유사도별 분류
        high_similarity = [r for r in results if r['similarity'] >= 0.7]
        medium_similarity = [r for r in results if 0.4 <= r['similarity'] < 0.7]
        low_similarity = [r for r in results if r['similarity'] < 0.4]
        
        print(f"🟢 높은 유사도 (≥70%): {len(high_similarity)}개")
        print(f"🟡 중간 유사도 (40-69%): {len(medium_similarity)}개")
        print(f"🔴 낮은 유사도 (<40%): {len(low_similarity)}개")
        
        # 문제가 있는 답변들 출력
        if low_similarity:
            print(f"\n🔴 낮은 유사도 답변들:")
            for result in low_similarity:
                print(f"  - {result['question']} (유사도: {result['similarity']:.2f})")
        
    else:
        print("❌ 성공한 테스트가 없습니다.")
    
    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"qa_comparison_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "test_info": {
                "timestamp": timestamp,
                "total_questions": len(TEST_QUESTIONS),
                "successful_tests": successful_tests,
                "average_similarity": total_similarity / successful_tests if successful_tests > 0 else 0
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과가 {filename}에 저장되었습니다.")

if __name__ == "__main__":
    run_comparison_test() 
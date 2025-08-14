import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

# 한국 시간대 설정 (UTC+9) - 표시용만
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간 반환 (표시용)"""
    return datetime.now(KST)

class DatabaseManager:
    def __init__(self, db_path: str = None):
        """
        db_path가 명시되지 않으면, 이 파일(database.py)과 같은 폴더의 school_data.db를 절대경로로 사용.
        (Render 등 배포 환경에서 상대경로 문제 방지)
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = db_path or os.path.join(base_dir, "school_data.db")
        self.init_database()
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # QA 데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 대화 히스토리 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 식단 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meal_type TEXT,
                menu TEXT,
                image_url TEXT
            )
        ''')
        
        # 공지사항 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT,
                created_at TEXT,
                tags TEXT,
                category TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_qa_data(self, category: Optional[str] = None) -> List[Dict]:
        """QA 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute('SELECT * FROM qa_data WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT * FROM qa_data')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'category': row[1],
                'question': row[2],
                'answer': row[3],
                'link': row[4],
                'created_at': row[5]
            }
            for row in results
        ]
    
    def save_conversation(self, user_id: str, message: str, response):
        """대화 히스토리 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # response가 dict인 경우 텍스트로 변환
        if isinstance(response, dict):
            if response.get("type") == "image":
                response_text = f"[이미지] {response.get('text', '')}"
            else:
                response_text = response.get("text", str(response))
        else:
            response_text = str(response)
        
        cursor.execute(
            'INSERT INTO conversation_history (user_id, message, response) VALUES (?, ?, ?)',
            (user_id, message, response_text)
        )
        
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict]:
        """사용자별 대화 히스토리 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM conversation_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, limit)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'user_id': row[1],
                'message': row[2],
                'response': row[3],
                'timestamp': row[4]
            }
            for row in results
        ]
    
    def get_meal_info(self, date: str) -> Optional[str]:
        """특정 날짜의 식단 정보 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT menu FROM meals WHERE date = ? AND meal_type = "중식"', (date,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else None
    
    def get_latest_notices(self, limit: int = 5) -> List[Dict]:
        """최신 공지사항 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM notices ORDER BY created_at DESC LIMIT ?', (limit,))
        results = cursor.fetchall()
        
        conn.close()
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'created_at': row[4],
                'tags': row[5],
                'category': row[6]
            }
            for row in results
        ]

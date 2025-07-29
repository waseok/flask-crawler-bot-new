# 와석초 카카오톡 챗봇

와석초등학교를 위한 AI 기반 카카오톡 챗봇입니다. OpenAI GPT를 활용하여 학교 관련 질문에 대해 정확하고 유용한 답변을 제공합니다.

## 🚀 주요 기능

- **AI 기반 답변**: OpenAI GPT를 활용한 지능형 대화
- **학교 데이터베이스 연동**: SQLite 기반 학교 정보 관리
- **대화 히스토리 관리**: 사용자별 대화 기록 저장
- **금지 단어 필터링**: 부적절한 내용 자동 필터링
- **퀵 리플라이 버튼**: 자주 묻는 질문에 대한 빠른 답변
- **헬스 체크**: 시스템 상태 모니터링
- **통계 기능**: 사용량 및 성능 통계 제공

## 📁 프로젝트 구조

```
new/
├── app.py                      # 메인 애플리케이션
├── config.py                   # 설정 파일
├── logic/
│   ├── bot_logic.py           # 챗봇 로직
│   └── prompt.txt             # AI 프롬프트
├── utils.py                   # 유틸리티 함수
├── data_migration_enhanced.py # 데이터 마이그레이션
├── requirements.txt           # 의존성 패키지
├── render.yaml               # Render 배포 설정
└── school_data.db            # 학교 데이터베이스
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
export OPENAI_API_KEY="your_openai_api_key"
export KAKAO_BOT_TOKEN="your_kakao_bot_token"
```

### 3. 애플리케이션 실행
```bash
python app.py
```

### 4. Render 배포 (권장)
- GitHub에 코드 푸시
- Render에서 저장소 연결
- 환경 변수 설정 후 자동 배포

## 📊 데이터베이스 구조

### qa_data 테이블
- `id`: 고유 식별자
- `category`: 카테고리 (초등/유치원/첨부파일)
- `question`: 질문
- `answer`: 답변
- `link`: 관련 링크
- `image_reference`: 이미지 참조
- `created_at`: 생성 시간

## 🔧 API 엔드포인트

### 카카오톡 챗봇
- `POST /`: 카카오톡 메시지 처리

### 관리 기능
- `GET /health`: 헬스 체크
- `GET /stats`: 사용 통계
- `GET /qa`: QA 데이터 조회

## 📈 데이터 통계

- **전체 데이터**: 85개
- **초등**: 51개 질문-답변
- **유치원**: 26개 질문-답변
- **첨부파일**: 8개 참조 정보

## 🚀 배포

### Render 배포
1. Render 계정 생성
2. GitHub 저장소 연결
3. `render.yaml` 설정으로 자동 배포

### 환경 변수 설정
- `OPENAI_API_KEY`: OpenAI API 키
- `PORT`: 포트 번호 (기본값: 5000)

## 📝 업데이트 로그

### v2.0.0 (2024-07-02)
- OpenAI GPT 기반 AI 로직 개선
- 대화 히스토리 관리 추가
- 금지 단어 필터링 기능
- 퀵 리플라이 버튼 지원
- 헬스 체크 및 통계 엔드포인트
- 모든 시트 데이터 마이그레이션 (초등, 유치원, 첨부파일)

### v1.0.0
- 기본 카카오톡 챗봇 기능
- SQLite 데이터베이스 연동

## 🤝 기여

프로젝트 개선을 위한 제안이나 버그 리포트는 언제든 환영합니다.

## 📄 라이선스

이 프로젝트는 교육 목적으로 개발되었습니다. 
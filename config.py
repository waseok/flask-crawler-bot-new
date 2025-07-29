import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI 설정
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

# 카카오톡 설정
KAKAO_API_KEY = os.environ.get("KAKAO_API_KEY")
KAKAO_BOT_TOKEN = os.environ.get("KAKAO_BOT_TOKEN")

# 서버 설정
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# AI 설정
TEMPERATURE = float(os.environ.get("TEMPERATURE", 0.7))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 150))
TOP_P = float(os.environ.get("TOP_P", 1.0))

# 금지 단어 목록
BAN_WORDS = ["욕설", "비속어", "폭력", "자살", "살인", "테러"] 
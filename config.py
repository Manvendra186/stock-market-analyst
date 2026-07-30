"""
Configuration for NYX Stock Market Expert Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ───
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))  # Your Telegram user ID

# ─── LLM (Local Model via LM Studio) ───
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-27b")  # Adjust to your loaded model name
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# ─── Stock Data ───
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

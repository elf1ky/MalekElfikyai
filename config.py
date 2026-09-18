import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_PATH = "edu_platform.db"

# Turso (Cloud SQLite) - Optional
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

# Groq API via OpenAI client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-20b"

# App Config
APP_NAME = "🎓 منصة التعلم الذكي"
APP_ICON = "🎓"
PAGE_CONFIG = {
    "page_title": "MalekElfikyAI",
    "page_icon": "logo_teacher_teal.png",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Theme Colors
PRIMARY_COLOR = "#4F46E5"
SECONDARY_COLOR = "#10B981"
BACKGROUND_COLOR = "#F8FAFC"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#1E293B"

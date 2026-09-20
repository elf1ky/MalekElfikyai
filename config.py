import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_PATH = "edu_platform.db"
# now that i am deploying the app i am not using env anymore 
def _get_secret(name):
    # Works locally (reads .env) AND on Streamlit Cloud (reads Secrets)
    return os.getenv(name) or st.secrets.get(name, "")

TURSO_DATABASE_URL = _get_secret("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = _get_secret("TURSO_AUTH_TOKEN")
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

GROQ_API_KEY = _get_secret("GROQ_API_KEY")
# Groq API via OpenAI client
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

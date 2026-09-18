"""
أدوات الأمان والحماية
"""
import re
import time
from functools import wraps
import streamlit as st

# ========== Teacher Registration Code ==========
# غيّر هذا الرقم السري! لا تعطِه إلا للمعلمين
TEACHER_SECRET_CODE = "EDU2026"  # ← غيّره لرقم سري قوي

def verify_teacher_code(code: str) -> bool:
    """التحقق من كود المعلم السري"""
    return code == TEACHER_SECRET_CODE

# ========== Rate Limiting for Login ==========
# يخزن محاولات تسجيل الدخول الفاشلة
_login_attempts = {}

def check_rate_limit(identifier: str, max_attempts: int = 5, window_seconds: int = 300) -> bool:
    """
    التحقق من عدم تجاوز الحد المسموح
    identifier: اسم المستخدم أو IP
    max_attempts: عدد المحاولات المسموحة (5)
    window_seconds: الفترة الزمنية (5 دقائق)
    """
    now = time.time()

    if identifier not in _login_attempts:
        _login_attempts[identifier] = []

    # إزالة المحاولات القديمة
    _login_attempts[identifier] = [
        t for t in _login_attempts[identifier] 
        if now - t < window_seconds
    ]

    if len(_login_attempts[identifier]) >= max_attempts:
        return False  # تم تجاوز الحد

    _login_attempts[identifier].append(now)
    return True

def record_failed_login(identifier: str):
    """تسجيل محاولة فاشلة"""
    now = time.time()
    if identifier not in _login_attempts:
        _login_attempts[identifier] = []
    _login_attempts[identifier].append(now)

# ========== Input Validation ==========

def sanitize_input(text: str, max_length: int = 5000) -> str:
    """تنظيف المدخلات من المستخدم"""
    if not text:
        return ""
    # إزالة HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # تقصير النص
    text = text[:max_length]
    return text.strip()

def validate_username(username: str) -> tuple:
    """
    التحقق من صحة اسم المستخدم
    ترجع: (صحيح/خطأ, رسالة الخطأ)
    """
    if not username:
        return False, "اسم المستخدم مطلوب"
    if len(username) < 3:
        return False, "اسم المستخدم يجب أن يكون 3 أحرف على الأقل"
    if len(username) > 30:
        return False, "اسم المستخدم طويل جداً"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام و _ فقط"
    return True, ""

def validate_password(password: str) -> tuple:
    """
    التحقق من قوة كلمة المرور
    """
    if not password:
        return False, "كلمة المرور مطلوبة"
    if len(password) < 6:
        return False, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
    if len(password) > 128:
        return False, "كلمة المرور طويلة جداً"
    return True, ""

# ========== File Upload Validation ==========

ALLOWED_EXTENSIONS = {'.pdf', '.txt'}
MAX_FILE_SIZE_MB = 50  # 50 ميجابايت

def validate_file(uploaded_file) -> tuple:
    """
    التحقق من الملف المرفوع
    ترجع: (صحيح/خطأ, رسالة الخطأ)
    """
    if not uploaded_file:
        return False, "لم يتم اختيار ملف"

    # التحقق من الحجم
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"حجم الملف كبير جداً. الحد الأقصى: {MAX_FILE_SIZE_MB} ميجابايت"

    # التحقق من الامتداد
    file_name = uploaded_file.name.lower()
    if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, f"نوع الملف غير مدعوم. الملفات المسموحة: {', '.join(ALLOWED_EXTENSIONS)}"

    return True, ""

# ========== Session Security ==========

def init_session_security():
    """تهيئة إعدادات الأمان في الجلسة"""
    if 'session_start' not in st.session_state:
        st.session_state.session_start = time.time()

    # التحقق من انتهاء الجلسة (30 دقيقة)
    SESSION_TIMEOUT = 30 * 60  # 30 دقيقة
    if st.session_state.session_start:
        elapsed = time.time() - st.session_state.session_start
        if elapsed > SESSION_TIMEOUT:
            # انتهت الجلسة
            st.session_state.user = None
            st.session_state.session_start = None
            st.warning("⏰ انتهت جلستك. يرجى تسجيل الدخول مرة أخرى.")
            st.rerun()

def refresh_session():
    """تحديث وقت الجلسة"""
    st.session_state.session_start = time.time()

# ========== Role Verification ==========

def require_role(required_role: str):
    """ديكوريتور للتحقق من صلاحيات المستخدم"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = st.session_state.get('user')
            if not user:
                st.error("🔒 يرجى تسجيل الدخول أولاً")
                return None
            if user.get('role') != required_role:
                st.error(f"⛔ هذه الصفحة مخصصة لـ {required_role} فقط")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

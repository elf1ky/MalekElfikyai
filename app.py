import streamlit as st
import database as db
from config import PAGE_CONFIG, PRIMARY_COLOR
from database import init_db
from security import (
    verify_teacher_code, check_rate_limit, record_failed_login,
    sanitize_input, validate_username, validate_password,
    init_session_security, refresh_session
)

init_db()
st.set_page_config(**PAGE_CONFIG)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    * {{ font-family: 'Tajawal', sans-serif; }}
    .stApp {{ background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }}
    .login-container {{ max-width: 450px; margin: 0 auto; padding: 2rem; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.1); margin-top: 5vh; }}
    .login-title {{ text-align: center; color: {PRIMARY_COLOR}; font-size: 2rem; font-weight: 800; }}
    .login-subtitle {{ text-align: center; color: #64748b; margin-bottom: 2rem; }}
    .stButton>button {{ width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.75rem; border-radius: 12px; font-weight: 700; font-size: 1.1rem; transition: all 0.3s ease; }}
    .stButton>button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }}
    .feature-card {{ background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin: 1rem 0; border-right: 4px solid {PRIMARY_COLOR}; transition: transform 0.3s ease; }}
    .feature-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }}
    .stat-card {{ background: white; padding: 1.5rem; border-radius: 16px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
    .stat-number {{ font-size: 2.5rem; font-weight: 800; color: {PRIMARY_COLOR}; }}
    .welcome-hero {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 3rem 2rem; border-radius: 24px; text-align: center; margin-bottom: 2rem; }}
    .welcome-hero h1 {{ font-size: 2.5rem; font-weight: 800; margin-bottom: 1rem; }}
    .welcome-hero p {{ font-size: 1.2rem; opacity: 0.9; }}
    .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; }}
    .badge-success {{ background: rgba(16, 185, 129, 0.1); color: #10b981; }}
    .badge-teacher {{ background: rgba(245, 158, 11, 0.1); color: #d97706; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}
</style>
""", unsafe_allow_html=True)

if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = "login"

def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-title">🎓 منصة التعلم الذكي</div>
            <div class="login-subtitle">تعلم بذكاء، تقدم بثقة</div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب"])

        with tab1:
            with st.form("login_form"):
                username = st.text_input("👤 اسم المستخدم", placeholder="أدخل اسم المستخدم")
                password = st.text_input("🔒 كلمة المرور", type="password", placeholder="أدخل كلمة المرور")
                submit = st.form_submit_button("تسجيل الدخول", use_container_width=True)

                if submit:
                    if not check_rate_limit(username):
                        st.error("⛔ عدد محاولات كثيرة. يرجى الانتظار 5 دقائق.")
                        st.stop()
                    username = sanitize_input(username, 30)
                    password = sanitize_input(password, 128)
                    if username and password:
                        user = db.authenticate_user(username, password)
                        if user:
                            st.session_state.user = user
                            refresh_session()
                            db.log_activity(user['id'], "login", f"User {username} logged in")
                            st.success("✅ تم تسجيل الدخول بنجاح!")
                            st.rerun()
                        else:
                            record_failed_login(username)
                            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
                    else:
                        st.warning("⚠️ يرجى ملء جميع الحقول")

        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("👤 اسم المستخدم *", placeholder="حروف إنجليزية وأرقام فقط")
                new_full_name = st.text_input("📝 الاسم الكامل *", placeholder="أدخل اسمك الكامل")
                new_password = st.text_input("🔒 كلمة المرور *", type="password", placeholder="6 أحرف على الأقل")
                confirm_password = st.text_input("🔒 تأكيد كلمة المرور *", type="password", placeholder="أعد إدخال كلمة المرور")
                role = st.selectbox("👤 نوع الحساب", ["student", "teacher"])
                teacher_code = None
                if role == "teacher":
                    st.info("🔐 المعلمون يحتاجون كود سري للتسجيل")
                    teacher_code = st.text_input("🔑 كود المعلم السري", type="password", placeholder="اطلبه من الإدارة")
                submit_reg = st.form_submit_button("إنشاء حساب", use_container_width=True)

                if submit_reg:
                    new_username = sanitize_input(new_username, 30)
                    new_full_name = sanitize_input(new_full_name, 50)
                    new_password = sanitize_input(new_password, 128)
                    confirm_password = sanitize_input(confirm_password, 128)

                    if not all([new_username, new_full_name, new_password, confirm_password]):
                        st.warning("⚠️ يرجى ملء جميع الحقول المطلوبة")
                        st.stop()

                    valid_user, user_msg = validate_username(new_username)
                    if not valid_user:
                        st.error(f"❌ {user_msg}")
                        st.stop()

                    valid_pass, pass_msg = validate_password(new_password)
                    if not valid_pass:
                        st.error(f"❌ {pass_msg}")
                        st.stop()

                    if new_password != confirm_password:
                        st.error("❌ كلمتا المرور غير متطابقتين")
                        st.stop()

                    if role == "teacher":
                        if not teacher_code or not verify_teacher_code(teacher_code):
                            st.error("❌ كود المعلم غير صحيح")
                            st.stop()

                    user_id = db.create_user(new_username, new_password, new_full_name, role)
                    if user_id:
                        st.success("✅ تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول")
                    else:
                        st.error("❌ اسم المستخدم موجود بالفعل")

def show_dashboard():
    init_session_security()
    refresh_session()
    user = st.session_state.user
    stats = db.get_stats(user['id'])
    classes = db.get_all_classes()

    with st.sidebar:
        role_badge = "badge-teacher" if user['role'] == 'teacher' else "badge-success"
        role_text = "👨‍🏫 معلم" if user['role'] == 'teacher' else "👨‍🎓 طالب"
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; margin-bottom: 1rem;">
            <div style="font-size: 3rem;">{'👨‍🏫' if user['role'] == 'teacher' else '👨‍🎓'}</div>
            <h3>{user['full_name']}</h3>
            <span class="badge {role_badge}">{role_text}</span>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown("### 🧭 القائمة")

        if st.button("🏠 الرئيسية", key="nav_home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button("📚 الفصول الدراسية", key="nav_classes", use_container_width=True):
            st.switch_page("pages/library.py")
        if st.button("📝 الملاحظات", key="nav_notes", use_container_width=True):
            st.switch_page("pages/notes.py")
        if st.button("📖 محادثة الكتاب", key="nav_book_chat", use_container_width=True):
            st.switch_page("pages/book_ai_chat.py")

        st.divider()
        if st.button("🚪 تسجيل الخروج", key="nav_logout", use_container_width=True):
            db.log_activity(user['id'], "logout")
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

        st.markdown("""<div style="text-align: center; padding: 1rem; color: #64748b;"><small>🎓 منصة التعلم الذكي v4.0<br>مدعوم بـ Groq AI + Turso</small></div>""", unsafe_allow_html=True)

    if st.session_state.page == "dashboard":
        show_main_dashboard()
    elif st.session_state.page == "library":
        st.switch_page("pages/library.py")
    elif st.session_state.page == "notes":
        st.switch_page("pages/notes.py")
    elif st.session_state.page == "book_chat":
        st.switch_page("pages/book_ai_chat.py")

def show_main_dashboard():
    user = st.session_state.user
    stats = db.get_stats(user['id'])
    classes = db.get_all_classes()

    st.markdown(f"""
    <div class="welcome-hero">
        <h1>أهلاً بك، {user['full_name']}! 👋</h1>
        <p>استكشف فصولك الدراسية واطرح أسئلتك!</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="stat-card"><div class="stat-number">{len(classes)}</div><div class="stat-label">فصول</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card"><div class="stat-number">{stats['total_notes']}</div><div class="stat-label">ملاحظات</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="stat-card"><div class="stat-number">{stats['total_answers']}</div><div class="stat-label">إجابات</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1px; background:linear-gradient(90deg, transparent, #cbd5e1, transparent); margin:2rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("### ⚡ الوصول السريع")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div class="feature-card"><h3>📚 الفصول الدراسية</h3><p>اكتشف كتبك وأسئلتك وامتحاناتك</p></div>""", unsafe_allow_html=True)
        if st.button("فتح", key="q_classes"): st.switch_page("pages/library.py")
    with col2:
        st.markdown("""<div class="feature-card"><h3>📝 الملاحظات</h3><p>احفظ ملاحظاتك الدراسية</p></div>""", unsafe_allow_html=True)
        if st.button("فتح", key="q_notes"): st.switch_page("pages/notes.py")

    if classes:
        st.markdown("<div style='height:1px; background:linear-gradient(90deg, transparent, #cbd5e1, transparent); margin:2rem 0;'></div>", unsafe_allow_html=True)
        st.markdown("### 🎓 الفصول المتاحة")
        cols = st.columns(3)
        for i, cls in enumerate(classes[:9]):
            with cols[i % 3]:
                st.markdown(f"""
                <div style="background:white; padding:1.5rem; border-radius:16px; box-shadow:0 4px 15px rgba(0,0,0,0.08); margin:0.5rem 0; border-top:4px solid #4f46e5; text-align:center;">
                    <div style="font-size:2rem;">🎓</div>
                    <h4>{cls['name']}</h4>
                    <p style="color:#64748b; font-size:0.9rem;">{cls['description'] or '---'}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("دخول", key=f"dash_cls_{cls['id']}"):
                    st.session_state.selected_class = cls['id']
                    st.switch_page("pages/library.py")

if st.session_state.user is None:
    show_login()
else:
    show_dashboard()

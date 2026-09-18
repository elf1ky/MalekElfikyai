import streamlit as st
import database as db
from config import PAGE_CONFIG

st.set_page_config(**PAGE_CONFIG)

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("🔒 يرجى تسجيل الدخول أولاً")
    st.stop()

user = st.session_state.user

st.markdown("""
<style>
    .notes-header {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        text-align: center;
    }
    .note-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-top: 4px solid #10b981;
        transition: transform 0.3s;
    }
    .note-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    .note-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    .note-content {
        color: #475569;
        line-height: 1.6;
    }
    .note-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
        font-size: 0.875rem;
        color: #64748b;
    }
    .category-badge {
        background: rgba(16, 185, 129, 0.1);
        color: #059669;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #64748b;
    }
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; margin-bottom: 1rem;">
        <div style="font-size: 3rem;">{'👨‍🎓' if user['role'] == 'student' else '👨‍🏫'}</div>
        <h3>{user['full_name']}</h3>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🏠 الرئيسية", key="notes_nav_home", use_container_width=True): st.switch_page("app.py")
    #if st.button("🤖 المساعد الذكي", key="notes_nav_ai", use_container_width=True): st.switch_page("pages/ai_chat.py")
    if st.button("📚 المكتبة", key="notes_nav_lib", use_container_width=True): st.switch_page("pages/library.py")
    if st.button("📖 محادثة الكتاب", key="notes_nav_book", use_container_width=True): st.switch_page("pages/book_ai_chat.py")
    st.divider()
    if st.button("🚪 تسجيل الخروج", key="notes_nav_logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# Main Content
st.markdown("""
<div class="notes-header">
    <h1>📝 الملاحظات</h1>
    <p>احفظ أفكارك وملاحظاتك الدراسية هنا</p>
</div>
""", unsafe_allow_html=True)

# Tabs for Create and View
tab1, tab2 = st.tabs(["➕ ملاحظة جديدة", "📋 ملاحظاتي"])

with tab1:
    st.markdown("### ✍️ كتابة ملاحظة جديدة")

    with st.form("note_form"):
        note_title = st.text_input("📌 عنوان الملاحظة", placeholder="مثال: ملخص الدرس الثاني")
        note_category = st.selectbox("📂 التصنيف", [
          "أحياء"
        ])
        note_content = st.text_area("📝 المحتوى", placeholder="اكتب ملاحظتك هنا...", height=200)

        col1, col2 = st.columns(2)
        with col1:
            submit_note = st.form_submit_button("💾 حفظ الملاحظة", use_container_width=True)
        with col2:
            if st.form_submit_button("🗑️ مسح", use_container_width=True):
                st.rerun()

        if submit_note:
            if note_title and note_content:
                db.save_note(user['id'], note_title, note_content, note_category)
                db.log_activity(user['id'], "create_note", f"Created note: {note_title}")
                st.success("✅ تم حفظ الملاحظة بنجاح!")
                st.balloons()
            else:
                st.error("❌ يرجى ملء العنوان والمحتوى")

with tab2:
    notes = db.get_notes(user['id'])

    if not notes:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📝</div>
            <h3>لا توجد ملاحظات بعد</h3>
            <p>ابدأ بإضافة ملاحظتك الأولى من تبويب "ملاحظة جديدة"</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Filter
        categories = list(set([n['category'] for n in notes]))
        selected_category = st.selectbox("🔍 تصفية حسب التصنيف", ["الكل"] + categories)

        filtered_notes = notes if selected_category == "الكل" else [n for n in notes if n['category'] == selected_category]

        st.markdown(f"**📊 عدد الملاحظات: {len(filtered_notes)}**")

        for note in filtered_notes:
            st.markdown(f"""
            <div class="note-card">
                <div class="note-title">{note['title']}</div>
                <div class="note-content">{note['content']}</div>
                <div class="note-meta">
                    <span class="category-badge">{note['category']}</span>
                    <span>📅 {note['created_at']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("🗑️ حذف", key=f"del_{note['id']}"):
                    db.delete_note(note['id'], user['id'])
                    db.log_activity(user['id'], "delete_note", f"Deleted note: {note['title']}")
                    st.success("تم الحذف!")
                    st.rerun()

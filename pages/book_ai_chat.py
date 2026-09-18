import streamlit as st
import database as db
from ai_service import get_rag_response
from config import PAGE_CONFIG

st.set_page_config(**PAGE_CONFIG)

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("🔒 يرجى تسجيل الدخول أولاً")
    st.stop()

user = st.session_state.user

st.markdown("""
<style>
    .book-chat-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        text-align: center;
    }
    .book-selector {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    }
    .rag-message-user {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 4px 20px;
        margin: 0.5rem 0 0.5rem 15%;
        max-width: 85%;
        word-wrap: break-word;
    }
    .rag-message-ai {
        background: white;
        color: #1e293b;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 4px;
        margin: 0.5rem 15% 0.5rem 0;
        max-width: 85%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        word-wrap: break-word;
    }
    .source-badge {
        display: inline-block;
        background: rgba(79, 70, 229, 0.1);
        color: #4f46e5;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        margin-top: 8px;
    }
    .context-info {
        background: #f8fafc;
        padding: 8px 12px;
        border-radius: 8px;
        margin-top: 8px;
        font-size: 12px;
        color: #64748b;
    }
    .quick-question-btn {
        background: rgba(79, 70, 229, 0.08);
        border: 1px solid rgba(79, 70, 229, 0.2);
        color: #4f46e5;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        transition: all 0.3s;
        font-size: 13px;
        margin: 4px;
    }
    .quick-question-btn:hover {
        background: #4f46e5;
        color: white;
    }
    .empty-book-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #64748b;
    }
    .empty-book-state-icon {
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
    if st.button("🏠 الرئيسية", use_container_width=True):
        st.switch_page("app.py")
    if st.button("📚 المكتبة", use_container_width=True):
        st.switch_page("pages/library.py")
    
    st.divider()
    if st.button("🚪 تسجيل الخروج", key="book_nav_logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.markdown("""
<div class="book-chat-header">
    <h1>📖 محادثة الكتاب</h1>
    <p>اسأل عن أي شيء في الكتاب - سيجيبك الذكاء الاصطناعي من محتوى الكتاب فقط!</p>
</div>
""", unsafe_allow_html=True)

# Get all books
books = db.get_all_books()# there is no get all books function in database.py added it but i will change this line to the next one because 
#if the book_ai_chat.py page should only show books for the student's class (which is more secure)
#books = db.get_books_by_class(st.session_state.class_id)

if not books:
    st.markdown("""
    <div class="empty-book-state">
        <div class="empty-book-state-icon">📚</div>
        <h3>لا توجد كتب مرفوعة بعد</h3>
        <p>سيتم إضافة الكتب قريباً. عد لاحقاً!</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Book selector
st.markdown("<div class='book-selector'>", unsafe_allow_html=True)
selected_book_id = st.selectbox(
    "📖 اختر الكتاب",
    options=[b['id'] for b in books],
    format_func=lambda x: next((f"📖 {b['title']} ({b['subject']})" for b in books if b['id'] == x), "")
)
st.markdown("</div>", unsafe_allow_html=True)

selected_book = next((b for b in books if b['id'] == selected_book_id), None)

if selected_book:
    chunks = db.get_book_chunks(selected_book_id)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 القطع النصية", len(chunks))
    with col2:
        st.metric("📚 المادة", selected_book['subject'])
    with col3:
        st.metric("👨‍🏫 المعلم", selected_book.get('teacher_name', '—'))

    st.divider()

    # Initialize chat for this book
    chat_key = f"book_chat_{selected_book_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
        # Welcome message
        welcome = f"""👋 مرحباً! أنا مساعدك الذكي لكتاب **{selected_book['title']}**.

يمكنني مساعدتك في:
• 📖 شرح مفاهيم من الكتاب
• 🔍 البحث عن معلومات محددة
• ❓ الإجابة على أسئلتك من محتوى الكتاب فقط
• 📝 تلخيص الأفكار الرئيسية

**ملاحظة:** سأجيب بناءً على محتوى هذا الكتاب فقط.

ما الذي تريد معرفته عن الكتاب؟"""
        st.session_state[chat_key].append({"role": "ai", "content": welcome})

    # Quick questions based on book
    st.markdown("### Please ask me in english knowing that the answer can be in any language you want^_^")
    quick_qs = [
        f"What are the main ideas in {selected_book['title']}?",
        "What are the most important points I need to memorize?",
        "Give me a summary of the book"
    ]

    cols = st.columns(2)
    for i, q in enumerate(quick_qs):
        with cols[i % 2]:
            if st.button(q, key=f"quick_book_{selected_book_id}_{i}", use_container_width=True):
                st.session_state[chat_key].append({"role": "user", "content": q})

                with st.spinner("🔍 يبحث في الكتاب..."):
                    relevant_chunks = db.search_book_chunks(selected_book_id, q, limit=5)
                    chat_history = st.session_state[chat_key][:-1]
                    result = get_rag_response(q, relevant_chunks, chat_history)

                st.session_state[chat_key].append({
                    "role": "ai", 
                    "content": result['answer'],
                    "chunks": result['chunks_used']
                })

                db.save_book_chat(user['id'], selected_book_id, q, result['answer'], result['chunks_used'])
                st.rerun()

    st.divider()

    # Display chat
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state[chat_key]:
            if msg["role"] == "user":
                st.markdown(f'<div class="rag-message-user">{msg["content"]}<div style="font-size: 11px; opacity: 0.8; margin-top: 6px;">أنت</div></div>', 
                           unsafe_allow_html=True)
            else:
                chunks_info = msg.get('chunks', '')
                chunks_html = f'<div class="source-badge">📚 مصدر: {chunks_info}</div>' if chunks_info else ''
                st.markdown(f'<div class="rag-message-ai">{msg["content"]}{chunks_html}<div style="font-size: 11px; opacity: 0.7; margin-top: 6px;">🤖 مساعد الكتاب</div></div>', 
                           unsafe_allow_html=True)

    # Input
    st.markdown("<br><br>", unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])
    with col1:
        user_input = st.text_input("اكتب سؤالك عن الكتاب...", key=f"book_input_{selected_book_id}", label_visibility="collapsed")
    with col2:
        send = st.button("📤 إرسال", use_container_width=True)

    if send and user_input.strip():
        st.session_state[chat_key].append({"role": "user", "content": user_input})

        with st.spinner("🔍 يبحث في الكتاب ويفكر..."):
            relevant_chunks = db.search_book_chunks(selected_book_id, user_input, limit=5)
            chat_history = st.session_state[chat_key][:-1]
            result = get_rag_response(user_input, relevant_chunks, chat_history)

        st.session_state[chat_key].append({
            "role": "ai", 
            "content": result['answer'],
            "chunks": result['chunks_used']
        })

        db.save_book_chat(user['id'], selected_book_id, user_input, result['answer'], result['chunks_used'])
        st.rerun()

    # Show relevant chunks for transparency
    with st.expander("🔍 عرض القطع النصية المستخدمة (للشفافية)"):
        if 'last_search_chunks' not in st.session_state:
            st.session_state.last_search_chunks = []

        if st.session_state[chat_key] and len(st.session_state[chat_key]) > 1:
            last_msg = st.session_state[chat_key][-1]
            if last_msg.get('chunks'):
                st.info(f"تم استخدام القطع التالية: {last_msg['chunks']}")

        st.markdown("**📄 جميع قطع الكتاب:**")
        for chunk in chunks[:10]:  # Show first 10 for preview
            st.markdown(f"""
            <div style="background: #f8fafc; padding: 10px; border-radius: 8px; margin: 4px 0; font-size: 12px;">
                <strong>قطعة {chunk['chunk_index']}</strong> {f"(صفحة {chunk['page_number']})" if chunk['page_number'] else ""}<br>
                {chunk['chunk_text'][:200]}...
            </div>
            """, unsafe_allow_html=True)

        if len(chunks) > 10:
            st.info(f"... و {len(chunks) - 10} قطعة أخرى")

import streamlit as st
import database as db
from document_processor import process_uploaded_file
from ai_service import evaluate_student_answer
from config import PAGE_CONFIG
from security import sanitize_input, validate_file

st.set_page_config(**PAGE_CONFIG)

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("🔒 يرجى تسجيل الدخول أولاً")
    st.stop()

user = st.session_state.user
is_teacher = user['role'] == 'teacher'

st.markdown("""
<style>
    .lib-header { background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: white; padding: 1.5rem; border-radius: 16px; margin-bottom: 1rem; text-align: center; }
    .class-card { background: white; padding: 1.5rem; border-radius: 16px; margin: 0.75rem 0; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-top: 4px solid #4f46e5; transition: transform 0.3s; text-align: center; }
    .class-card:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.12); }
    .class-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .question-card { background: white; padding: 1.5rem; border-radius: 16px; margin: 0.75rem 0; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-right: 4px solid #f59e0b; }
    .answer-card { background: white; padding: 1.5rem; border-radius: 16px; margin: 0.75rem 0; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-right: 4px solid #10b981; }
    .score-high { background: #d1fae5; color: #059669; padding: 0.5rem 1rem; border-radius: 12px; font-weight: 700; display: inline-block; }
    .score-mid { background: #fef3c7; color: #d97706; padding: 0.5rem 1rem; border-radius: 12px; font-weight: 700; display: inline-block; }
    .score-low { background: #fee2e2; color: #dc2626; padding: 0.5rem 1rem; border-radius: 12px; font-weight: 700; display: inline-block; }
    .link-btn { display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 0.75rem 1.5rem; border-radius: 12px; text-decoration: none; font-weight: 600; margin: 0.5rem 0; }
    .link-btn:hover { opacity: 0.9; }
    .empty-state { text-align: center; padding: 4rem 2rem; color: #64748b; }
    .tag { background: rgba(79, 70, 229, 0.1); color: #4f46e5; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
    .exam-box { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 1.5rem; border-radius: 16px; text-align: center; margin: 1rem 0; }
    .book-box { background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%); padding: 1.5rem; border-radius: 16px; text-align: center; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; margin-bottom: 1rem;">
        <div style="font-size: 3rem;">{'👨‍🏫' if is_teacher else '👨‍🎓'}</div>
        <h3>{user['full_name']}</h3>
        <span style="background: {'rgba(245,158,11,0.1)' if is_teacher else 'rgba(16,185,129,0.1)'}; color: {'#d97706' if is_teacher else '#059669'}; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;">{'👨‍🏫 معلم' if is_teacher else '👨‍🎓 طالب'}</span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    if st.button("🏠 الرئيسية", key="lib_nav_home", use_container_width=True): st.switch_page("app.py")
    if st.button("📝 الملاحظات", key="lib_nav_notes", use_container_width=True): st.switch_page("pages/notes.py")
    if st.button("📖 محادثة الكتاب", key="lib_nav_book", use_container_width=True): st.switch_page("pages/book_ai_chat.py")
    st.divider()
    if st.button("🚪 تسجيل الخروج", key="lib_nav_logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

st.markdown("""
<div class="lib-header">
    <h1>📚 الفصول الدراسية</h1>
    <p>""" + ("إدارة الفصول والمحتوى" if is_teacher else "اختر فصلك وابدأ التعلم") + """</p>
</div>
""", unsafe_allow_html=True)

# ===================== TEACHER VIEW =====================
if is_teacher:
    tab1, tab2 = st.tabs(["➕ إنشاء فصل جديد", "📋 إدارة الفصول"])

    with tab1:
        st.markdown("### ➕ إنشاء فصل دراسي جديد")
        with st.form("create_class_form"):
            c_name = st.text_input("🎓 اسم الفصل", placeholder="مثال: الصف الأول الثانوي - الفصل الأول")
            c_desc = st.text_area("📝 وصف الفصل", placeholder="وصف مختصر...")
            c_exam = st.text_input("🔗 رابط الامتحان (اختياري)", placeholder="https://forms.google.com/...")
            submit = st.form_submit_button("💾 إنشاء الفصل", use_container_width=True)

            if submit:
                c_name = sanitize_input(c_name, 100)
                c_desc = sanitize_input(c_desc, 500)
                c_exam = sanitize_input(c_exam, 500)
                if c_name:
                    db.create_class(c_name, c_desc, c_exam, user['id'])
                    db.log_activity(user['id'], "create_class", c_name)
                    st.success(f"✅ تم إنشاء فصل: {c_name}")
                    st.balloons()
                else:
                    st.error("❌ اسم الفصل مطلوب")

    with tab2:
        classes = db.get_all_classes()
        if not classes:
            st.info("📭 لا توجد فصول. أنشئ فصلاً من تبويب 'إنشاء فصل جديد'")
        else:
            st.markdown(f"**📊 عدد الفصول: {len(classes)}**")
            for cls in classes:
                with st.expander(f"🎓 {cls['name']}"):
                    st.markdown(f"<p style='color:#64748b'>{cls['description'] or 'لا يوجد وصف'}</p>", unsafe_allow_html=True)

                    # Exam link
                    if cls['exam_url']:
                        st.markdown(f"""
                        <div class="exam-box">
                            <h4>📝 رابط الامتحان</h4>
                            <a href="{cls['exam_url']}" target="_blank" class="link-btn">📎 فتح الامتحان</a>
                        </div>
                        """, unsafe_allow_html=True)

                    # Books in this class
                    books = db.get_books_by_class(cls['id'])
                    st.markdown("#### 📖 الكتب")
                    if books:
                        for book in books:
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                if book['book_url']:
                                    st.markdown(f"📎 [{book['title']}]({book['book_url']}) - رابط خارجي")
                                else:
                                    st.write(f"📄 {book['title']} (PDF مرفوع)")
                            with col2:
                                if st.button("🗑️ حذف", key=f"del_b_{book['id']}"):
                                    db.delete_book(book['id'])
                                    st.rerun()

                    # Add book to class
                    st.markdown("---")
                    st.markdown("**➕ إضافة كتاب للفصل**")
                    with st.form(f"add_book_{cls['id']}"):
                        b_title = st.text_input("📖 عنوان الكتاب", key=f"bt_{cls['id']}")
                        b_subject = st.text_input("📚 المادة", key=f"bs_{cls['id']}")
                        b_url = st.text_input("🔗 رابط الكتاب (PDF)", placeholder="https://drive.google.com/...", key=f"bu_{cls['id']}")
                        st.info("💡 اترك رابط الكتاب فارغاً إذا تريد رفع PDF للـ RAG")
                        b_file = st.file_uploader("📤 أو ارفع PDF للـ RAG", type=["pdf", "txt"], key=f"bf_{cls['id']}")

                        if st.form_submit_button("💾 إضافة الكتاب", use_container_width=True):
                            b_title = sanitize_input(b_title, 200)
                            b_subject = sanitize_input(b_subject, 100)
                            b_url = sanitize_input(b_url, 500)

                            if not b_title:
                                st.error("❌ عنوان الكتاب مطلوب")
                                st.stop()

                            file_name = b_file.name if b_file else ""
                            file_type = b_file.type if b_file else ""

                            book_id = db.save_book(cls['id'], b_title, b_subject, "", b_url, file_name, file_type, user['id'])

                            if b_file:
                                valid, msg = validate_file(b_file)
                                if not valid:
                                    st.error(f"❌ {msg}")
                                    st.stop()
                                result = process_uploaded_file(b_file)
                                if "error" not in result:
                                    for i, chunk in enumerate(result['chunks']):
                                        db.save_book_chunk(book_id, chunk['text'], chunk['index'], chunk['page'])
                                    st.success(f"✅ تم رفع PDF مع {result['total_chunks']} قطعة!")
                                else:
                                    st.error(f"❌ {result['error']}")
                            else:
                                st.success("✅ تم إضافة رابط الكتاب!")
                            st.rerun()

                   
                    # Questions
                    st.markdown("---")
                    tab_q_list, tab_q_add = st.tabs(["❓ قائمة الأسئلة", "➕ إضافة سؤال"])

                    with tab_q_list:
                         questions = db.get_questions_by_class(cls['id'])
                         if questions:
                            st.markdown(f"**📊 عدد الأسئلة: {len(questions)}**")

                            # Pagination: 10 per page
                            page_size = 10
                            total_pages = (len(questions) + page_size - 1) // page_size
                            page = st.selectbox(
                                        "صفحة", options=range(1, total_pages + 1),
                                       format_func=lambda p: f"صفحة {p} من {total_pages}", key=f"qpage_{cls['id']}" )

                            start = (page - 1) * page_size
                            for q in questions[start:start + page_size]:
                               col_q, col_del = st.columns([5, 1])
                               with col_q:
                                 st.markdown(
                                          f"<div style='background:#f8fafc; padding:8px; border-radius:8px; margin:4px 0;'>"
                                          f"<strong>{q['title']}</strong> - {q['difficulty']}</div>",
                                               unsafe_allow_html=True  )
                               with col_del:
                                if st.button("🗑️", key=f"del_q_{q['id']}", help="حذف السؤال"):
                                   db.delete_question(q['id'])
                                   st.rerun()
                         else:
                              st.info("📭 لا توجد أسئلة لهذا الفصل بعد")

                    with tab_q_add:
                      with st.form(f"add_q_{cls['id']}"):
                             q_title = st.text_input("📌 عنوان السؤال", key=f"qt_{cls['id']}")
                             q_text = st.text_area("❓ نص السؤال", key=f"qtx_{cls['id']}")
                             q_answer = st.text_area("✅ الإجابة النموذجية", key=f"qa_{cls['id']}")
                             q_diff = st.selectbox("📊 الصعوبة", ["سهل", "متوسط", "صعب"], key=f"qd_{cls['id']}")
                             if st.form_submit_button("➕ إضافة سؤال", use_container_width=True):
                               if q_title and q_text and q_answer:
                                  db.save_question(cls['id'], None, q_title, q_text, q_answer, q_diff, user['id'])
                                  st.success("✅ تم إضافة السؤال!")
                                  st.rerun()
                               else:
                                st.error("❌ يرجى ملء جميع الحقول")
                    # Delete class
                    st.markdown("---")
                    if st.button("🗑️ حذف الفصل", key=f"del_c_{cls['id']}"):
                        db.delete_class(cls['id'])
                        st.success("تم حذف الفصل!")
                        st.rerun()

# ===================== STUDENT VIEW =====================
else:
    # Check if a class is selected
    selected_class_id = st.session_state.get('selected_class', None)

    if selected_class_id:
        cls = db.get_class_by_id(selected_class_id)
        if not cls:
            st.error("❌ الفصل غير موجود")
            st.session_state.selected_class = None
            st.rerun()

        # Back button
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("⬅️ رجوع"):
                st.session_state.selected_class = None
                st.rerun()
        with col_title:
            st.markdown(f"### 🎓 {cls['name']}")

        books = db.get_books_by_class(selected_class_id)
        questions = db.get_questions_by_class(selected_class_id)

        tab1, tab2, tab3, tab4 = st.tabs(["📖 الكتاب", "❓ الأسئلة", "📝 الامتحان", "🤖 محادثة الكتاب"])

        with tab1:
            if books:
                for book in books:
                    if book['book_url']:
                        st.markdown(f"""
                        <div class="book-box">
                            <h4>📖 {book['title']}</h4>
                            <p style="color:#4f46e5; font-weight:600">📚 {book['subject'] or 'عام'}</p>
                            <a href="{book['book_url']}" target="_blank" class="link-btn">📎 فتح الكتاب</a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info(f"📄 {book['title']} - لا يوجد رابط مباشر")
            else:
                st.info("📭 لا يوجد كتاب لهذا الفصل بعد")

        with tab2:
            if questions:
                st.markdown(f"**📊 عدد الأسئلة: {len(questions)}**")
                for q in questions:
                    st.markdown(f"""
                    <div class="question-card">
                        <h4>❓ {q['title']}</h4>
                        <p style="color:#475569; margin:8px 0">{q['question_text']}</p>
                        <span class="tag" style="background:rgba(245,158,11,0.1);color:#d97706">📊 {q['difficulty']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    existing = [a for a in db.get_student_answers(user['id']) if a['question_id'] == q['id']]
                    if existing:
                        ans = existing[0]
                        score_class = "score-high" if ans['score'] >= 80 else "score-mid" if ans['score'] >= 60 else "score-low"
                        st.markdown(f'<span class="{score_class}">📊 {ans["score"]}/100</span>', unsafe_allow_html=True)
                        st.caption(f"إجابتك: {ans['answer_text'][:80]}...")
                    else:
                        with st.expander("✍️ كتابة الإجابة"):
                            ans_text = st.text_area("إجابتك", key=f"ans_{q['id']}")
                            if st.button("📤 إرسال", key=f"sub_{q['id']}"):
                                if ans_text.strip():
                                    with st.spinner("⏳ يتم التقييم..."):
                                        eval_result = evaluate_student_answer(q['question_text'], q['correct_answer'], ans_text)
                                    db.save_student_answer(q['id'], user['id'], ans_text, eval_result['feedback'], eval_result['score'])
                                    st.success(f"✅ درجتك: {eval_result['score']}/100")
                                    st.rerun()
                                else:
                                    st.warning("⚠️ يرجى كتابة إجابة")
            else:
                st.info("📭 لا توجد أسئلة لهذا الفصل بعد")

        with tab3:
            if cls['exam_url']:
                st.markdown(f"""
                <div class="exam-box">
                    <h2>📝 الامتحان</h2>
                    <p style="color:#92400e; margin:1rem 0">اضغط الزر أدناه لفتح صفحة الامتحان</p>
                    <a href="{cls['exam_url']}" target="_blank" class="link-btn">📝 بدء الامتحان</a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("📭 لم يتم إضافة رابط امتحان لهذا الفصل بعد")

        with tab4:
            # Only show if there's a book with PDF uploaded
            pdf_books = [b for b in books if b['file_name']]
            if pdf_books:
                st.info("🤖 يمكنك السؤال عن الكتاب في صفحة 'محادثة الكتاب'")
                if st.button("🤖 فتح محادثة الكتاب", use_container_width=True):
                    st.session_state.selected_book = pdf_books[0]
                    st.switch_page("pages/book_ai_chat.py")
            else:
                st.info("📭 لا يوجد كتاب PDF مرفوع للـ RAG في هذا الفصل")

    else:
        # Show all classes as cards
        classes = db.get_all_classes()
        if not classes:
            st.markdown("""
            <div class="empty-state">
                <div style="font-size:4rem; margin-bottom:1rem">🎓</div>
                <h3>لا توجد فصول دراسية بعد</h3>
                <p>سيتم إضافتها قريباً!</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"**📊 عدد الفصول: {len(classes)}**")
            cols = st.columns(3)
            for i, cls in enumerate(classes):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="class-card">
                        <div class="class-icon">🎓</div>
                        <h4>{cls['name']}</h4>
                        <p style="color:#64748b; font-size:0.9rem; margin:8px 0">{cls['description'] or '---'}</p>
                        <span class="tag">👨‍🏫 {cls.get('teacher_name', '---')}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("دخول", key=f"enter_{cls['id']}", use_container_width=True):
                        st.session_state.selected_class = cls['id']
                        st.rerun()

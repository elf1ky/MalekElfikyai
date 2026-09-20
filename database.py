import sqlite3
import hashlib
import secrets

from django.core.mail import get_connection
from config import DB_PATH, USE_TURSO, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN

def get_db_connection():
    if USE_TURSO:
        try:
            import libsql_experimental as libsql
            conn = libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
            return conn
        except Exception as e:
            print(f"⚠️ Turso failed: {e}. Using local SQLite.")
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def _row_to_dict(row, cursor):
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return dict(row)
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def _column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    try:
        cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
        return True
    except:
        return False

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Classes (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            exam_url TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    # Books (with class_id and book_url)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            title TEXT NOT NULL,
            subject TEXT,
            description TEXT,
            book_url TEXT,
            file_name TEXT,
            file_type TEXT,
            uploaded_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    """)

    # Add columns if upgrading from old schema
    for col in [('class_id', 'INTEGER'), ('book_url', 'TEXT')]:
        if not _column_exists(cursor, 'books', col[0]):
            cursor.execute(f"ALTER TABLE books ADD COLUMN {col[0]} {col[1]}")

    # Book chunks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            page_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
        )
    """)

    # Questions (with class_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            book_id INTEGER,
            title TEXT NOT NULL,
            question_text TEXT NOT NULL,
            correct_answer TEXT,
            difficulty TEXT DEFAULT 'متوسط',
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes (id),
            FOREIGN KEY (book_id) REFERENCES books (id)
        )
    """)

    if not _column_exists(cursor, 'questions', 'class_id'):
        cursor.execute("ALTER TABLE questions ADD COLUMN class_id INTEGER")

    # Student answers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL,
            ai_feedback TEXT,
            score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    """)

    # Book chat history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            chunks_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Notes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'عام',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Activity log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

# ========== Auth ==========
def hash_password(password):
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + pwdhash.hex()

def verify_password(stored, provided):
    salt = stored[:32]
    stored_hash = stored[32:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided.encode(), salt.encode(), 100000)
    return pwdhash.hex() == stored_hash

def create_user(username, password, full_name, role="student"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                       (username, hash_password(password), full_name, role))
        conn.commit()
        return cursor.lastrowid
    except:
        return None
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    user_dict = _row_to_dict(user, cursor)
    if user_dict and verify_password(user_dict['password_hash'], password):
        return user_dict
    return None

# ========== Classes ==========
def create_class(name, description, exam_url, created_by):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO classes (name, description, exam_url, created_by) VALUES (?, ?, ?, ?)",
                   (name, description, exam_url, created_by))
    conn.commit()
    class_id = cursor.lastrowid
    conn.close()
    return class_id

def get_all_classes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT c.*, u.full_name as teacher_name FROM classes c JOIN users u ON c.created_by = u.id ORDER BY c.created_at")
    classes = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return classes

def get_class_by_id(class_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
    cls = cursor.fetchone()
    conn.close()
    return _row_to_dict(cls, cursor) if cls else None

def delete_class(class_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 1. Student answers to this class's questions
    cursor.execute("""
        DELETE FROM student_answers WHERE question_id IN (
            SELECT id FROM questions WHERE class_id = ?
        )
    """, (class_id,))
    # 2. Questions
    cursor.execute("DELETE FROM questions WHERE class_id = ?", (class_id,))
    # 3. RAG chunks of this class's books
    cursor.execute("DELETE FROM book_chunks WHERE book_id IN (SELECT id FROM books WHERE class_id = ?)", (class_id,))
    # 4. Chat history of this class's books
    cursor.execute("DELETE FROM book_chat_history WHERE book_id IN (SELECT id FROM books WHERE class_id = ?)", (class_id,))
    # 5. Books
    cursor.execute("DELETE FROM books WHERE class_id = ?", (class_id,))
    # 6. The class — last
    cursor.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()
    
# ========== Books ==========
def save_book(class_id, title, subject, description, book_url, file_name, file_type, uploaded_by):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO books (class_id, title, subject, description, book_url, file_name, file_type, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (class_id, title, subject, description, book_url, file_name, file_type, uploaded_by))
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    return book_id

def get_books_by_class(class_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE class_id = ?", (class_id,))
    books = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return books

def get_all_books():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books ORDER BY created_at DESC")
    books = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return books

def get_book_by_id(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    conn.close()
    return _row_to_dict(book, cursor)

def delete_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 1. Answers to this book's questions
    cursor.execute("DELETE FROM student_answers WHERE question_id IN (SELECT id FROM questions WHERE book_id = ?)", (book_id,))
    # 2. Questions attached to this book
    cursor.execute("DELETE FROM questions WHERE book_id = ?", (book_id,))
    # 3. RAG chunks
    cursor.execute("DELETE FROM book_chunks WHERE book_id = ?", (book_id,))
    # 4. Chat history about this book (no FK, but cleanup so it doesn't dangle)
    cursor.execute("DELETE FROM book_chat_history WHERE book_id = ?", (book_id,))
    # 5. The book itself — always last
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
# ========== Chunks ==========
def save_book_chunk(book_id, chunk_text, chunk_index, page_number=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO book_chunks (book_id, chunk_text, chunk_index, page_number) VALUES (?, ?, ?, ?)",
                   (book_id, chunk_text, chunk_index, page_number))
    conn.commit()
    conn.close()

def get_book_chunks(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM book_chunks WHERE book_id = ? ORDER BY chunk_index", (book_id,))
    chunks = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return chunks

def search_book_chunks(book_id, query, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    words = query.split()
    if not words:
        return []
    conditions = " OR ".join(["chunk_text LIKE ?" for _ in words])
    params = [f"%{w}%" for w in words]
    cursor.execute(f"SELECT * FROM book_chunks WHERE book_id = ? AND ({conditions}) ORDER BY chunk_index LIMIT ?",
                   (book_id, ) + tuple(params) + (limit, ))
    chunks = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return chunks

# ========== Questions ==========
def save_question(class_id, book_id, title, question_text, correct_answer, difficulty, created_by):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions (class_id, book_id, title, question_text, correct_answer, difficulty, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (class_id, book_id, title, question_text, correct_answer, difficulty, created_by))
    conn.commit()
    conn.close()

def get_questions_by_class(class_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT q.*, b.title as book_title FROM questions q LEFT JOIN books b ON q.book_id = b.id WHERE q.class_id = ? ORDER BY q.created_at DESC", (class_id,))
    questions = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return questions

def get_all_questions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT q.*, c.name as class_name FROM questions q LEFT JOIN classes c ON q.class_id = c.id ORDER BY q.created_at DESC")
    questions = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return questions

def delete_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student_answers WHERE question_id = ?", (question_id,))
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
# ========== Student Answers ==========
def save_student_answer(question_id, student_id, answer_text, ai_feedback=None, score=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO student_answers (question_id, student_id, answer_text, ai_feedback, score)
        VALUES (?, ?, ?, ?, ?)
    """, (question_id, student_id, answer_text, ai_feedback, score))
    conn.commit()
    conn.close()

def get_student_answers(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sa.*, q.title as question_title, q.question_text, c.name as class_name
        FROM student_answers sa
        JOIN questions q ON sa.question_id = q.id
        LEFT JOIN classes c ON q.class_id = c.id
        WHERE sa.student_id = ? ORDER BY sa.created_at DESC
    """, (student_id,))
    answers = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return answers

# ========== Chat ==========
def save_chat(user_id, message, response, model="llama"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, message, response, model_used) VALUES (?, ?, ?, ?)",
                   (user_id, message, response, model))
    conn.commit()
    conn.close()

def save_book_chat(user_id, book_id, message, response, chunks_used=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO book_chat_history (user_id, book_id, message, response, chunks_used) VALUES (?, ?, ?, ?, ?)",
                   (user_id, book_id, message, response, chunks_used))
    conn.commit()
    conn.close()

def get_book_chat_history(user_id, book_id, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM book_chat_history WHERE user_id = ? AND book_id = ? ORDER BY created_at DESC LIMIT ?",
                   (user_id, book_id, limit))
    chats = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return chats

# ========== Notes ==========
def save_note(user_id, title, content, category="عام"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (user_id, title, content, category) VALUES (?, ?, ?, ?)",
                   (user_id, title, content, category))
    conn.commit()
    conn.close()

def get_notes(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    notes = [_row_to_dict(row, cursor) for row in cursor.fetchall()]
    conn.close()
    return notes

def delete_note(note_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
    conn.commit()
    conn.close()

# ========== Activity & Stats ==========
def log_activity(user_id, activity_type, details=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activity_log (user_id, activity_type, details) VALUES (?, ?, ?)",
                   (user_id, activity_type, details))
    conn.commit()
    conn.close()

def get_stats(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM book_chat_history WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    total_chats = _row_to_dict(row, cursor)['total'] if row else 0
    cursor.execute("SELECT COUNT(*) as total FROM notes WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    total_notes = _row_to_dict(row, cursor)['total'] if row else 0
    cursor.execute("SELECT COUNT(*) as total FROM student_answers WHERE student_id = ?", (user_id,))
    row = cursor.fetchone()
    total_answers = _row_to_dict(row, cursor)['total'] if row else 0
    conn.close()
    return {"total_chats": total_chats, "total_notes": total_notes, "total_answers": total_answers}

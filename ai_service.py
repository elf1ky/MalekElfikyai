from openai import OpenAI
import os
from config import GROQ_API_KEY, GROQ_MODEL
import streamlit as st
import database as db

@st.cache_resource
def get_client():
    """Initialize OpenAI client with Groq base URL"""
    if not GROQ_API_KEY:
        return None
    return OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY
    )

def get_ai_response(message: str, chat_history: list = None, system_prompt: str = None) -> str:
    client = get_client()
    if not client:
        return "❌ لم يتم إعداد مفتاح Groq API. يرجى التحقق من ملف .env"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    else:
        messages.append({
            "role": "system", 
            "content": """أنت مساعد تعليمي ذكي وودود. ساعد الطلاب في فهم المواد الدراسية، 
            أجب على أسئلتهم بوضوح، وشجعهم على التعلم. استخدم الأمثلة العملية عند الحاجة.
            تحدث باللغة العربية أو الإنجليزية حسب لغة السؤال."""
        })

    if chat_history:
        for chat in chat_history[-5:]:
            # Handle both formats: {'role': 'user', 'content': '...'} and {'message': '...', 'response': '...'}
            if 'role' in chat and 'content' in chat:
                # Format from ai_chat.py session state
                role = "assistant" if chat['role'] == "ai" else chat['role']
                messages.append({"role": role, "content": chat['content']})
            elif 'message' in chat and 'response' in chat:
                # Format from database
                messages.append({"role": "user", "content": chat['message']})
                messages.append({"role": "assistant", "content": chat['response']})
            elif 'message' in chat:
                # Only message (user input)
                messages.append({"role": "user", "content": chat['message']})

    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            top_p=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ خطأ في الاتصال: {str(e)}"

# ========== RAG Functions ==========

def get_rag_response(question: str, book_chunks: list, chat_history: list = None) -> dict:
    """Answer using RAG (from book only)"""
    client = get_client()
    if not client:
        return {"answer": "❌ لم يتم إعداد مفتاح API", "chunks_used": ""}

    if not book_chunks:
        return {"answer": "❌ لم يتم العثور على معلومات ذات صلة في الكتاب. حاول صياغة سؤالك بشكل مختلف.", "chunks_used": ""}

    context = " ".join([f"[قطعة {i+1}]: {chunk['chunk_text']}" for i, chunk in enumerate(book_chunks)])

    system_prompt = f"""أنت مساعد تعليمي متخصص. يجب أن تجيب على أسئلة الطلاب بناءً على المعلومات المقدمة فقط من الكتاب.

قواعد مهمة:
1. جاوب بناءً على المعلومات في "السياق" فقط
2. إذا لم تجد الإجابة في السياق، قول "لم أجد إجابة لهذا السؤال في الكتاب"
3. اذكر رقم الصفحة إذا كان متوفراً
4. كن دقيقاً وواضحاً
5. استخدم الأمثلة من النص عند الإمكان

السياق من الكتاب:
{context}
"""

    messages = [{"role": "system", "content": system_prompt}]

    if chat_history:
        for chat in chat_history[-3:]:
            # Handle both formats
            if 'role' in chat and 'content' in chat:
                role = "assistant" if chat['role'] == "ai" else chat['role']
                messages.append({"role": role, "content": chat['content']})
            elif 'message' in chat and 'response' in chat:
                messages.append({"role": "user", "content": chat['message']})
                messages.append({"role": "assistant", "content": chat['response']})
            elif 'message' in chat:
                messages.append({"role": "user", "content": chat['message']})

    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            top_p=0.9,
        )

        chunks_summary = " | ".join([f"قطعة {c['chunk_index']}" for c in book_chunks])
        return {
            "answer": response.choices[0].message.content,
            "chunks_used": chunks_summary
        }
    except Exception as e:
        return {"answer": f"❌ خطأ: {str(e)}", "chunks_used": ""}

def evaluate_student_answer(question: str, correct_answer: str, student_answer: str, book_context: str = "") -> dict:
    """Evaluate student answer with AI"""
    client = get_client()
    if not client:
        return {"score": 0, "feedback": "❌ خطأ في الاتصال"}

    prompt = f"""قيم إجابة الطالب التالية:

السؤال: {question}
الإجابة النموذجية: {correct_answer}
إجابة الطالب: {student_answer}

{book_context}

قم بالتقييم وقدم:
1. درجة من 0 إلى 100
2. ملخص قصير للتقييم
3. نصائح للتحسين
4. ما كان صحيحاً وما كان خاطئاً

قدم الإجابة بالتنسيق التالي:
الدرجة: [رقم]
التقييم: [نص]
النصائح: [نص]
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "أنت معلم متخصص في تقييم إجابات الطلاب. كن عادلاً وشجعاً."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1024,
        )

        result = response.choices[0].message.content

        import re
        score_match = re.search(r'الدرجة[:\s]*(\d+)', result)
        score = int(score_match.group(1)) if score_match else 50

        return {"score": score, "feedback": result}
    except Exception as e:
        return {"score": 0, "feedback": f"❌ خطأ في التقييم: {str(e)}"}

def get_study_plan(subject: str, duration: str, level: str) -> str:
    prompt = f"""أنشئ خطة دراسية مفصلة للمادة: {subject}
    المدة: {duration}
    المستوى: {level}

    قسّم الخطة إلى:
    1. أهداف التعلم
    2. جدول زمني
    3. موارد مقترحة
    4. تمارين واختبارات
    """
    return get_ai_response(prompt, system_prompt="أنت مخطط تعليمي خبير. أنشئ خطط دراسية منظمة وعملية.")

def explain_topic(topic: str, level: str = "متوسط") -> str:
    prompt = f"""اشرح الموضوع التالي ببساطة ووضوح:
    الموضوع: {topic}
    المستوى: {level}

    استخدم:
    - أمثلة عملية
    - تشبيهات مفيدة
    - نقاط رئيسية واضحة
    """
    return get_ai_response(prompt)

def generate_quiz(subject: str, num_questions: int = 5, difficulty: str = "متوسط") -> str:
    prompt = f"""أنشئ اختباراً في: {subject}
    عدد الأسئلة: {num_questions}
    مستوى الصعوبة: {difficulty}

    لكل سؤال:
    - السؤال
    - 4 خيارات (أ، ب، ج، د)
    - الإجابة الصحيحة
    - شرح مختصر
    """
    return get_ai_response(prompt, system_prompt="أنت معلم متخصص في إعداد الاختبارات التعليمية.")

"""
معالجة المستندات - استخراج النص وتقسيمه لنظام RAG
"""
import PyPDF2
import io
import re

def extract_text_from_pdf(pdf_file) -> str:
    """استخراج النص من ملف PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- صفحة {page_num + 1} ---\n"
                text += page_text
        return text
    except Exception as e:
        return f"خطأ في قراءة الملف: {str(e)}"

def extract_text_from_docx(docx_file) -> str:
    """استخراج النص من ملف Word (إذا لزم الأمر)"""
    try:
        import docx
        doc = docx.Document(docx_file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except:
        return ""

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    """
    تقسيم النص لقطع صغيرة للـ RAG
    chunk_size: عدد الأحرف في كل قطعة
    overlap: تداخل بين القطع للحفاظ على السياق
    """
    # تنظيف النص
    text = re.sub(r'\s+', ' ', text).strip()

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size

        # حاول تقطيع عند نهاية جملة إذا أمكن
        if end < len(text):
            # ابحث عن آخر نقطة أو فاصلة
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)

            split_point = max(last_period, last_newline)
            if split_point > start + chunk_size // 2:
                end = split_point + 1

        chunk = text[start:end].strip()
        if chunk:
            # استخراج رقم الصفحة إذا موجود
            page_match = re.search(r'--- صفحة (\d+) ---', chunk)
            page_number = int(page_match.group(1)) if page_match else None

            # إزالة علامات الصفحات من النص
            clean_chunk = re.sub(r'--- صفحة \d+ ---', '', chunk).strip()

            if clean_chunk:
                chunks.append({
                    'text': clean_chunk,
                    'index': chunk_index,
                    'page': page_number
                })
                chunk_index += 1

        start = end - overlap

    return chunks

def process_uploaded_file(uploaded_file) -> dict:
    """معالجة الملف المرفوع واستخراج القطع"""
    file_type = uploaded_file.type

    if file_type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        text = extract_text_from_docx(uploaded_file)
    elif file_type == "text/plain":
        text = uploaded_file.read().decode('utf-8')
    else:
        return {"error": "نوع الملف غير مدعوم. يدعم: PDF, Word, TXT"}

    if text.startswith("خطأ"):
        return {"error": text}

    if len(text.strip()) < 50:
        return {"error": "الملف فارغ أو لا يحتوي على نص قابل للاستخراج"}

    chunks = chunk_text(text)

    return {
        "text": text[:500] + "..." if len(text) > 500 else text,
        "chunks": chunks,
        "total_chunks": len(chunks),
        "total_chars": len(text)
    }

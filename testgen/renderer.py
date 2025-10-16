from typing import List
from docx import Document
from core.models import QuizIR, QuestionIR

def questions_to_plain(q: QuestionIR) -> str:
    out = [f"{q.id}) {q.prompt}"]
    for i, c in enumerate(q.choices, start=1):
        out.append(f"   ({chr(96+i)}) {c.text}")  # a), b), c)...
    return "\n".join(out)

def render_to_docx(quiz: QuizIR, template_path: str, out_docx: str, placeholder="{{QUESTOES}}"):
    doc = Document(template_path)
    body_plain = "\n\n".join(questions_to_plain(q) for q in quiz.questions)
    # substitui placeholder em todos os parágrafos
    for p in doc.paragraphs:
        if placeholder in p.text:
            p.text = p.text.replace(placeholder, body_plain)
    doc.save(out_docx)

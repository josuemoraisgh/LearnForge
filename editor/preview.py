from core.parsers import to_ir
from core.models import QuestionIR

def preview_text(raw_questions, title="Pré-visualização"):
    quiz = to_ir(raw_questions, title=title)
    lines = []
    for q in quiz.questions:
        lines.append(f"[{q.kind}] {q.id}. {q.prompt}")
        for i, c in enumerate(q.choices, start=1):
            flag = "*" if c.is_correct else " "
            lines.append(f"   {flag} {chr(96+i)}) {c.text}")
        if q.solution:
            lines.append(f"   Solução: {q.solution}")
        lines.append("")
    return "\n".join(lines)

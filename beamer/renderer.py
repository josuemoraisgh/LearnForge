from typing import Iterable
from core.models import QuizIR, QuestionIR, Choice

def _latex_escape(s: str) -> str:
    return (s.replace('\\', r'\textbackslash{}')
             .replace('&', r'\&').replace('%', r'\%')
             .replace('$', r'\$').replace('#', r'\#')
             .replace('_', r'\_').replace('{', r'\{')
             .replace('}', r'\}').replace('~', r'\textasciitilde{}')
             .replace('^', r'\textasciicircum{}'))

def render_question(q: QuestionIR, fsq="Large", fsa="normalsize") -> str:
    prompt = _latex_escape(q.prompt)
    lines = [r"\begin{frame}", rf"\{fsq} {prompt}\\[4pt]"]
    if q.choices:
        lines.append(r"\begin{itemize}")
        for c in q.choices:
            txt = _latex_escape(c.text)
            lines.append(rf"\item \{fsa} {txt}")
        lines.append(r"\end{itemize}")
    if q.solution:
        lines.append(r"\vspace{4pt}")
        lines.append(rf"\textit{{Solução:}} \{fsa} {_latex_escape(q.solution)}")
    lines.append(r"\end{frame}")
    return "\n".join(lines)

def render_quiz(quiz: QuizIR, title="Slides", fsq="Large", fsa="normalsize") -> str:
    frames = [render_question(q, fsq=fsq, fsa=fsa) for q in quiz.questions]
    doc = [
        r"\documentclass{beamer}",
        r"\usetheme{default}",
        rf"\title{{{_latex_escape(quiz.title or title)}}}",
        r"\begin{document}",
        r"\frame{\titlepage}",
        *frames,
        r"\end{document}",
    ]
    return "\n".join(doc)

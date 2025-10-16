
# -*- coding: utf-8 -*-
"""
Utilidades para geração de LaTeX/Beamer.
Responsabilidade: funções puras de renderização e escaping.
"""
from typing import List, Dict
import re

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".bmp", ".webp")

def latex_escape(text: str) -> str:
    """Escapa LaTeX, preservando <PLACEHOLDERS>."""
    text = text or ""
    placeholders = re.findall(r"<[^<>]+>", text)
    tmp = text
    for i, ph in enumerate(placeholders):
        tmp = tmp.replace(ph, f"__PH{i}__")
    repl = {
        '\\': r'\textbackslash{}',
        '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_',
        '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
    }
    out = "".join(repl.get(ch, ch) for ch in tmp)
    for i, ph in enumerate(placeholders):
        out = out.replace(f"__PH{i}__", ph)
    return out

def is_image_path(s: str) -> bool:
    return isinstance(s, str) and s.strip().lower().endswith(IMAGE_EXTS)

def render_images(imgs: List[str]) -> str:
    if not imgs: return ""
    lines = [r"\begin{center}"]
    for p in imgs:
        lines.append("\\includegraphics[width=0.85\\linewidth]{{{}}}\\\\[2mm]".format(latex_escape(p)))
    lines.append(r"\end{center}")
    return "\n".join(lines) + "\n"

def render_afirmacoes(afirm):
    """
    Renderiza afirmativas (tipo 4) a partir de dict OU lista.
       - dict {"I": "texto", "II": "texto", ...} -> ordena por romano
       - list/tuple ["texto I", "texto II", ...] -> rotula I, II, III, ...
    """
    if not afirm:
        return ""

    def int_to_roman(n: int) -> str:
        vals = [
            (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
        ]
        out = []
        x = n
        for v, sym in vals:
            while x >= v:
                out.append(sym)
                x -= v
        return "".join(out)

    if isinstance(afirm, (list, tuple)):
        itens = [(int_to_roman(i+1), s) for i, s in enumerate(afirm) if isinstance(s, str) and s.strip()]
        if not itens: return ""
        out = [r"\begin{itemize}"]
        for k, v in itens:
            out.append("\\item \\textbf{{{}}} {}".format(latex_escape(k), latex_escape(v)))
        out.append(r"\end{itemize}")
        return "\n".join(out) + "\n"

    if isinstance(afirm, dict):
        def roman_key(s: str) -> int:
            roman = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
            s = (s or "").strip().upper()
            total = 0; prev = 0
            for ch in reversed(s):
                val = roman.get(ch,0)
                if val < prev: total -= val
                else: total += val; prev = val
            return total
        items = sorted(((str(k), str(v)) for k, v in afirm.items()), key=lambda kv: roman_key(kv[0]))
        if not items: return ""
        out = [r"\begin{itemize}"]
        for k, v in items:
            out.append("\\item \\textbf{{{}}} {}".format(latex_escape(k), latex_escape(v)))
        out.append(r"\end{itemize}")
        return "\n".join(out) + "\n"

    return ""

def render_alts_text(alts: List[str], correta: str = "", highlight: bool = False) -> str:
    """Alternativas em texto com enumerate a), b), c) (requer enumitem no preâmbulo)."""
    if not alts:
        return r"\emph{(Sem alternativas no JSON.)}" + "\n"
    out = [r"\begin{enumerate}[label=\alph*)]"]
    for a in alts:
        t = latex_escape(a)
        if highlight and correta and a.strip() == correta.strip():
            out.append("\\item \\alert{{{}}}".format(t))
        else:
            out.append("\\item {}".format(t))
    out.append(r"\end{enumerate}")
    return "\n".join(out) + "\n"

def render_alts_images(alts: List[str], correta: str = "", highlight: bool = False) -> str:
    """Alternativas em 2 colunas de imagens/legendas."""
    if not alts:
        return r"\emph{(Sem alternativas no JSON.)}" + "\n"
    letters = "abcdefghijklmnopqrstuvwxyz"
    lines = [r"\begin{columns}"]
    for i, a in enumerate(alts):
        lines.append(r"\begin{column}{0.5\textwidth}")
        if is_image_path(a):
            lines.append(r"\begin{center}")
            lines.append("\\includegraphics[width=\\linewidth]{{{}}}".format(latex_escape(a)))
            cap = "\\textbf{{{} )}}".format(letters[i])
            if highlight and correta and a.strip() == (correta or "").strip():
                cap += r" \alert{(correta)}"
            lines.append(cap)
            lines.append(r"\end{center}")
        else:
            cap = "\\textbf{{{} )}} {}".format(letters[i], latex_escape(a))
            if highlight and correta and a.strip().lower().startswith('nenhuma') and (correta or '').strip().lower().startswith('nenhuma'):
                cap += r" \alert{(correta)}"
            lines.append(cap)
        lines.append(r"\end{column}")
        if (i % 2) == 1 and i != len(alts)-1:
            lines.append(r"\end{columns}")
            lines.append(r"\begin{columns}")
    lines.append(r"\end{columns}")
    return "\n".join(lines) + "\n"

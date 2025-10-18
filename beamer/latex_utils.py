
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import re

def _parse_img_spec(s: str):
    """Parse 'path;LxA' -> (path, L, A) in mm; or (path, None, None)."""
    if not isinstance(s, str):
        return s, None, None
    if ';' in s:
        path, size = s.split(';',1)
        import re
        m = re.match(r'^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$', size.strip())
        if m:
            return path.strip(), float(m.group(1)), float(m.group(2))
        return path.strip(), None, None
    return s.strip(), None, None



IMG_EXTS = ('.png','.jpg','.jpeg','.gif','.bmp','.svg','.pdf')

def latex_escape(s: str) -> str:
    if s is None: return ""
    s = str(s)
    repl = {"\\":"\\textbackslash{}", "&":"\\&", "%":"\\%", "$":"\\$", "#":"\\#", "_":"\\_", "{":"\\{", "}":"\\}", "~":"\\textasciitilde{}", "^":"\\textasciicircum{}"}
    out = ""
    for ch in s:
        out += repl.get(ch, ch)
    # map angle brackets to text macros to avoid encoding issues
    out = out.replace('<', r'\textless{}').replace('>', r'\textgreater{}')     
    return out

def is_image_path(x: str) -> bool:
    return isinstance(x, str) and any(x.lower().endswith(ext) for ext in IMG_EXTS)

def _label(i: int) -> str:
    abc = "abcdefghijklmnopqrstuvwxyz"
    return abc[i] + ")" if i < len(abc) else f"{i+1})"

def render_images(imgs: List[str], base_dir: str|None=None) -> str:
    lines = [r"\begin{center}"]
    from pathlib import Path
import re

def _parse_img_spec(s: str):
    """Parse 'path;LxA' -> (path, L, A) in mm; or (path, None, None)."""
    if not isinstance(s, str):
        return s, None, None
    if ';' in s:
        path, size = s.split(';',1)
        import re
        m = re.match(r'^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$', size.strip())
        if m:
            return path.strip(), float(m.group(1)), float(m.group(2))
        return path.strip(), None, None
    return s.strip(), None, None


    for img in imgs or []:
        spec_p, wmm, hmm = _parse_img_spec(img)
        p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
        if p.exists():
            if wmm and hmm:
            lines.append(rf"\includegraphics[width={wmm}mm,height={hmm}mm]{{{p.as_posix()}}}")
        else:
            lines.append(rf"\includegraphics[width=0.9\linewidth]{{{p.as_posix()}}}")
        else:
            # quadro vazio 6x4 cm
            lines.append(r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{center}")
    return "\n".join(lines)


def render_afirmacoes_line(afirm: Dict[str,str]) -> str:
    """
    Retorna uma linha única: 'I. ...; II. ...; ...' já com escape LaTeX e \par.
    Ordem fixa I, II, III... sem embaralhar.
    """
    if not afirm:
        return ""
    order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
    labeled = [f"{k}. {afirm[k]}" for k in order if k in afirm]
    if not labeled:
        return ""
    # ESCAPA tudo e junta por '; '
    safe = "; ".join(latex_escape(x) for x in labeled)
    return r"\par " + safe

def render_alts_text(alts: List[str], correta: str, highlight: bool=False) -> str:
    lines = [r"\begin{itemize}"]
    for i, alt in enumerate(alts or []):
        label = _label(i)
        content = latex_escape(alt)
        if highlight and (alt or "").strip() == (correta or "").strip():
            content = r"\alert{" + content + "}"
        lines.append(r"\item[" + label + "] " + content)
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

def render_alts_images(alts: List[str], correta: str, base_dir: str|None=None) -> str:
    lines = [r"\begin{itemize}"]
    for i, alt in enumerate(alts or []):
        label = _label(i)
        spec_p, wmm, hmm = _parse_img_spec(alt)
        p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
        if p.exists():
            if wmm and hmm:
            lines.append(r"\item[" + label + "] " + rf"\includegraphics[width={wmm}mm,height={hmm}mm]{{{p.as_posix()}}}")
        else:
            lines.append(r"\item[" + label + "] " + rf"\includegraphics[width=0.75\linewidth]{{{p.as_posix()}}}")
        else:
            lines.append(r"\item[" + label + "] " + r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

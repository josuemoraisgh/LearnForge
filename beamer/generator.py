# -*- coding: utf-8 -*-
"""
Geração de slides Beamer a partir de JSON de questões.

Padrões aplicados:
- Preâmbulo conforme template usado no projeto (beamer + Madrid, etc.).
- Ordena por id; título do frame: "<id>) <enunciado>".
- Dois frames por questão: (1) sem gabarito; (2) com gabarito (\\alert{...}).
- Frame adicional de OBS. quando houver.
- Alternativas sempre a), b), c), d).
- Tipo 4: afirmativas em linha única "I. ...; II. ...; ..." (escapadas e com \\par).
- Tipo 2: alternativas por imagem; se arquivo não existir (relativo ao JSON), desenha um quadro vazio.
- Caminhos de imagem sempre relativos ao diretório do JSON.

Compatível com a GUI já existente:
json2beamer(input_json, output_tex, shuffle_seed, title, fsq, fsa, alert_color, **kwargs)
"""

from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import json

# --------------------------------------------------------------------
# Helpers internos (auto-contidos para evitar dependência externa)
# --------------------------------------------------------------------

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf')

def _read_text_any(p: Path) -> str:
    b = p.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")

def latex_escape(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in s)

def _label(i: int) -> str:
    abc = "abcdefghijklmnopqrstuvwxyz"
    return abc[i] + ")" if i < len(abc) else f"{i+1})"

def _is_image_path(x: str) -> bool:
    return isinstance(x, str) and any(x.lower().endswith(ext) for ext in IMG_EXTS)

def _alts_with_correct(q: Dict[str, Any]) -> List[str]:
    """
    Garante que a alternativa correta esteja na lista (se não estiver),
    removendo duplicatas e preservando ordem.
    """
    alts = list(q.get("alternativas") or [])
    cor = (q.get("correta") or "").strip()
    if cor and not any((a or "").strip() == cor for a in alts):
        alts.append(cor)
    seen = set()
    out = []
    for a in alts:
        key = (a or "").strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out

def render_images(imgs: List[str], base_dir: str | None = None) -> str:
    """
    Imagens do enunciado, centralizadas; se não houver arquivo, mostra quadro vazio 6x4 cm.
    """
    if not imgs:
        return ""
    lines = [r"\begin{center}"]
    for img in imgs:
        p = Path(base_dir, img) if base_dir else Path(img)
        if p.exists():
            lines.append(rf"\includegraphics[width=0.9\linewidth]{{{p.as_posix()}}}")
        else:
            lines.append(r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{center}")
    return "\n".join(lines)

def render_afirmacoes_line(afirm: Dict[str, str]) -> str:
    """
    Linha única 'I. ...; II. ...; ...' escapada e precedida de \\par.
    Ordem fixa I, II, III… (sem embaralhar).
    """
    if not afirm:
        return ""
    order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
    labeled = [f"{k}. {afirm[k]}" for k in order if k in afirm]
    if not labeled:
        return ""
    safe = "; ".join(latex_escape(x) for x in labeled)
    return r"\par " + safe

def render_alts_text(alts: List[str], correta: str, highlight: bool = False) -> str:
    """
    Alternativas em texto, rotuladas como a), b), c)…; se highlight=True, correta em \alert{...}.
    """
    if not alts:
        return ""
    lines = [r"\begin{itemize}"]
    cor = (correta or "").strip()
    for i, alt in enumerate(alts):
        label = _label(i)
        content = latex_escape(alt or "")
        if highlight and (alt or "").strip() == cor:
            content = r"\alert{" + content + "}"
        lines.append(r"\item[" + label + "] " + content)
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

def render_alts_images(alts: List[str], base_dir: str | None = None) -> str:
    """
    Alternativas com imagens, rotuladas como a), b), c)…; se a imagem não existir, mostra quadro vazio.
    (Para imagens não aplicamos highlight via \alert.)
    """
    if not alts:
        return ""
    lines = [r"\begin{itemize}"]
    for i, alt in enumerate(alts):
        label = _label(i)
        if _is_image_path(alt or ""):
            p = Path(base_dir, alt) if base_dir else Path(alt)
            if p.exists():
                lines.append(r"\item[" + label + "] " + rf"\includegraphics[width=0.75\linewidth]{{{p.as_posix()}}}")
            else:
                lines.append(r"\item[" + label + "] " + r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
        else:
            # Se a alternativa declarada não é imagem, ainda assim mostramos um quadro (com rótulo),
            # conforme sua orientação de “um quadro vazio” quando não há figura.
            lines.append(r"\item[" + label + "] " + r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

# --------------------------------------------------------------------
# Gerador principal
# --------------------------------------------------------------------

def _load_json_list(p: str) -> List[Dict[str, Any]]:
    text = _read_text_any(Path(p))
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{p}: o JSON deve ser um array de questões.")
    return data

def json2beamer(
    input_json='assets/questoes_template.json',
    output_tex='assets/questoes_template_slides.tex',
    shuffle_seed=None,             # aceito por compatibilidade; não embaralhamos no Beamer
    title='Exercícios – Apresentação',
    fsq='Large',
    fsa='normalsize',
    alert_color='red',             # aceito por compatibilidade; \alert usa cor do tema
    **kwargs
) -> int:
    """
    Gera .tex Beamer conforme o padrão acordado.
    - Ordem das questões por id (sem shuffle).
    - Caminhos de imagem relativos ao diretório do JSON.
    """
    # Carregar JSON(s) e detectar diretório base das imagens relativo ao JSON
    if isinstance(input_json, (list, tuple)):
        qs: List[Dict[str, Any]] = []
        json_dirs = []
        for p in input_json:
            qs.extend(_load_json_list(p))
            json_dirs.append(str(Path(p).parent.resolve()))
        base_dir = json_dirs[0] if json_dirs else None
    else:
        qs = _load_json_list(input_json)
        base_dir = str(Path(input_json).parent.resolve())

    # Ordenar por id
    try:
        qs = sorted(qs, key=lambda q: int(q.get("id", 0)))
    except Exception:
        pass

    # PREÂMBULO conforme seu template
    preamble = (
        "\\documentclass[12pt]{beamer}\n"
        "\\usepackage{bookmark}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usetheme{Madrid}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{enumitem}\n"
        "\\title{" + latex_escape(title) + "}\n"
        "\\author{}\n"
        "\\date{}\n"
    )

    parts: List[str] = [
        preamble,
        "\\begin{document}\n",
        "\\frame{\\titlepage}\n",
        f"\\setbeamerfont{{frametitle}}{{size=\\{fsq}}}\n",
        f"\\newcommand{{\\BodySize}}{{\\{fsa}}}\n",
    ]

    for q in qs:
        qid = q.get("id", "?")
        enun = (q.get("enunciado", "") or "").strip()
        enun_tex = latex_escape(enun)
        tipo = int(q.get("tipo", 1))

        # Alternativas: SEM embaralhar no Beamer; garante correta presente
        alts = _alts_with_correct(q)

        # ---------------- Frame 1: sem gabarito ----------------
        parts.append("\\begin{frame}")
        parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
        parts.append("{\\BodySize")

        # Imagens do enunciado
        imgs = q.get("imagens") or []
        if imgs:
            parts.append(render_images(imgs, base_dir=base_dir))

        # Afirmativas (Tipo 4) — linha única com escape + \par
        if q.get("afirmacoes"):
            parts.append(render_afirmacoes_line(q["afirmacoes"]))

        # Alternativas
        if tipo == 2:
            parts.append(render_alts_images(alts, base_dir=base_dir))
        else:
            parts.append(render_alts_text(alts, q.get("correta", ""), highlight=False))

        parts.append("}")
        parts.append("\\end{frame}\n")

        # ---------------- Frame 2: com gabarito ----------------
        parts.append("\\begin{frame}")
        parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
        parts.append("{\\BodySize")

        if imgs:
            parts.append(render_images(imgs, base_dir=base_dir))

        if q.get("afirmacoes"):
            parts.append(render_afirmacoes_line(q["afirmacoes"]))

        if tipo == 2:
            # Para imagem, mantemos sem highlight; apenas repetimos as imagens/quadro
            parts.append(render_alts_images(alts, base_dir=base_dir))
        else:
            # Para texto, destaca a correta
            parts.append(render_alts_text(alts, q.get("correta", ""), highlight=True))

        parts.append("}")
        parts.append("\\end{frame}\n")

        # ---------------- Frame 3: OBS (se houver) ----------------
        obs = q.get("obs")
        obs_items = []
        if isinstance(obs, str) and obs.strip():
            obs_items = [obs.strip()]
        elif isinstance(obs, (list, tuple)):
            obs_items = [str(x).strip() for x in obs if str(x).strip()]

        if obs_items:
            parts.append("\\begin{frame}")
            parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
            parts.append("{\\BodySize")
            parts.append("\\textbf{OBS.:}")
            parts.append("\\begin{itemize}")
            for it in obs_items:
                parts.append("\\item " + latex_escape(it))
            parts.append("\\end{itemize}")
            parts.append("}")
            parts.append("\\end{frame}\n")

    parts.append("\\end{document}\n")

    out = Path(output_tex)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return 0
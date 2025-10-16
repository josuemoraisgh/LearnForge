
# -*- coding: utf-8 -*-
"""
Geração de slides Beamer a partir de JSON de questões.
Responsabilidade: orquestrar a construção do .tex (usa latex_utils).
"""
from typing import List, Dict, Any
import json, random
from .latex_utils import (
    latex_escape, is_image_path, render_images, render_afirmacoes,
    render_alts_text, render_alts_images
)

def combine_and_shuffle_alternatives(q: Dict[str, Any], rng: random.Random) -> List[str]:
    """Inclui a correta (se faltar), remove duplicatas preservando ordem e embaralha."""
    alts = list(q.get("alternativas", []) or [])
    correta = (q.get("correta") or "").strip()
    if correta and not any((a or "").strip() == correta for a in alts):
        alts.append(correta)
    seen = set(); dedup = []
    for a in alts:
        key = (a or "").strip()
        if key in seen: continue
        seen.add(key); dedup.append(a)
    rng.shuffle(dedup)
    return dedup

def beamer_title_block(title: str) -> str:
    return "\\title{{{}}}\n\\author{{}}\n\\date{{}}\n".format(latex_escape(title or "Exercícios"))

def frame_title_text(q: Dict[str, Any]) -> str:
    qid = q.get("id","?")
    enun = (q.get("enunciado","") or "").strip()
    return "{}. {}".format(qid, latex_escape(enun))

def frame_question(q: Dict[str, Any], show_answer: bool, alts_shuffled: List[str]) -> str:
    imgs = q.get("imagens", [])
    correta = (q.get("correta","") or "").strip()
    tipo = int(q.get("tipo", 1))

    lines = [r"\begin{frame}", f"\\frametitle{{{frame_title_text(q)}}}"]
    lines.append(r"{\BodySize")

    if imgs:
        lines.append(render_images(imgs))
    if tipo == 4:
        lines.append(render_afirmacoes(q.get("afirmacoes", {})))

    if tipo == 2:
        lines.append(render_alts_images(alts_shuffled, correta, highlight=show_answer))
    else:
        lines.append(render_alts_text(alts_shuffled, correta, highlight=show_answer))

    lines.append("}")
    lines.append(r"\end{frame}")
    return "\n".join(lines) + "\n"

def frame_obs(q: Dict[str, Any]) -> str:
    obs_raw = q.get("obs")
    if isinstance(obs_raw, str):
        items = [obs_raw.strip()] if obs_raw.strip() else []
    elif isinstance(obs_raw, (list, tuple)):
        items = [str(x).strip() for x in obs_raw if isinstance(x, str) and str(x).strip()]
    else:
        items = []
    if not items:
        return ""

    lines = [r"\begin{frame}", f"\\frametitle{{{frame_title_text(q)}}}"]
    lines.append(r"{\BodySize")
    lines.append(r"\textbf{OBS.:}")
    lines.append(r"\begin{itemize}")
    for it in items:
        lines.append("\\item " + latex_escape(it))
    lines.append(r"\end{itemize}")
    lines.append("}")
    lines.append(r"\end{frame}")
    return "\n".join(lines) + "\n"

def json2beamer(
    input_json = 'Exercicios_NS.json',
    output_tex  = 'Exercicios_NS_slides.tex',
    shuffle_seed = None,
    title = "Exercícios – Apresentação",
    fsq = "Large",
    fsa = "normalsize",
    alert_color = "red"
    ) -> int:

    data = json.load(open(input_json, "r", encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("O JSON deve ser um array de questões.")

    preamble = (
        "\\documentclass[12pt]{beamer}\n"
        "\\usepackage{bookmark}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usetheme{Madrid}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{enumitem}\n"
    )
    post = "\\end{document}\n"

    parts: List[str] = [
        preamble,
        beamer_title_block(title),
        r"\begin{document}",
        r"\frame{\titlepage}",
        f"\\setbeamerfont{{frametitle}}{{size=\\{fsq}}}",
        f"\\newcommand{{\\BodySize}}{{\\{fsa}}}",
    ]

    rng = random.Random(shuffle_seed)
    qs = sorted(data, key=lambda q: q.get("id", 0))

    for q in qs:
        alts_shuffled = combine_and_shuffle_alternatives(q, rng)
        parts.append(frame_question(q, show_answer=False, alts_shuffled=alts_shuffled))
        parts.append(frame_question(q, show_answer=True,  alts_shuffled=alts_shuffled))
        obs_frame = frame_obs(q)
        if obs_frame:
            parts.append(obs_frame)

    parts.append(post)

    with open(output_tex, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("Arquivo gerado:", output_tex)
    return 0

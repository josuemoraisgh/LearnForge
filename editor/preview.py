# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any

def preview_text(questions: List[Dict[str, Any]], title: str|None=None, **kwargs) -> str:
    """
    Preview unificado:
    - Ordena por id (id mostrado antes do enunciado)
    - Tipo 3: resolve <VAR>, <RES> e expressões (<TEMP + 1>, etc.)
    - Tipo 4: mostra linha "I. ...; II. ...; ..." (sem embaralhar)
    - Alternativas sempre a), b), c), d)
    - Imagem nas alternativas: mostra "[imagem: caminho]" no preview
    """
    from core.variables import resolve_all
    # seed opcional para bater com Beamer/Prova quando informado
    seed = kwargs.get("seed", None)

    # 1) ordena por id
    try:
        questions = sorted(questions, key=lambda q: int(q.get("id", 0)))
    except Exception:
        pass

    alph = "abcdefghijklmnopqrstuvwxyz"
    lines: List[str] = []
    if title:
        lines += [title, "-"*max(8, len(title))]

    for q in questions:
        # 2) resolve variáveis/resoluções e substitui em todos os campos (Tipo 3)
        q_res, _env = resolve_all(q, seed=seed)

        qid = q_res.get("id", "?")
        enun = str(q_res.get("enunciado", "") or "").strip()
        lines.append(f"{qid}) {enun}")

        # 3) Tipo 4: linha de afirmativas (I; II; III; ...) SEM embaralhar
        afirm = q_res.get("afirmacoes") or {}
        if isinstance(afirm, dict) and afirm:
            order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
            labeled = [f"{k}. {afirm[k]}" for k in order if k in afirm]
            if labeled:
                lines.append("   " + "; ".join(labeled))

        # 4) Alternativas: a), b), c) ...
        alts = q_res.get("alternativas") or []
        for i, alt in enumerate(alts):
            label = alph[i] + ")" if i < len(alph) else f"{i+1})"
            s = str(alt or "")
            # se parecer imagem, no preview mostro só um marcador textual
            if s.lower().endswith((".png",".jpg",".jpeg",".gif",".bmp",".svg",".pdf")):
                s = f"[imagem: {s}]"
            lines.append(f"   {label} {s}")

        lines.append("")  # linha em branco entre questões

    return "\n".join(lines)
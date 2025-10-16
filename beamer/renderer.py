
from __future__ import annotations
from typing import List, Dict, Any
from core.models import RenderOptions
from core.pipeline import render_all

def render_for_tex(raw_questions: List[Dict[str, Any]], seed: int|None=None) -> List[Dict[str, Any]]:
    """
    Returns a list of resolved questions for LaTeX Beamer.
    Keeps the JSON order and the alternatives order.
    Adds labeled afirmations into 'afirmacoes_view' for Type 4.
    """
    opts = RenderOptions(
        target="beamer",
        shuffle_questions=False,
        shuffle_alternatives=False,
        seed=seed,
    )
    rqs = render_all(raw_questions, opts)
    out: List[Dict[str, Any]] = []
    for r in rqs:
        item = {
            "id": r.id,
            "tipo": int(r.tipo),
            "enunciado": r.enunciado,
            "imagens": r.imagens,
            "alternativas": r.alternativas,
            "correta": r.correta,
        }
        if "afirmacoes_labeled" in r.extra:
            item["afirmacoes_view"] = r.extra["afirmacoes_labeled"]
        out.append(item)
    return out

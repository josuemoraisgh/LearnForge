
from __future__ import annotations
from typing import List, Dict, Any
from core.models import RenderOptions
from core.pipeline import render_all

def render_for_docx(raw_questions: List[Dict[str, Any]], seed: int|None=None, shuffle_questions: bool=True, shuffle_alternatives: bool=True) -> List[Dict[str, Any]]:
    """
    Returns a list of resolved questions for DOCX generator.
    Shuffles both questions and alternatives (deterministic if seed given).
    """
    opts = RenderOptions(
        target="testgen",
        shuffle_questions=shuffle_questions,
        shuffle_alternatives=shuffle_alternatives,
        seed=seed,
    )
    rqs = render_all(raw_questions, opts)
    out: List[Dict[str, Any]] = []
    for r in rqs:
        out.append({
            "id": r.id,
            "tipo": int(r.tipo),
            "enunciado": r.enunciado,
            "imagens": r.imagens,
            "alternativas": r.alternativas,
            "correta": r.correta,
            "extra": r.extra,
        })
    return out

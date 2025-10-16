
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

ROMAN = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]

@dataclass
class RenderedQuestion:
    id: int
    tipo: int
    enunciado: str
    imagens: List[str]
    alternativas: List[str]
    correta: str
    extra: Dict[str, Any]

def render_type4(q: Dict[str, Any]) -> Dict[str, Any]:
    afirm = q.get("afirmacoes") or {}
    # mantém a ordem natural I, II, III...
    ordered = [k for k in ROMAN if k in afirm]
    labeled = [f"{k}. {afirm[k]}" for k in ordered]
    line = "; ".join(labeled)
    q["extra"] = q.get("extra") or {}
    q["extra"]["afirmacoes_labeled"] = labeled
    q["extra"]["afirmacoes_line"] = line
    return q

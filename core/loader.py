
from __future__ import annotations
from typing import List, Dict, Any
from .models import Question

def normalize_ids(questions: List[Question]) -> None:
    questions.sort(key=lambda q: q.id or 0)
    for i, q in enumerate(questions, start=1):
        q.id = i

def load_questions(raw: List[Dict[str, Any]]) -> List[Question]:
    qs = [Question.from_dict(x) for x in raw]
    normalize_ids(qs)
    for q in qs:
        if not q.dificuldade:
            q.dificuldade = "média"
        if not isinstance(q.alternativas, list):
            q.alternativas = []
        if not isinstance(q.imagens, list):
            q.imagens = []
        if q.tipo.value == 3:
            if not q.variaveis or not q.resolucoes:
                raise ValueError(f"Questão {q.id}: Tipo 3 requer 'variaveis' e 'resolucoes'.")
        if q.tipo.value == 4 and not q.afirmacoes:
            raise ValueError(f"Questão {q.id}: Tipo 4 requer 'afirmacoes'.")
        if not q.enunciado.strip():
            raise ValueError(f"Questão {q.id}: 'enunciado' não pode ser vazio.")
    return qs

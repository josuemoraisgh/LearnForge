import json
from typing import List, Dict, Any
from pathlib import Path
from core.models import QuestionIR, QuizIR, QuestionKind
# apenas ao import, registre builders:
from core.types.type1 import Type1Builder
from core.types.type2 import Type2Builder
from core.types.type3 import Type3Builder
from core.types.type4 import Type4Builder
from core.registry import register, get_builder

# registra uma vez (poderia ser em core/__init__)
register(Type1Builder())
register(Type2Builder())
register(Type3Builder())
register(Type4Builder())

def load_jsons(paths: List[str]) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, list):
            raise ValueError(f"JSON precisa ser uma lista de questões: {p}")
        data.extend(obj)
    return data

def to_ir(raw_questions: List[Dict[str, Any]], title="Quiz") -> QuizIR:
    """Valida e converte todas as questões em IR, com reindexação de id."""
    out: List[QuestionIR] = []
    for i, q in enumerate(raw_questions, start=1):
        kind_str = q.get("type") or q.get("kind")
        if not kind_str:
            raise ValueError(f"Questão sem 'type': {q}")
        kind = QuestionKind(kind_str)
        builder = get_builder(kind)
        out.append(builder.build_ir(q, new_id=i))
    return QuizIR(title=title, questions=out)

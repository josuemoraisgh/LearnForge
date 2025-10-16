from typing import Dict, Type
from core.types.base import QuestionTypeBuilder
from core.models import QuestionKind

_REGISTRY: Dict[QuestionKind, QuestionTypeBuilder] = {}

def register(builder: QuestionTypeBuilder):
    _REGISTRY[builder.kind] = builder

def get_builder(kind: QuestionKind) -> QuestionTypeBuilder:
    if kind not in _REGISTRY:
        raise KeyError(f"Question type não registrado: {kind}")
    return _REGISTRY[kind]

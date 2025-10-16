from abc import ABC, abstractmethod
from typing import Dict, Any
from core.models import QuestionIR, QuestionKind

class QuestionTypeBuilder(ABC):
    kind: QuestionKind

    @abstractmethod
    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        """Converte o dict da questão daquele tipo em QuestionIR."""

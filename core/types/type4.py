# core/types/type4.py
from typing import Dict, Any, List, Tuple
from ..models import QuestionIR, QuestionKind, Choice
from .base import QuestionTypeBuilder

class Type4Builder(QuestionTypeBuilder):
    """
    Tipo sem alternativas visuais:
      - Resposta curta: { "type":"type4", "prompt":"...", "answer":"Ohm" } 
                        ou { "answers": ["Ohm","Ω"] }
      - Associação (matching): { "type":"type4", "prompt":"...", "pairs":[["LED","Diodo emissor"], ["R","Resistor"]] }
    """
    kind = QuestionKind.TYPE4

    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        prompt = raw.get("prompt", "").strip()
        sol = raw.get("solution")

        choices: List[Choice] = []  # normalmente vazio

        if "pairs" in raw:
            # associação
            pairs: List[List[str]] = raw["pairs"]
            # gabarito textual
            mapping = [f"{i+1}) {a} ↔ {b}" for i, (a, b) in enumerate(pairs)]
            if sol is None:
                sol = "Associação (gabarito):\n" + "\n".join(mapping)
            # dica para renderizadores (podem desenhar duas colunas etc.)
            meta = {"pairs": pairs, **raw.get("meta", {})}
        else:
            # resposta curta
            answers = raw.get("answers")
            answer = raw.get("answer")
            acc = []
            if isinstance(answers, list) and answers:
                acc = [str(x) for x in answers]
            elif answer is not None:
                acc = [str(answer)]
            if sol is None and acc:
                sol = "Resposta: " + " / ".join(acc)
            meta = {"answers": acc, **raw.get("meta", {})}

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,
            solution=sol,
            metadata=meta
        )

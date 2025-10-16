# core/types/type2.py
from typing import Dict, Any
from ..models import QuestionIR, QuestionKind, Choice
from .base import QuestionTypeBuilder

class Type2Builder(QuestionTypeBuilder):
    """
    Verdadeiro/Falso (ou Sim/Não).
    Aceita JSON:
    { "type":"type2", "prompt":"...", "answer": true }        # boolean
    { "type":"type2", "prompt":"...", "answer":"true|false" }
    { "type":"type2", "prompt":"...", "answer":"V|F|S|N" }
    """
    kind = QuestionKind.TYPE2

    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        prompt = raw.get("prompt", "").strip()
        sol = raw.get("solution")

        truth = self._parse_bool(raw.get("answer"))
        # padrão VF
        choices = [
            Choice(text="Verdadeiro", is_correct=truth is True),
            Choice(text="Falso",     is_correct=truth is False),
        ]
        if sol is None and truth is not None:
            sol = "Resposta: Verdadeiro" if truth else "Resposta: Falso"

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,
            solution=sol,
            metadata={ **(raw.get("meta") or {}), "obs": raw.get("obs", []) }
        )

    def _parse_bool(self, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("v", "verdadeiro", "true", "t", "sim", "s", "yes", "y", "1"):
                return True
            if s in ("f", "falso", "false", "n", "nao", "não", "no", "0"):
                return False
        return None

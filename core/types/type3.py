from typing import Dict, Any, List
from ..models import QuestionIR, QuestionKind, Choice
from ..utils import mathx
from .base import QuestionTypeBuilder

class Type3Builder(QuestionTypeBuilder):
    kind = QuestionKind.TYPE3

    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        # Ex.: raw contém números, operação, unidades; gerar prompt e alternativas
        a = float(raw["a"])
        b = float(raw["b"])
        op = raw.get("op", "+")
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            result = a / b if b != 0 else float("inf")
        else:
            raise ValueError(f"Operação não suportada: {op}")

        result_fmt = mathx.round_sig(result, sig=4)
        correct = Choice(text=str(result_fmt), is_correct=True)

        # distratores numéricos simples
        ds = [
            Choice(text=str(mathx.round_sig(result * 1.1, 4))),
            Choice(text=str(mathx.round_sig(result * 0.9, 4))),
            Choice(text=str(mathx.round_sig(result + 1, 4))),
        ]
        choices = [correct] + ds

        prompt = raw.get("prompt") or f"Calcule: {a} {op} {b}"
        sol = raw.get("solution") or f"Resultado: {result_fmt}"

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,
            solution=sol,
            metadata=raw.get("meta", {})
        )

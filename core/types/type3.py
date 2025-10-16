# core/types/type3.py
from typing import Dict, Any, List
from ..models import QuestionIR, QuestionKind, Choice, Asset
from .base import QuestionTypeBuilder
from ..utils import mathx  # se você usar matemática; se não, pode remover

class Type3Builder(QuestionTypeBuilder):
    kind = QuestionKind.TYPE3

    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        prompt = (raw.get("prompt") or raw.get("enunciado") or "").strip()

        # alternativas + correta vindas do JSON (independente da matemática)
        alts = list(raw.get("alternativas") or raw.get("options") or [])
        correta_txt = (raw.get("correta") or raw.get("answer") or "").strip()
        if correta_txt and (correta_txt not in [str(a).strip() for a in alts]):
            alts.append(correta_txt)
        choices = [Choice(text=str(t), is_correct=(str(t).strip() == correta_txt)) for t in alts]

        # imagens / obs
        imagens = raw.get("imagens") or raw.get("imagem")
        if isinstance(imagens, str):
            imagens = [imagens]
        assets = [Asset(kind="image", src=s) for s in (imagens or [])]

        # se você já tiver resoluções/variáveis e quiser calcular a correta, pode
        # chamar sua lógica aqui; mas NÃO deixe de preencher as choices.

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,
            solution=(raw.get("solution") or raw.get("solucao")),
            assets=assets,
            metadata={
                **(raw.get("meta") or {}),
                "obs": raw.get("obs", []),
                "variaveis": raw.get("variaveis"),
                "resolucoes": raw.get("resolucoes"),
            },
        )

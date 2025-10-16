# core/types/type4.py
from typing import Dict, Any, List, Tuple
from ..models import QuestionIR, QuestionKind, Choice, Asset
from .base import QuestionTypeBuilder

class Type4Builder(QuestionTypeBuilder):
    kind = QuestionKind.TYPE4

    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        prompt = (raw.get("prompt") or raw.get("enunciado") or "").strip()

        # --- afirmações ---
        afirm = raw.get("afirmacoes") or raw.get("pairs")
        afirm_list: List[Tuple[str, str]] = []
        if isinstance(afirm, dict):
            # preserva ordem se veio de JSON (Python 3.7+ já preserva)
            afirm_list = [(k, str(v)) for k, v in afirm.items()]
        elif isinstance(afirm, list):
            # permite [["I","texto"], ...] ou [{"I":"texto"}, ...]
            for it in afirm:
                if isinstance(it, (list, tuple)) and len(it) >= 2:
                    afirm_list.append((str(it[0]), str(it[1])))
                elif isinstance(it, dict):
                    for k, v in it.items():
                        afirm_list.append((str(k), str(v)))

        # --- alternativas + correta ---
        alts = list(raw.get("alternativas") or raw.get("options") or [])
        correta_txt = (raw.get("correta") or raw.get("answer") or "").strip()

        # garante que a correta esteja na lista (se for texto que não esteja lá)
        if correta_txt and (correta_txt not in [str(a).strip() for a in alts]):
            alts.append(correta_txt)

        choices = [Choice(text=str(t), is_correct=(str(t).strip() == correta_txt)) for t in alts]

        # --- imagens / obs ---
        imagens = raw.get("imagens") or raw.get("imagem")
        if isinstance(imagens, str):
            imagens = [imagens]
        assets = [Asset(kind="image", src=s) for s in (imagens or [])]

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,                       # podem estar vazias; renderer lida
            solution=None,
            assets=assets,
            metadata={
                **(raw.get("meta") or {}),
                "obs": raw.get("obs", []),
                "afirmacoes": afirm_list,         # <- usado no beamer
            },
        )

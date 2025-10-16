# core/types/type1.py
from typing import Dict, Any, List
from ..models import QuestionIR, QuestionKind, Choice
from .base import QuestionTypeBuilder

class Type1Builder(QuestionTypeBuilder):
    """
    Múltipla escolha.
    Aceita JSON nos formatos:
    A) { "type":"type1", "prompt": "...", "choices":[{"text":"A","correct":true}, ...] }
    B) { "type":"type1", "prompt": "...", "options":["A","B","C","D"], "answer": 1 }  # índice ou letra
    C) { "type":"type1", "prompt": "...", "options":["A","B","C","D"], "answers":[0,2] }  # múltiplas
    """
    kind = QuestionKind.TYPE1

    def build_ir(self, raw: Dict[str, Any], new_id: int) -> QuestionIR:
        prompt = raw.get("prompt", "").strip()
        sol = raw.get("solution")

        choices: List[Choice] = []

        if "choices" in raw and isinstance(raw["choices"], list):
            # formato A
            for c in raw["choices"]:
                txt = str(c.get("text", ""))
                is_ok = bool(c.get("correct", False))
                choices.append(Choice(text=txt, is_correct=is_ok, meta={k:v for k,v in c.items() if k not in ("text","correct")}))
            if sol is None:
                # tenta montar solução a partir das corretas
                corrects = [c.text for c in choices if c.is_correct]
                sol = "Resposta: " + (", ".join(corrects) if corrects else "(nenhuma marcada)")
        else:
            # formatos B/C
            options = raw.get("options") or raw.get("alternatives") or []
            answers = raw.get("answers")
            answer = raw.get("answer")
            correct_idx: List[int] = []
            if isinstance(answers, list):
                # múltiplas
                for a in answers:
                    correct_idx.append(self._norm_index(a, len(options)))
            elif answer is not None:
                correct_idx.append(self._norm_index(answer, len(options)))

            for i, txt in enumerate(options):
                choices.append(Choice(text=str(txt), is_correct=(i in correct_idx)))

            if sol is None and correct_idx:
                # letras a,b,c,... (a=0)
                letters = [chr(97+i) for i in correct_idx]
                sol = "Resposta: " + ", ".join(letters)

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,
            solution=sol,
            metadata=raw.get("meta", {})
        )

    def _norm_index(self, x, n):
        # aceita 0-based, 1-based e letras ("a"/"A")
        if isinstance(x, int):
            if 0 <= x < n:
                return x
            if 1 <= x <= n:
                return x-1
        if isinstance(x, str) and x:
            ch = x.strip().lower()
            if ch.isalpha() and len(ch) == 1:
                return ord(ch) - 97
            if ch.isdigit():
                k = int(ch)
                return k-1 if 1 <= k <= n else k
        return -1

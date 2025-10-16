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
        prompt = (raw.get("prompt") or raw.get("enunciado") or "").strip()
        sol = raw.get("solution")

        choices: List[Choice] = []

        # Formato A: choices = [{"text":"...","correct":true}, ...]
        if isinstance(raw.get("choices"), list):
            for c in raw["choices"]:
                txt = str(c.get("text", ""))
                is_ok = bool(c.get("correct", False))
                choices.append(Choice(text=txt, is_correct=is_ok,
                                      meta={k:v for k,v in c.items() if k not in ("text","correct")}))
            if sol is None:
                corrects = [c.text for c in choices if c.is_correct]
                if corrects:
                    sol = "Resposta: " + ", ".join(corrects)

        else:
            # Formato B/C antigo: options/answers/answer
            options = (
                raw.get("options")
                or raw.get("alternatives")
                or raw.get("alternativas")
                or []
            )
            answer = raw.get("answer")
            answers = raw.get("answers")
            correta_txt = raw.get("correta")

            correct_idx: List[int] = []

            # 1) múltiplas pelo campo "answers"
            if isinstance(answers, list) and options:
                for a in answers:
                    idx = self._norm_index_or_text(a, options)
                    if idx >= 0:
                        correct_idx.append(idx)

            # 2) única pelo campo "answer"
            elif answer is not None and options:
                idx = self._norm_index_or_text(answer, options)
                if idx >= 0:
                    correct_idx.append(idx)

            # 3) antiga: "correta" (texto da alternativa ou letra/índice)
            if not correct_idx and correta_txt and options:
                idx = self._norm_index_or_text(correta_txt, options)
                if idx >= 0:
                    correct_idx.append(idx)

            for i, txt in enumerate(options):
                choices.append(Choice(text=str(txt), is_correct=(i in set(correct_idx))))

            if sol is None and correct_idx:
                # monta solução por letra (a,b,c,...) ou texto
                letters = [chr(97+i) for i in correct_idx]
                sol = "Resposta: " + ", ".join(letters)

        return QuestionIR(
            id=new_id,
            kind=self.kind,
            prompt=prompt,
            choices=choices,
            solution=sol,
            metadata={ **(raw.get("meta") or {}), "obs": raw.get("obs", []) }
        )

    def _norm_index_or_text(self, x, options: List[str]) -> int:
        """Aceita 0/1-based, letras (a,b,...) OU texto igual a uma opção."""
        n = len(options)
        # texto igual?
        if isinstance(x, str):
            s = x.strip()
            # match por texto exato
            for i, opt in enumerate(options):
                if s == str(opt).strip():
                    return i
            # letra (a,b,...)
            ch = s.lower()
            if ch.isalpha() and len(ch) == 1:
                return ord(ch) - 97
            # dígito
            if ch.isdigit():
                k = int(ch)
                if 1 <= k <= n:
                    return k - 1
                if 0 <= k < n:
                    return k
            return -1

        # inteiro
        if isinstance(x, int):
            if 0 <= x < n:
                return x
            if 1 <= x <= n:
                return x - 1

        return -1

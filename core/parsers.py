import json
from typing import List, Dict, Any, Iterable, Union
from pathlib import Path
from core.models import QuestionIR, QuizIR, QuestionKind
# apenas ao import, registre builders:
from core.types.type1 import Type1Builder
from core.types.type2 import Type2Builder
from core.types.type3 import Type3Builder
from core.types.type4 import Type4Builder
from core.registry import register, get_builder
from __future__ import annotations
# (mantenha os demais imports que você já tem)


# registra uma vez (poderia ser em core/__init__)
register(Type1Builder())
register(Type2Builder())
register(Type3Builder())
register(Type4Builder())

def _normalize_alternativas_key_inplace(q: Dict[str, Any]) -> None:
    """
    Converte chaves 'alternativas;K' do dict cru (lido do JSON) em:
      - q['alternativas'] = <lista inteira>  (se 'alternativas' estiver ausente/ não-lista/ vazia)
      - q['_firstrow'] = K  (metadado para o Beamer)
    Remove TODAS as chaves 'alternativas;K' ao final.
    """
    alts_std = q.get("alternativas")

    # coletar TODAS as chaves alternativas;K
    altk_entries: list[tuple[str, int | None]] = []
    for k in list(q.keys()):
        if isinstance(k, str) and k.startswith("alternativas;"):
            try:
                K = int(k.split(";", 1)[1])
            except Exception:
                K = None
            altk_entries.append((k, K))

    if not altk_entries:
        return

    # anota um K válido
    for _, K in altk_entries:
        if K is not None:
            q["_firstrow"] = K
            break

    # substituir 'alternativas' se ausente/não-lista/vazia
    need_replace = (not isinstance(alts_std, list)) or (len(alts_std) == 0)
    if need_replace:
        placed = False
        for key, _ in altk_entries:
            v = q.get(key)
            if isinstance(v, list):
                q["alternativas"] = list(v)  # COPIA A LISTA INTEIRA
                placed = True
                break
        if not placed:
            # fallback (raro): se nenhum 'alternativas;K' é lista
            for key, _ in altk_entries:
                v = q.get(key)
                q["alternativas"] = [] if v is None else [v]
                break

    # REMOVER TODAS as 'alternativas;K' para ninguém sobrescrever depois
    for key, _ in altk_entries:
        q.pop(key, None)

def load_jsons(paths: Union[str, Path, Iterable[Union[str, Path]]]) -> List[Dict[str, Any]]:
    """
    Lê 1..N arquivos .json e retorna uma lista de dicts (questões) já normalizados.
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    out: List[Dict[str, Any]] = []
    for p in paths:
        p = Path(p)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"{p}: conteúdo deve ser um array de questões (list).")

        for q in data:
            if not isinstance(q, dict):
                continue
            # <<< NORMALIZAÇÃO AQUI >>>
            _normalize_alternativas_key_inplace(q)
            # (opcional) anote de onde veio o JSON, se você usa isso em outro lugar
            q.setdefault("__json_dir", str(p.parent.resolve()))
            out.append(q)

    return out


def to_ir(raw_questions: List[Dict[str, Any]], title="Quiz") -> QuizIR:
    out: List[QuestionIR] = []
    for i, q in enumerate(raw_questions, start=1):
        # NOVO: aceitar vários jeitos de indicar o tipo
        kind_val = q.get("type") or q.get("kind") or q.get("questionType")

        if not kind_val and "tipo" in q:
            # mapeia 1/2/3/4 -> enums
            try:
                tipo_int = int(q["tipo"])
            except Exception:
                raise ValueError(f"Campo 'tipo' inválido: {q.get('tipo')}")
            mapa = {
                1: QuestionKind.TYPE1,
                2: QuestionKind.TYPE2,
                3: QuestionKind.TYPE3,
                4: QuestionKind.TYPE4,
            }
            kind = mapa.get(tipo_int)
            if not kind:
                raise ValueError(f"Tipo numérico não suportado: {tipo_int}")
        else:
            # aceita "type": "type1" (string)
            if not kind_val:
                raise ValueError(f"Questão sem 'type'/'tipo': {q}")
            kind = QuestionKind(str(kind_val))

        builder = get_builder(kind)
        out.append(builder.build_ir(q, new_id=i))

    return QuizIR(title=title, questions=out)


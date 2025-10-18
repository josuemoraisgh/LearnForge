from __future__ import annotations
from typing import List, Dict, Any
from .models import Question

def _normalize_alternativas_key(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte 'alternativas;K' em:
      - q['alternativas'] = <lista inteira>
      - q['_firstrow'] = K
    e remove TODAS as chaves 'alternativas;K'.
    Se 'alternativas' já existir e não for vazia, ela é preservada; o K é apenas anotado.
    """
    alts_std = q.get("alternativas")

    # Coletar TODAS as chaves alternativas;K
    altk_entries: list[tuple[str, int | None]] = []
    for k in list(q.keys()):
        if isinstance(k, str) and k.startswith("alternativas;"):
            try:
                K = int(k.split(";", 1)[1])
            except Exception:
                K = None
            altk_entries.append((k, K))

    if altk_entries:
        # Anotar um K válido (primeiro que for int)
        for _, K in altk_entries:
            if K is not None:
                q["_firstrow"] = K
                break

        # Substituir 'alternativas' se ausente/não-lista/vazia
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
                # Fallback se nenhuma das 'alternativas;K' for lista
                for key, _ in altk_entries:
                    v = q.get(key)
                    q["alternativas"] = [] if v is None else [v]
                    break

        # REMOVER TODAS as 'alternativas;K' para ninguém consumir depois
        for key, _ in altk_entries:
            q.pop(key, None)

    return q


def _normalize_alternativas_on_raw(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aplica a normalização em todos os dicts de questões lidos do JSON."""
    return [_normalize_alternativas_key(dict(q)) for q in raw]


def load_questions(raw: List[Dict[str, Any]], renumber_ids: bool = False) -> List[Question]:
    """
    1) Normaliza 'alternativas;K' -> 'alternativas' + '_firstrow' e remove 'alternativas;K'
    2) Constrói Question.from_dict(...)
    3) (Opcional) renumera IDs
    4) Validações leves
    """
    # (1) Normalizar AQUI, antes de construir os objetos
    raw = _normalize_alternativas_on_raw(raw)

    # (2) Agora sim, construir objetos
    qs = [Question.from_dict(x) for x in raw]

    # (3) Renumerar (se desejar)
    if renumber_ids:
        qs.sort(key=lambda q: q.id or 0)
        for i, q in enumerate(qs, start=1):
            q.id = i

    # (4) Validações leves (ajuste conforme seu modelo)
    for q in qs:
        if not q.dificuldade:
            q.dificuldade = "média"
        if not isinstance(q.alternativas, list):
            q.alternativas = []
        if not isinstance(q.imagens, list):
            q.imagens = []
        if q.tipo.value == 3:
            if not q.variaveis or not q.resolucoes:
                raise ValueError(f"Questão {q.id}: Tipo 3 requer 'variaveis' e 'resolucoes'.")
        if q.tipo.value == 4 and not q.afirmacoes:
            raise ValueError(f"Questão {q.id}: Tipo 4 requer 'afirmacoes'.")
        if not (q.enunciado or "").strip():
            raise ValueError(f"Questão {q.id}: 'enunciado' não pode ser vazio.")

    return qs
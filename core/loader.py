
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json, zipfile, logging

from .prepare import (
    normalize_alternativas_inplace,
    resolve_question_inplace,
    prepare_alternativas_inplace,
)

logger = logging.getLogger(__name__)

class QuizLoadError(Exception):
    """Erro de leitura/normalização do questionário."""
    pass

def _coerce_to_data(obj: Union[str, bytes, Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    if isinstance(obj, (dict, list)): return obj
    if isinstance(obj, (str, bytes)):
        try:
            return json.loads(obj)
        except Exception as e:
            raise QuizLoadError(f"JSON inválido: {e}") from e
    raise QuizLoadError(f"Tipo não suportado: {type(obj).__name__}")

def _read_json_file(p: Path) -> Union[Dict[str, Any], List[Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise QuizLoadError(f"Erro lendo '{p}': {e}") from e

def _read_zip(p: Path) -> List[Union[Dict[str, Any], List[Any]]]:
    try:
        out=[]
        with zipfile.ZipFile(p, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".json"):
                    out.append(json.loads(z.read(name).decode("utf-8")))
        return out
    except zipfile.BadZipFile as e:
        raise QuizLoadError(f"Arquivo ZIP inválido '{p}': {e}") from e

def _ensure_questions(data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [q for q in data if isinstance(q, dict)]
    if isinstance(data, dict):
        for k in ("questions","questoes","lista","itens"):
            v = data.get(k)
            if isinstance(v, list):
                return [q for q in v if isinstance(q, dict)]
    return []

def _normalize_dataset(
    data: Union[Dict[str, Any], List[Any]],
    *,
    shuffle_seed: Optional[int],
    resolve_vars: bool,
    merge_correct: bool,
    dedup: bool
) -> Dict[str, Any]:
    qs = _ensure_questions(data)
    norm_qs: List[Dict[str, Any]] = []
    for q in qs:
        if not isinstance(q, dict):
            continue
        normalize_alternativas_inplace(q)
        if resolve_vars:
            resolve_question_inplace(q, seed_for_vars=shuffle_seed)
        prepare_alternativas_inplace(q, merge_correct=merge_correct, dedup=dedup, shuffle_seed=shuffle_seed)
        norm_qs.append(q)

    meta: Dict[str, Any] = {}
    if isinstance(data, dict):
        m = data.get("meta")
        if isinstance(m, dict):
            meta = m
    return {"questions": norm_qs, "meta": meta}

def load_quiz(
    source: Union[str, Path, bytes, Dict[str, Any], List[Any]],
    *,
    shuffle_seed: Optional[int] = None,
    resolve_vars: bool = True,
    merge_correct: bool = True,
    dedup: bool = True,
) -> Dict[str, Any]:
    """
    Fonte ÚNICA para carregar questionários já prontos para renderização.
    - Normaliza alternativas;K
    - (Opcional) resolve variáveis
    - Mescla correta, deduplica e embaralha (determinístico por questão)
    - Expõe correct_index
    Retorna sempre: {"questions":[...], "meta": {...}}
    """
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists():
            if p.is_file():
                if p.suffix.lower()==".zip":
                    merged={"questions": [], "meta": {}}
                    for ds in _read_zip(p):
                        nd=_normalize_dataset(ds, shuffle_seed=shuffle_seed, resolve_vars=resolve_vars, merge_correct=merge_correct, dedup=dedup)
                        merged["questions"].extend(nd["questions"])
                        merged["meta"].update(nd["meta"] or {})
                    return merged
                else:
                    ds=_read_json_file(p)
                    return _normalize_dataset(ds, shuffle_seed=shuffle_seed, resolve_vars=resolve_vars, merge_correct=merge_correct, dedup=dedup)
            else:
                files=sorted(p.glob("*.json"))
                if not files:
                    raise QuizLoadError(f"Nenhum .json no diretório '{p}'")
                merged={"questions": [], "meta": {}}
                for fp in files:
                    nd=_normalize_dataset(_read_json_file(fp), shuffle_seed=shuffle_seed, resolve_vars=resolve_vars, merge_correct=merge_correct, dedup=dedup)
                    merged["questions"].extend(nd["questions"])
                    merged["meta"].update(nd["meta"] or {})
                return merged
        # se não existe como path, tentar string JSON
        data=_coerce_to_data(str(source))
        return _normalize_dataset(data, shuffle_seed=shuffle_seed, resolve_vars=resolve_vars, merge_correct=merge_correct, dedup=dedup)
    # bytes / dict / list
    data=_coerce_to_data(source)
    return _normalize_dataset(data, shuffle_seed=shuffle_seed, resolve_vars=resolve_vars, merge_correct=merge_correct, dedup=dedup)

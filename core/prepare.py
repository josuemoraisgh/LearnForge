
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional, Union
import logging, hashlib, random

logger = logging.getLogger(__name__)

ALT_KEY = "alternativas"
ALT_FIRSTROW_KEY = "alternativas_firstrow"
CORR_KEY = "correta"
CORR_INDEX_KEY = "correct_index"

# ---------- base normalization ----------

def _extract_k_from_key(key: str) -> Optional[int]:
    if isinstance(key, str) and key.startswith("alternativas;"):
        try:
            return int(key.split(";",1)[1].strip())
        except Exception:
            return None
    return None

def normalize_alternativas_inplace(q: Dict[str, Any]) -> None:
    if not isinstance(q, dict):
        return
    altk: List[Tuple[str,int,Any]] = []
    for k,v in list(q.items()):
        kval = _extract_k_from_key(k)
        if kval is not None:
            altk.append((k,kval,v))
    alts = q.get(ALT_KEY, None)
    if alts is None:
        chosen=None; ksave=None
        for k,kval,val in altk:
            if isinstance(val, list):
                chosen=val; ksave=kval; break
        q[ALT_KEY] = list(chosen) if isinstance(chosen, list) else []
        if ksave is not None:
            q[ALT_FIRSTROW_KEY] = int(ksave)
    elif not isinstance(alts, list):
        logger.warning("Campo '%s' não-lista (%s) -> []", ALT_KEY, type(alts).__name__)
        q[ALT_KEY] = []
    if ALT_FIRSTROW_KEY not in q:
        for _,kval,val in altk:
            if isinstance(val, list):
                q[ALT_FIRSTROW_KEY] = int(kval); break
    for k,_,_ in altk:
        q.pop(k, None)

# ---------- variables resolution ----------

def resolve_question_inplace(q: Dict[str, Any], *, seed_for_vars: Optional[int]=None) -> None:
    """
    Centraliza a resolução de variáveis chamando core.variables.resolve_all.
    A assinatura local não expõe envs extras enquanto o projeto não suportar.
    """
    from core.variables import resolve_all
    res = resolve_all(q, seed=seed_for_vars)
    q_res = res[0] if isinstance(res, tuple) else res
    q.clear()
    q.update(q_res)

# ---------- answers: merge + dedup + shuffle ----------

def _dedup_preserving_first(items: List[Any]) -> List[Any]:
    seen=set(); out=[]
    for a in items:
        key=a.strip() if isinstance(a,str) else a
        if key in seen: 
            continue
        seen.add(key)
        out.append(a)
    return out

def _rng_for_question(seed: int, q: Dict[str, Any]) -> random.Random:
    base=str(seed)
    salt=f"{q.get('id','')}|{q.get('enunciado','')}|{len(q.get(ALT_KEY,[]) or [])}"
    h=hashlib.sha256((base+'|'+salt).encode('utf-8')).hexdigest()
    return random.Random(int(h[:16],16))

def prepare_alternativas_inplace(
    q: Dict[str, Any],
    *,
    merge_correct: bool=True,
    dedup: bool=True,
    shuffle_seed: Optional[int]=None,
) -> None:
    if not isinstance(q, dict):
        return
    alts = q.get(ALT_KEY) or []
    if not isinstance(alts, list):
        alts = []
    cor = q.get(CORR_KEY, None)

    merged = list(alts)
    if merge_correct and cor not in (None,""):
        merged.append(cor)
    if dedup:
        merged = _dedup_preserving_first(merged)

    correct_idx = None
    if cor not in (None,"") and isinstance(merged, list):
        try:
            correct_idx = merged.index(cor)
        except ValueError:
            if isinstance(cor,str):
                cs=cor.strip()
                for i,a in enumerate(merged):
                    if isinstance(a,str) and a.strip()==cs:
                        correct_idx=i; break

    if shuffle_seed is not None and len(merged)>1:
        rng=_rng_for_question(shuffle_seed, q)
        idxs=list(range(len(merged)))
        rng.shuffle(idxs)
        merged_shuf=[merged[i] for i in idxs]
        if correct_idx is not None:
            correct_idx = idxs.index(correct_idx)
        merged = merged_shuf

    q[ALT_KEY]=merged
    if correct_idx is not None:
        q[CORR_INDEX_KEY]=int(correct_idx)
    else:
        q.pop(CORR_INDEX_KEY, None)

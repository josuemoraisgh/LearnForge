# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union
import json
import zipfile
import logging
import random
import hashlib

# --------------------------------------------------------------------
# Configuração de log
# --------------------------------------------------------------------
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Constantes de chaves
# --------------------------------------------------------------------
ALT_KEY = "alternativas"
ALT_FIRSTROW_KEY = "alternativas_firstrow"
CORR_KEY = "correta"
CORR_INDEX_KEY = "correct_index"

# --------------------------------------------------------------------
# Exceção do Loader
# --------------------------------------------------------------------
class QuizLoadError(Exception):
    """Erro de leitura/normalização do questionário."""
    pass


# ====================================================================
# 1) Normalizações base (alternativas;K -> alternativas + alternativas_firstrow)
# ====================================================================

def _extract_k_from_key(key: str) -> Optional[int]:
    """Extrai K de uma chave 'alternativas;K'. Retorna None se não for nesse formato."""
    if isinstance(key, str) and key.startswith("alternativas;"):
        try:
            return int(key.split(";", 1)[1].strip())
        except Exception:
            return None
    return None


def _dedup_preserving_order(items: List[Any]) -> List[Any]:
    """
    Remove duplicatas preservando a primeira ocorrência (ordem estável).
    Para strings, compara pelo texto strip() como chave, mas preserva o valor original.
    """
    seen = set()
    out: List[Any] = []
    for a in items:
        key = a
        if isinstance(key, str):
            key = key.strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def normalize_alternativas_inplace(q: Dict[str, Any]) -> None:
    """
    Unifica variantes de 'alternativas':
      - Se existir 'alternativas;K', copia a lista para 'alternativas' (se não houver),
        e salva K em 'alternativas_firstrow'.
      - Garante que 'alternativas' seja sempre uma lista (ou []).
      - Remove todas as chaves 'alternativas;K'.
    """
    if not isinstance(q, dict):
        return

    # Captura candidatas 'alternativas;K'
    altk: List[Tuple[str, int, Any]] = []
    for k, v in list(q.items()):
        kval = _extract_k_from_key(k)
        if kval is not None:
            altk.append((k, kval, v))

    # Fonte de verdade para a lista
    alts = q.get(ALT_KEY, None)
    if alts is None:
        chosen = None
        ksave = None
        for key, kval, val in altk:
            if isinstance(val, list):
                chosen = val
                ksave = kval
                break
        q[ALT_KEY] = list(chosen) if isinstance(chosen, list) else []
        if ksave is not None:
            q[ALT_FIRSTROW_KEY] = int(ksave)
    elif not isinstance(alts, list):
        logger.warning("Campo '%s' não é lista (type=%s). Forçando [].", ALT_KEY, type(alts).__name__)
        q[ALT_KEY] = []

    # Se ainda não houve K, tenta derivar do primeiro alternativas;K válido
    if ALT_FIRSTROW_KEY not in q:
        for _, kval, val in altk:
            if isinstance(val, list):
                q[ALT_FIRSTROW_KEY] = int(kval)
                break

    # Remove chaves legadas
    for key, _, _ in altk:
        q.pop(key, None)


# ====================================================================
# 2) Resolução de variáveis (centralizada no core)
# ====================================================================

def resolve_question_inplace(
    q: Dict[str, Any],
    *,
    vars_env: Optional[Dict[str, Any]] = None,   # deixei no signature por compat, mas não uso aqui
    seed_for_vars: Optional[int] = None,
) -> None:
    """
    Resolve variáveis/expressões na questão usando core.variables.resolve_all.
    Sobrepõe os campos no próprio dict 'q'.

    Observação: esta versão chama resolve_all(q, seed=...) sem 'extra_env',
    pois a sua implementação não aceita esse parâmetro. Se precisar injetar
    variáveis externas, ajuste o próprio resolve_all do seu projeto para aceitar,
    ou defina a convenção de ler de alguma chave (ex.: q['_env']).
    """
    from core.variables import resolve_all  # import local para evitar acoplamento de import

    # resolve_all pode retornar só o objeto OU (obj, env). Tratamos os dois casos.
    res = resolve_all(q, seed=seed_for_vars)
    if isinstance(res, tuple) and len(res) >= 1:
        q_res = res[0]
    else:
        q_res = res

    # Sobrepõe sem trocar a referência original
    q.clear()
    q.update(q_res)

# ====================================================================
# 3) Merge da correta + dedup + shuffle determinístico (+ índice correto)
# ====================================================================

def _per_question_rng(seed: int, q: Dict[str, Any]) -> random.Random:
    """
    Gera um RNG determinístico por questão, a partir da seed global e de campos estáveis.
    Isso garante reprodutibilidade com a mesma seed entre execuções.
    """
    base = str(seed)
    salt = f"{q.get('id','')}|{q.get('enunciado','')}|{len(q.get(ALT_KEY, []) or [])}"
    h = hashlib.sha256((base + "|" + salt).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))  # usa 64 bits (16 hex)

def merge_correct_and_shuffle_inplace(
    q: Dict[str, Any],
    *,
    merge_correct: bool = True,
    dedup: bool = True,
    shuffle_seed: Optional[int] = None,
) -> None:
    """
    - Mescla 'correta' dentro de 'alternativas'
    - Deduplica preservando a primeira ocorrência
    - Embaralha (se seed fornecida) de forma determinística por questão
    - Define 'correct_index' de acordo com a lista final
    - Mantém 'correta' (valor) por compatibilidade
    """
    if not isinstance(q, dict):
        return

    alts = q.get(ALT_KEY) or []
    if not isinstance(alts, list):
        alts = []

    cor = q.get(CORR_KEY, None)

    # 1) Merge da correta
    merged = list(alts)
    if merge_correct and cor not in (None, ""):
        merged.append(cor)

    # 2) Deduplicação
    if dedup:
        merged = _dedup_preserving_order(merged)

    # 3) Índice da correta (por valor) antes do shuffle
    correct_idx: Optional[int] = None
    if cor not in (None, "") and isinstance(merged, list):
        try:
            correct_idx = merged.index(cor)
        except ValueError:
            if isinstance(cor, str):
                cor_s = cor.strip()
                for i, a in enumerate(merged):
                    if isinstance(a, str) and a.strip() == cor_s:
                        correct_idx = i
                        break

    # 4) Shuffle determinístico por questão
    if shuffle_seed is not None and len(merged) > 1:
        rng = _per_question_rng(shuffle_seed, q)
        idxs = list(range(len(merged)))
        rng.shuffle(idxs)
        merged_shuf = [merged[i] for i in idxs]
        if correct_idx is not None:
            correct_idx = idxs.index(correct_idx)
        merged = merged_shuf

    # 5) Persiste resultado
    q[ALT_KEY] = merged
    if correct_idx is not None:
        q[CORR_INDEX_KEY] = int(correct_idx)
    else:
        q.pop(CORR_INDEX_KEY, None)  # se não achou, remove índice


# ====================================================================
# 4) I/O (arquivos/diretórios/zip/string/dict) + dataset normalize
# ====================================================================

def _coerce_to_data(obj: Union[str, bytes, Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    """Converte string/bytes JSON em dict/list; retorna dict/list inalterado quando já for."""
    if isinstance(obj, (dict, list)):
        return obj
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
        out: List[Union[Dict[str, Any], List[Any]]] = []
        with zipfile.ZipFile(p, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".json"):
                    out.append(json.loads(z.read(name).decode("utf-8")))
        return out
    except zipfile.BadZipFile as e:
        raise QuizLoadError(f"Arquivo ZIP inválido '{p}': {e}") from e

def _ensure_questions(data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
    """
    Suporta:
      - array raiz: [ {...}, {...} ]
      - objeto com chaves comuns: { "questions"/"questoes"/"lista"/"itens": [...] }
    """
    if isinstance(data, list):
        return [q for q in data if isinstance(q, dict)]
    if isinstance(data, dict):
        for k in ("questions", "questoes", "lista", "itens"):
            v = data.get(k)
            if isinstance(v, list):
                return [q for q in v if isinstance(q, dict)]
    return []

def _normalize_dataset(
    data: Union[Dict[str, Any], List[Any]],
    *,
    shuffle_seed: Optional[int],
    merge_correct: bool,
    dedup: bool,
    resolve_vars: bool,
    vars_env: Optional[Dict[str, Any]],
    seed_for_vars: Optional[int],
) -> Dict[str, Any]:
    """Normaliza um dataset bruto (dict/list) em {'questions': [...], 'meta': {...}}."""
    qs = _ensure_questions(data)

    norm_questions: List[Dict[str, Any]] = []
    for i, q in enumerate(qs):
        if not isinstance(q, dict):
            continue

        # A) normalização de alternativas;K
        normalize_alternativas_inplace(q)

        # B) resolução de variáveis (centralizada no core)
        if resolve_vars:
            resolve_question_inplace(q, vars_env=vars_env, seed_for_vars=seed_for_vars)

        # C) merge correta + dedup + shuffle + correct_index
        merge_correct_and_shuffle_inplace(
            q,
            merge_correct=merge_correct,
            dedup=dedup,
            shuffle_seed=shuffle_seed
        )

        norm_questions.append(q)

    meta: Dict[str, Any] = {}
    if isinstance(data, dict):
        m = data.get("meta")
        if isinstance(m, dict):
            meta = m

    return {"questions": norm_questions, "meta": meta}


# ====================================================================
# 5) API pública
# ====================================================================

def load_quiz(
    source: Union[str, Path, bytes, Dict[str, Any], List[Any]],
    *,
    # Alternativas/correta:
    shuffle_seed: Optional[int] = None,
    merge_correct: bool = True,
    dedup: bool = True,
    # Variáveis:
    resolve_vars: bool = True,
    vars_env: Optional[Dict[str, Any]] = None,
    seed_for_vars: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Ponto ÚNICO de verdade para carregar e preparar o questionário.

    - Aceita: arquivo .json, diretório com .json, .zip com .json, string/bytes JSON, dict/list.
    - Normaliza 'alternativas;K' -> 'alternativas' + 'alternativas_firstrow'.
    - (Opcional) Resolve variáveis (core.variables.resolve_all).
    - Mescla 'correta' em 'alternativas', deduplica e embaralha (determinístico por questão quando 'shuffle_seed' é fornecido).
    - Expõe 'correct_index' (índice da correta) e mantém 'correta' (valor) por compatibilidade.

    Retorna SEMPRE: {"questions": [...], "meta": {...}}
    """
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists():
            if p.is_file():
                if p.suffix.lower() == ".zip":
                    merged = {"questions": [], "meta": {}}
                    for ds in _read_zip(p):
                        nd = _normalize_dataset(
                            ds,
                            shuffle_seed=shuffle_seed,
                            merge_correct=merge_correct,
                            dedup=dedup,
                            resolve_vars=resolve_vars,
                            vars_env=vars_env,
                            seed_for_vars=seed_for_vars,
                        )
                        merged["questions"].extend(nd["questions"])
                        merged["meta"].update(nd["meta"] or {})
                    return merged
                else:
                    ds = _read_json_file(p)
                    return _normalize_dataset(
                        ds,
                        shuffle_seed=shuffle_seed,
                        merge_correct=merge_correct,
                        dedup=dedup,
                        resolve_vars=resolve_vars,
                        vars_env=vars_env,
                        seed_for_vars=seed_for_vars,
                    )
            else:
                files = sorted(p.glob("*.json"))
                if not files:
                    raise QuizLoadError(f"Nenhum .json no diretório '{p}'")
                merged = {"questions": [], "meta": {}}
                for fp in files:
                    nd = _normalize_dataset(
                        _read_json_file(fp),
                        shuffle_seed=shuffle_seed,
                        merge_correct=merge_correct,
                        dedup=dedup,
                        resolve_vars=resolve_vars,
                        vars_env=vars_env,
                        seed_for_vars=seed_for_vars,
                    )
                    merged["questions"].extend(nd["questions"])
                    merged["meta"].update(nd["meta"] or {})
                return merged

        # Caminho não existe: tentar string JSON
        data = _coerce_to_data(str(source))
        return _normalize_dataset(
            data,
            shuffle_seed=shuffle_seed,
            merge_correct=merge_correct,
            dedup=dedup,
            resolve_vars=resolve_vars,
            vars_env=vars_env,
            seed_for_vars=seed_for_vars,
        )

    # bytes / dict / list
    data = _coerce_to_data(source)
    return _normalize_dataset(
        data,
        shuffle_seed=shuffle_seed,
        merge_correct=merge_correct,
        dedup=dedup,
        resolve_vars=resolve_vars,
        vars_env=vars_env,
        seed_for_vars=seed_for_vars,
    )
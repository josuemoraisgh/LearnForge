# core/loader.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import zipfile
import logging
import re
import hashlib
import random
from .math import resolve_all  # <— cálculo correto de variáveis/resoluções + substituições

logger = logging.getLogger(__name__)

# -----------------------------
# API pública
# -----------------------------

class QuizLoadError(Exception):
    """Erros de leitura/normalização do questionário."""
    pass

def load_quiz(
    source: Union[str, Path, bytes, Dict[str, Any], List[Any]],
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Lê e processa o questionário sem conhecer "tipos".
    Pipeline:
      1) Lê JSON bruto e obtém um dicionário canônico;
      2) Normaliza todas as chaves "NOME;VALOR" -> "NOME" e cria:
         - "NOME_firstrow" = VALOR
         - se formato "A x B" (ou "A X B"): também "NOME_secondrow" = B
      3) Resolve variáveis e resoluções com resolve_all() e substitui <...> em todos os textos;
      4) Prepara alternativas: merge correta, dedup, shuffle determinístico (por questão) e
         grava 'correta' como tupla (index, valor).

    Retorna sempre: {"questions":[...], "meta": {...}} (mesmo se o JSON original for array raiz).
    """
    raw = _read_any(source)

    # Canonicalizar: achar a lista de itens (questões) e o meta
    questions, meta = _split_questions_and_meta(raw)

    # 1) Normalizar chaves "NOME;VALOR" (e "A x B") em cada questão
    for q in questions:
        _normalize_semicolon_keys_inplace(q)

    # 2) Resolver variáveis/resoluções + substituir <...> com o core correto (variables.resolve_all)
    resolved_questions: List[Dict[str, Any]] = []
    for q in questions:
        try:
            q_res, _env = resolve_all(q, seed=seed)
        except Exception as e:
            # Se algo falhar, registre e siga com a questão original (sem travar o lote)
            logger.exception("Falha em resolve_all para questão id=%s: %s", q.get("id"), e)
            q_res = q
        resolved_questions.append(q_res)

    # 3) Preparar alternativas (merge 'correta', dedup, shuffle determinístico, correta como tupla)
    for q in resolved_questions:
        _prepare_alternativas_inplace(q, seed=seed)

    return {"questions": resolved_questions, "meta": meta}


# -----------------------------
# I/O e canonicização
# -----------------------------

def _read_any(source: Union[str, Path, bytes, Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    if isinstance(source, (dict, list)):
        return source
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists():
            if p.is_file():
                if p.suffix.lower() == ".zip":
                    # lê todos os .json do zip e concatena
                    datasets: List[Union[Dict[str, Any], List[Any]]] = _read_zip(p)
                    # se houver múltiplos, concatena "questions"
                    merged_qs: List[Dict[str, Any]] = []
                    merged_meta: Dict[str, Any] = {}
                    for ds in datasets:
                        qs, mm = _split_questions_and_meta(ds)
                        merged_qs.extend(qs)
                        merged_meta.update(mm or {})
                    return {"questions": merged_qs, "meta": merged_meta}
                else:
                    return _read_json_file(p)
            else:
                # diretório: ler todos .json e concatenar
                qs_all: List[Dict[str, Any]] = []
                meta_merged: Dict[str, Any] = {}
                files = sorted(p.glob("*.json"))
                if not files:
                    raise QuizLoadError(f"Nenhum .json no diretório '{p}'.")
                for fp in files:
                    data = _read_json_file(fp)
                    qs, mm = _split_questions_and_meta(data)
                    qs_all.extend(qs)
                    meta_merged.update(mm or {})
                return {"questions": qs_all, "meta": meta_merged}
        # não existe caminho: pode ser string JSON
        try:
            return json.loads(str(source))
        except Exception as e:
            raise QuizLoadError(f"Entrada não é caminho nem JSON: {e}") from e
    if isinstance(source, (bytes, bytearray)):
        try:
            return json.loads(source.decode("utf-8"))
        except Exception as e:
            raise QuizLoadError(f"bytes não são JSON válido: {e}") from e
    raise QuizLoadError(f"Tipo de origem não suportado: {type(source).__name__}")

def _read_json_file(p: Path) -> Union[Dict[str, Any], List[Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise QuizLoadError(f"Falha ao ler JSON '{p}': {e}") from e

def _read_zip(p: Path) -> List[Union[Dict[str, Any], List[Any]]]:
    try:
        out: List[Union[Dict[str, Any], List[Any]]] = []
        with zipfile.ZipFile(p, "r") as z:
            for name in z.namelist():
                if name.lower().endswith(".json"):
                    out.append(json.loads(z.read(name).decode("utf-8")))
        return out
    except zipfile.BadZipFile as e:
        raise QuizLoadError(f"ZIP inválido '{p}': {e}") from e

def _split_questions_and_meta(data: Union[Dict[str, Any], List[Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Não conhece 'tipos': só extrai a lista e o meta quando houver.
    - Se raiz for lista -> assume lista de questões
    - Se raiz for dict -> procura chaves {questions, questoes, itens, lista}
    """
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)], {}
    if isinstance(data, dict):
        for k in ("questions", "questoes", "itens", "lista"):
            v = data.get(k)
            if isinstance(v, list):
                meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
                return [x for x in v if isinstance(x, dict)], meta
        # fallback: não achou a chave — tenta coerção simples
        items = data.get("items") if isinstance(data.get("items"), list) else []
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        return [x for x in items if isinstance(x, dict)], meta
    return [], {}


# -----------------------------
# Passo 1: normalizar "NOME;VALOR" (e "A x B")
# -----------------------------

_SEMI_RE = re.compile(r"^(?P<base>[^;]+);(?P<val>.+)$")

def _normalize_semicolon_keys_inplace(obj: Any) -> None:
    """
    Para QUALQUER dict, transforma chaves 'nome;valor' em:
      - 'nome' -> conteúdo original daquela chave (se ainda não existir)
      - 'nome_firstrow'  -> primeiro valor (int/float quando possível)
      - 'nome_secondrow' -> segundo valor, quando o valor vier como 'A x B' (ou 'A X B')
    Aplica recursivamente em sub-dicts e listas.

    Exemplos:
      'alternativas;3'         -> 'alternativas' + 'alternativas_firstrow=3'
      'imagens;640x480'        -> 'imagens' + 'imagens_firstrow=640' + 'imagens_secondrow=480'
      'foo; 10 X 5 '           -> 'foo' + 'foo_firstrow=10' + 'foo_secondrow=5'
    """
    if isinstance(obj, dict):
        # normaliza recursivamente os valores primeiro
        for k in list(obj.keys()):
            _normalize_semicolon_keys_inplace(obj[k])

        # agora reescreve as chaves com ';'
        keys = list(obj.keys())
        for k in keys:
            m = _SEMI_RE.match(k)
            if not m:
                continue

            base = m.group("base").strip()
            raw_val = m.group("val").strip()

            # 1) garantir a chave base (não sobrescreve se já existir)
            if base not in obj:
                obj[base] = obj[k]

            # 2) quebrar VAL em 'A x B' se for o caso (aceita x ou X, com espaços opcionais)
            parts = re.split(r"\s*[xX]\s*", raw_val)
            if len(parts) >= 2 and parts[0] and parts[1]:
                first = _coerce_scalar(parts[0])
                second = _coerce_scalar(parts[1])

                key_first = f"{base}_firstrow"
                key_second = f"{base}_secondrow"

                if key_first not in obj:
                    obj[key_first] = first
                if key_second not in obj:
                    obj[key_second] = second
            else:
                # apenas um valor -> só firstrow
                key_first = f"{base}_firstrow"
                if key_first not in obj:
                    obj[key_first] = _coerce_scalar(raw_val)

            # 3) remover a chave antiga 'base;valor'
            obj.pop(k, None)

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _normalize_semicolon_keys_inplace(v)

def _coerce_scalar(s: str) -> Any:
    # tenta int, depois float; senão mantém string
    try:
        return int(s)
    except Exception:
        pass
    try:
        return float(s)
    except Exception:
        pass
    return s


# -----------------------------
# Passo 3: preparar alternativas
# -----------------------------

def _dedup_preserving_first(items: List[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for a in items:
        key = a.strip() if isinstance(a, str) else a
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out

def _rng_for_item(seed: int, item: Dict[str, Any]) -> random.Random:
    """
    RNG determinístico por item (questão) a partir da seed e conteúdo estável.
    """
    base = str(seed)
    salt = f"{item.get('id','')}|{item.get('enunciado','')}|{len(item.get('alternativas',[]) or [])}"
    h = hashlib.sha256((base + "|" + salt).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))  # 64 bits

def _prepare_alternativas_inplace(q: Dict[str, Any], *, seed: Optional[int]) -> None:
    """
    Concatena 'alternativas' + 'correta', dedup, embaralha determinístico (se seed),
    e salva:
      - 'alternativas' final
      - 'correta' = (index, valor)  (tupla)
    """
    if not isinstance(q, dict):
        return

    alts = q.get("alternativas") or []
    if not isinstance(alts, list):
        alts = []

    cor_val = q.get("correta", None)

    merged = list(alts)
    if cor_val not in (None, ""):
        merged.append(cor_val)

    merged = _dedup_preserving_first(merged)

    # índice da correta antes do shuffle
    idx = None
    if cor_val not in (None, ""):
        try:
            idx = merged.index(cor_val)
        except ValueError:
            if isinstance(cor_val, str):
                cs = cor_val.strip()
                for i, a in enumerate(merged):
                    if isinstance(a, str) and a.strip() == cs:
                        idx = i
                        break

    # shuffle determinístico por item
    if seed is not None and len(merged) > 1:
        rng = _rng_for_item(seed, q)
        order = list(range(len(merged)))
        rng.shuffle(order)
        merged_shuf = [merged[i] for i in order]
        if idx is not None:
            idx = order.index(idx)
        merged = merged_shuf

    # persistir novos valores
    q["alternativas"] = merged
    if idx is not None:
        q["correta"] = (int(idx), merged[idx])  # tupla (indice, valor)
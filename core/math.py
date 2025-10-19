# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Tuple
import ast, re, random

ANGLE_RE = re.compile(r"<([^<>]+)?>")

import re

_RANGE_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$"
)

def _parse_range_spec(spec_str: str) -> tuple[float, float, float]:
    """
    Aceita apenas 'min:step:max' (floats, com sinal opcional). Ex.: '1:0.5:3'
    Retorna (min_v, step, max_v) como floats, com validações.
    """
    m = _RANGE_RE.match(spec_str or "")
    if not m:
        raise ValueError("Variável deve estar no formato 'min:step:max' (ex.: '1:0.5:3').")
    min_v = float(m.group(1))
    step  = float(m.group(2))
    max_v = float(m.group(3))

    if step <= 0:
        raise ValueError("step deve ser > 0.")
    if max_v < min_v:
        raise ValueError("max deve ser >= min.")

    # (opcional) checagem de múltiplos — tolerância p/ float
    span = (max_v - min_v) / step
    if abs(round(span) - span) > 1e-9:
        # Não é múltiplo exato — pode causar discrepância de grade
        # Mantemos permissivo ou levanta erro; se quiser estrito, descomente:
        # raise ValueError("max - min deve ser múltiplo de step.")
        pass

    return min_v, step, max_v


def _is_int(x: float) -> bool:
    return abs(x - int(x)) < 1e-9

def _fmt(x: float) -> str:
    return str(int(x)) if _is_int(x) else f"{x:.2f}"

def choose_value(min_v: float, max_v: float, step: float, rng: random.Random) -> float:
    # intervalo fechado com múltiplos exatos de step
    n = round((max_v - min_v) / step)
    # protege de casos flutuantes
    values = [min_v + i * step for i in range(n + 1)]
    # normaliza arredondando ao grid do step
    values = [round(v / step) * step for v in values]
    return values[rng.randrange(0, len(values))]

ALLOWED = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load, ast.Name,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
    ast.Constant,  # py3.8+
    ast.Expr,
    ast.Pow, ast.Mod  # aceitos, mesmo que pouco usados
}

def _check_ast(node: ast.AST):
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            raise ValueError("Funções não permitidas nas expressões.")
        if type(n) not in ALLOWED:
            # Parênteses são apenas tokens, não nós. Outros nós não são permitidos.
            pass

def safe_eval(expr: str, env: Dict[str, float]) -> float:
    node = ast.parse(expr, mode="eval")
    _check_ast(node)
    code = compile(node, "<expr>", "eval")
    return float(eval(code, {"__builtins__": {}}, dict(env)))

def replace_angles(template: str, env: Dict[str, float]) -> str:
    def repl(m: re.Match) -> str:
        inner = (m.group(1) or "").strip()
        if not inner:
            return ""
        # variável pura
        if inner in env:
            val = env[inner]
            return _fmt(val)
        # expressão (pode ser VAR, ou operação usando VAR/RES)
        val = safe_eval(inner, env)
        return _fmt(val)
    return ANGLE_RE.sub(repl, template)

def resolve_all(question: Dict[str, Any], seed: int|None) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Gera valores para variáveis (intervalo fechado, múltiplos de step), avalia resoluções na ordem
    e substitui <...> em enunciado, alternativas, correta, obs e resoluções posteriores.
    Retorna (question_resolved, env_final)."""
    rng = random.Random(seed)
    q = json_clone(question)

    env: Dict[str, float] = {}
    # 1) variáveis
    vars_def = (q.get("variaveis") or {})
    for name, spec in vars_def.items():
        if not isinstance(spec, str):
            # Enforce estrito: apenas string "min:step:max"
            raise ValueError(f"Variável '{name}': use string no formato 'min:step:max'.")
        min_v, step, max_v = _parse_range_spec(spec)
        env[name] = choose_value(min_v, max_v, step, rng)

    # 2) resoluções (na ordem declarada)
    res_def = (q.get("resolucoes") or {})
    for key, expr in res_def.items():
        expr_r = replace_angles(str(expr), env)
        env[key] = safe_eval(expr_r, env)

    # 3) substituição em todos os campos de texto
    def sub(x):
        if isinstance(x, str): return replace_angles(x, env)
        if isinstance(x, list): return [sub(i) for i in x]
        if isinstance(x, dict): return {k: sub(v) for k,v in x.items()}
        return x

    for field in ["enunciado","correta","obs"]:
        if field in q and isinstance(q[field], str):
            q[field] = sub(q[field])
    if "alternativas" in q and isinstance(q["alternativas"], list):
        q["alternativas"] = [sub(a) for a in q["alternativas"]]
    if "afirmacoes" in q and isinstance(q["afirmacoes"], dict):
        q["afirmacoes"] = {k: sub(v) for k,v in q["afirmacoes"].items()}
    if "resolucoes" in q and isinstance(q["resolucoes"], dict):
        q["resolucoes"] = {k: sub(v) for k,v in q["resolucoes"].items()}

    # Apply substitution to obs (list or string)
    if "obs" in q:
        if isinstance(q["obs"], list):
            q["obs"] = [sub(o) if isinstance(o, str) else o for o in q["obs"]]
        elif isinstance(q["obs"], str):
            q["obs"] = sub(q["obs"]) 

    return q, env

def json_clone(x):  # simples cópia profunda via JSON
    import json
    return json.loads(json.dumps(x))
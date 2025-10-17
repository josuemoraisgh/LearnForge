# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
import re

def _parse_img_spec(s: str):
    """Parse 'path;LxA' -> (path, L, A) em mm; ou (path, None, None) se não houver tamanho."""
    if not isinstance(s, str):
        return s, None, None
    if ';' in s:
        path, size = s.split(';',1)
        m = re.match(r'^\s*(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*$', size.strip())
        if m:
            return path.strip(), float(m.group(1)), float(m.group(2))
        return path.strip(), None, None
    return s.strip(), None, None

def preview_text(questions: List[Dict[str, Any]], title: str|None=None, **kwargs) -> str:
    """
    Preview unificado:
    - Ordena por id
    - Tipo 3: resolve <VAR>, <RES>, expressões
    - Tipo 4: linha "I. ...; II. ...; ..."
    - Alternativas a), b), c)...
    - Para imagens, mostra marcador: [imagem: caminho LxAmm]
    """
    from core.variables import resolve_all
    seed = kwargs.get("seed", None)
    alph = "abcdefghijklmnopqrstuvwxyz"
    lines: List[str] = []

    qs = sorted(questions or [], key=lambda q: int(q.get("id", 0)))
    for q in qs:
        q_res, _ = resolve_all(q, seed=seed)

        # Título
        lines.append(f"{q_res.get('id','?')}) {q_res.get('enunciado','').strip()}")

        # IMAGENS do enunciado (campo "imagens")
        imgs = q_res.get("imagens") or []
        for img in imgs:
            p, w, h = _parse_img_spec(str(img))
            size = f" {int(w)}x{int(h)}mm" if (w and h) else ""
            lines.append(f"   [imagem: {p}{size}]")

        # Tipo 4 (afirmativas) — linha única
        afirm = q_res.get("afirmacoes") or {}
        if isinstance(afirm, dict) and afirm:
            order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
            labeled = [f"{k}. {afirm[k]}" for k in order if k in afirm]
            if labeled:
                lines.append("   " + "; ".join(labeled))

        # Alternativas
        alts = q_res.get("alternativas") or []
        for i, alt in enumerate(alts):
            label = alph[i] + ")" if i < len(alph) else f"{i+1})"
            s = str(alt or "")
            p, w, h = _parse_img_spec(s)
            if isinstance(p, str) and p.lower().endswith((".png",".jpg",".jpeg",".gif",".bmp",".svg",".pdf")):
                size = f" {int(w)}x{int(h)}mm" if (w and h) else ""
                s_view = f"[imagem: {p}{size}]"
            else:
                s_view = s
            lines.append(f"   {label} {s_view}")

        lines.append("")  # separador

    return "\n".join(lines)
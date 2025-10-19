# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import re

def _parse_img_spec(s: str) -> Tuple[str, Optional[float], Optional[float]]:
    """Parse 'path;LxA' -> (path, L, A) em mm; ou (path, None, None) se não houver tamanho."""
    if not isinstance(s, str):
        return s, None, None
    if ';' in s:
        path, size = s.split(';', 1)
        m = re.match(r'^\s*(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*$', size.strip())
        if m:
            return path.strip(), float(m.group(1)), float(m.group(2))
        return path.strip(), None, None
    return s.strip(), None, None

def preview_text(questions: List[Dict[str, Any]], title: str | None = None, **kwargs) -> str:
    """
    Preview unificado (consumidor BURRO do core):
    - NÃO resolve variáveis localmente (isso é do core).
    - Ordena por id para leitura.
    - Exibe enunciado, imagens (como marcador), afirmações (se houver), subenunciado (se houver) e alternativas.
    - Alternativas são as já preparadas pelo core (com correta mesclada, deduplicada e embaralhada).
    """
    alph = "abcdefghijklmnopqrstuvwxyz"
    lines: List[str] = []

    # Ordena somente para leitura previsível
    qs = sorted(questions or [], key=lambda q: int(q.get("id", 0)))

    # Cabeçalho (opcional)
    if title:
        lines.append(title.strip())
        lines.append("=" * max(4, len(title.strip())))
        lines.append("")

    for q in qs:
        # Título da questão
        enun = (q.get("enunciado") or "").strip()
        lines.append(f"{q.get('id','?')}) {enun}")

        # IMAGENS (marcador textual)
        imgs = q.get("imagens") or []
        if isinstance(imgs, list):
            for img in imgs:
                p, w, h = _parse_img_spec(str(img))
                size = f" {int(w)}x{int(h)}mm" if (w and h) else ""
                lines.append(f"   [imagem: {p}{size}]")

        # AFIRMAÇÕES (se existirem)
        afirm = q.get("afirmacoes") or {}
        if isinstance(afirm, dict) and afirm:
            order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
            for k in order:
                if k in afirm:
                    lines.append(f"   {k}. {str(afirm[k]).strip()}")

            # SUBENUNCIADO (se houver, independente de 'tipo')
            sub = (q.get("subenunciado") or "").strip()
            if sub:
                lines.append(f"   {sub}")

        # ALTERNATIVAS (já preparadas pelo core)
        alts = q.get("alternativas") or []
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

        lines.append("")  # separador entre questões

    return "\n".join(lines)
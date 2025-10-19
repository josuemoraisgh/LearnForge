# -*- coding: utf-8 -*-
"""
Renderização "raw" (texto) do JSON da **questão atual** para exibição na aba "Raw" do editor.

Exponha apenas a função `format_question_json(q: dict) -> str`.
- Mantém a ordem das chaves conforme o dicionário recebido (Python 3.7+ preserva ordem de inserção).
- Usa indentação e acentos preservados (ensure_ascii=False, indent=2).
- Converte objetos não-serializáveis via `default=str` (garantindo que sempre renderize algo útil).
"""
from __future__ import annotations
import json
from typing import Any, Dict


def format_question_json(q: Dict[str, Any]) -> str:
    """Retorna uma string JSON bonita da questão atual.

    Parameters
    ----------
    q : dict
        Estrutura da questão atual (já normalizada pelo editor).

    Returns
    -------
    str
        JSON formatado com indentação de 2 espaços e acentos preservados.
    """
    try:
        return json.dumps(q, ensure_ascii=False, indent=2, default=str) + "\n"
    except Exception:
        # fallback conservador: tenta serializar chaves/valores como str
        q2 = {str(k): (v if isinstance(v, (str, int, float, bool, type(None))) else str(v)) for k, v in q.items()}
        return json.dumps(q2, ensure_ascii=False, indent=2) + "\n"

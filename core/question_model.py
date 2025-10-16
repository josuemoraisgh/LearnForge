
# -*- coding: utf-8 -*-
"""
Modelo e utilidades de questão.
"""
from typing import Dict, Any, List

def default_question(next_id: int = 1) -> Dict[str, Any]:
    return {
        'id': next_id,
        'tipo': 1,
        'dificuldade': 'média',
        'enunciado': '',
        'imagens': [],
        'alternativas': [],
        'correta': '',
        'obs': []
    }

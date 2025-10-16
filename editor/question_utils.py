
# -*- coding: utf-8 -*-
"""
Utilidades para o editor: normalização de campos e detecção de tipo.
"""
def ensure_lists(item):
    item.setdefault('imagens', [])
    item.setdefault('alternativas', [])
    item.setdefault('correta', '')
    item.setdefault('obs', [])

from core.models import Question

def tipo_of(q:dict)->int:
    return int(Question.infer_tipo(q))

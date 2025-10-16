
# -*- coding: utf-8 -*-
"""
Utilidades para o editor: normalização de campos e detecção de tipo.
"""
def ensure_lists(item):
    item.setdefault('imagens', [])
    item.setdefault('alternativas', [])
    item.setdefault('correta', '')
    item.setdefault('obs', [])

def tipo_of(q:dict)->int:
    t=q.get('tipo',None)
    if isinstance(t,int) and t in (1,2,3,4): return t
    if 'variaveis' in q or 'resolucoes' in q: return 3
    if 'afirmacoes' in q: return 4
    alts=q.get('alternativas') or []
    if any(isinstance(a,str) and a.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp','.svg')) for a in alts): return 2
    return 1

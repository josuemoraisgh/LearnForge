
import json
from core.models import RenderOptions
from core.pipeline import render_all

def test_demo():
    raw = [
        {"id":1,"enunciado":"Qual?","alternativas":["A","B","C","D"],"correta":"B"},
        {"id":2,"enunciado":"Escolha a imagem","alternativas":["a.png","b.png","Nenhuma"],"correta":"a.png"},
        {"id":3,"enunciado":"Valor <TEMP>","variaveis":{"X":{"min":1,"max":1,"step":1},"Y":{"min":2,"max":2,"step":1}},"resolucoes":{"TEMP":"X+Y"},"alternativas":["<TEMP+1>","<TEMP*2>"],"correta":"<TEMP>"},
        {"id":4,"enunciado":"Analise:","afirmacoes":{"I":"uma","II":"duas","III":"tres"},"alternativas":["Apenas I e II","Apenas I e III"],"correta":"Apenas I e III"}
    ]
    out = render_all(raw, RenderOptions(target="preview", shuffle_questions=False, shuffle_alternatives=False, seed=42))
    assert len(out)==4
    assert out[1].tipo.value==2
    assert "afirmacoes_labeled" in out[-1].extra

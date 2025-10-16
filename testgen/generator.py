
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import json, random

from docx import Document
from docx.shared import Inches

def _read_text_any(p: Path) -> str:
    b = p.read_bytes()
    for enc in ("utf-8","utf-8-sig","cp1252","latin1"):
        try: return b.decode(enc)
        except Exception: pass
    return b.decode("utf-8", errors="replace")

def _load_json_list(p: str) -> List[Dict[str, Any]]:
    text = _read_text_any(Path(p))
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{p}: o JSON deve ser um array de questões.")
    # base_dir relativo ao JSON para imagens
    base = str(Path(p).parent.resolve())
    for q in data:
        q.setdefault("_base_dir", base)
    return data

def _alts_with_correct(q: Dict[str, Any]) -> List[str]:
    alts = list(q.get("alternativas") or [])
    cor = (q.get("correta") or "").strip()
    if cor and not any((a or "").strip() == cor for a in alts):
        alts.append(cor)
    # dedup preservando ordem
    seen = set(); out = []
    for a in alts:
        key = (a or "").strip()
        if key in seen: continue
        seen.add(key); out.append(a)
    return out

def _compose_docx_block(q: Dict[str, Any], seq: int) -> List[Dict[str, Any]]:
    """Retorna uma sequência de runs p/ inserir na prova, com numeração sequencial (1..N)."""
    runs = []
    runs.append({"type":"text","text": f"{seq}) {q['enunciado']}\n"})
    # Afirmativas (linha única)
    extra = q.get("extra") or {}
    line = extra.get("afirmacoes_line","")
    if not line and isinstance(q.get("afirmacoes"), dict):
        # fallback simples
        order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
        labeled = [f"{k}. {q['afirmacoes'][k]}" for k in order if k in q["afirmacoes"]]
        line = "; ".join(labeled)
    if line:
        runs.append({"type":"text","text": "  " + line + "\n"})
    # Alternativas (a), b)...)
    alph = "abcdefghijklmnopqrstuvwxyz"
    from pathlib import Path as _P
    base_dir = q.get("_base_dir")
    for i, alt in enumerate(q.get("alternativas") or []):
        label = alph[i] + ")" if i < len(alph) else f"{i+1})"
        s = str(alt)
        # imagem?
        if s.lower().endswith((".png",".jpg",".jpeg",".gif",".bmp",".svg",".pdf")):
            p = _P(base_dir, s) if base_dir else _P(s)
            runs.append({"type":"text","text": f"  {label} "})
            if p.exists():
                runs.append({"type":"image","path": str(p)})
            else:
                runs.append({"type":"image","path": "assets/placeholder.png"})
            runs.append({"type":"text","text": "\n"})
        else:
            runs.append({"type":"text","text": f"  {label} {s}\n"})
    runs.append({"type":"text","text": "\n"})
    return runs

def _render_blocks_for_docx(resolved: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    return [_compose_docx_block(q, i+1) for i, q in enumerate(resolved)]

def json2docx(
    json_paths: List[str],
    template: str,
    out_docx: str,
    placeholder: str = "{{QUESTOES}}",
    title: str = "Prova",
    num: Optional[int] = None,
    seed: Optional[int] = None,
    shuffle: bool = True,
) -> int:
    # carregar questões e marcar base_dir relativo ao JSON
    raw: List[Dict[str, Any]] = []
    for p in json_paths:
        raw.extend(_load_json_list(p))

    rng = random.Random(seed)
    # embaralhar questões (apenas na prova)
    if shuffle:
        rng.shuffle(raw)
    if isinstance(num, int) and num>0:
        raw = raw[:num]

    # embaralhar alternativas e inserir correta
    for q in raw:
        alts = _alts_with_correct(q)
        rng.shuffle(alts)
        q["alternativas"] = alts

    # montar documento
    doc = Document(template)

    def replace_placeholder(document, placeholder_text, blocks):
        for para in document.paragraphs:
            if placeholder_text in para.text:
                p = para._p
                parent = p.getparent()
                idx = parent.index(p)
                parent.remove(p)
                # inserir após o removido
                for block in blocks:
                    pr = document.add_paragraph()
                    for run in block:
                        if run["type"] == "text":
                            pr.add_run(run["text"])
                        elif run["type"] == "image":
                            try:
                                pr.add_run().add_picture(run["path"], width=Inches(5.5))
                            except Exception:
                                pr.add_run("[imagem]")
                return True
        return False

    blocks = _render_blocks_for_docx(raw)
    if not replace_placeholder(doc, placeholder, blocks):
        # append no final
        for block in blocks:
            pr = doc.add_paragraph()
            for run in block:
                if run["type"] == "text":
                    pr.add_run(run["text"])
                elif run["type"] == "image":
                    try:
                        pr.add_run().add_picture(run["path"], width=Inches(5.5))
                    except Exception:
                        pr.add_run("[imagem]")

    Path(out_docx).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_docx)
    return 0

# Backward compat para seu GUI
def jsons_to_docx(json_paths, template, out_docx, placeholder='{{QUESTOES}}', title='Prova', num=None, seed=None, shuffle=True):
    return json2docx(json_paths, template, out_docx, placeholder=placeholder, title=title, num=num, seed=seed, shuffle=shuffle)

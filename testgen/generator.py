# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json, random
from core.variables import resolve_all  # <-- necessário para q_res, _env = resolve_all(...)
from docx import Document
from docx.shared import Inches

def mm_to_inches(mm: float) -> float:
    return (mm or 0) / 25.4

IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".pdf")

def _parse_img_spec(s: str):
    """Parse 'path;LxA' -> (path, L, A) em mm; (path, None, None) se sem tamanho."""
    if not isinstance(s, str):
        return s, None, None
    if ';' in s:
        path, size = s.split(';',1)
        import re
        m = re.match(r'^\s*(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*$', size.strip())
        if m:
            return path.strip(), float(m.group(1)), float(m.group(2))
        return path.strip(), None, None
    return s.strip(), None, None

def _is_image_path(s: str) -> bool:
    if not isinstance(s, str):
        return False
    p = s.split(';',1)[0].strip()
    return any(p.lower().endswith(ext) for ext in IMG_EXTS)

def _read_text_any(p: Path) -> str:
    b = p.read_bytes()
    for enc in ("utf-8","utf-8-sig","cp1252","latin1"):
        try: return b.decode(enc)
        except Exception: pass
    return b.decode("utf-8", errors="replace")

def _load_json_list(p: str) -> List[Dict[str, Any]]:
    """Carrega lista de questões e anota _base_dir relativo ao JSON, para resolver caminhos de imagem."""
    text = _read_text_any(Path(p))
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{p}: o JSON deve ser um array de questões.")
    base = str(Path(p).parent.resolve())
    for q in data:
        q.setdefault("_base_dir", base)
    return data

def _alts_with_correct(q: Dict[str, Any]) -> List[str]:
    """Garante a presença da correta e remove duplicatas preservando a ordem."""
    alts = list(q.get("alternativas") or [])
    cor = (q.get("correta") or "").strip()
    if cor and not any((a or "").strip() == cor for a in alts):
        alts.append(cor)
    seen, out = set(), []
    for a in alts:
        key = (a or "").strip()
        if key in seen: 
            continue
        seen.add(key)
        out.append(a)
    return out

def _afirm_line(q: Dict[str, Any]) -> str:
    """Monta 'I. ...; II. ...; ...' para Tipo 4 (sem embaralhar)."""
    afirm = q.get("afirmacoes") or {}
    if not isinstance(afirm, dict) or not afirm:
        return ""
    order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
    labeled = [f"{k}. {afirm[k]}" for k in order if k in afirm]
    return "; ".join(labeled)

def _compose_docx_block(q: Dict[str, Any], seq: int) -> List[Dict[str, Any]]:
    """
    Transforma a questão resolvida em uma sequência de 'runs' para docx.
    - Numeração sequencial (1..N) na Prova.
    - Alternativas rotuladas a), b), c)...
    - Tipo 2: insere imagem; se faltar, usa placeholder.
    """
    runs: List[Dict[str, Any]] = []
    alph = "abcdefghijklmnopqrstuvwxyz"
    base_dir = q.get("_base_dir") or q.get("__json_dir") or ""
    placeholder = "assets/placeholder.png"

    # 1) Enunciado
    runs.append({"type":"text","text": f"{seq}) {q['enunciado']}\n"})
    
    # 2) Imagens do enunciado (AGORA entre enunciado e alternativas)
    imgs = q.get("imagens") or []
    for img in imgs:
        spec_p, wmm, hmm = _parse_img_spec(img)
        p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
        if p.exists():
            runs.append({"type":"image","path": str(p), "width_mm": wmm, "height_mm": hmm})
        else:
            # se preferir, deixe um marcador textual
            runs.append({"type":"text","text": "[imagem]\n"})
    if imgs:
        runs.append({"type":"text","text": "\n"})  # respiro antes das alternativas
        
    # 3) (Opcional) Linha de afirmativas do Tipo 4
    afirm = q.get("afirmacoes") or {}
    if isinstance(afirm, dict) and afirm:
        order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
        for k in order:
            if k in afirm:
                runs.append({"type":"text","text": f"  {k}. {afirm[k]}\n"})
                
    # SUBENUNCIADO (Tipo 4) — entre afirmações e alternativas
    if q.get("afirmacoes"):
        sub = (q.get("subenunciado") or "").strip()
        if sub:
            runs.append({"type":"text","text": f"  {sub}\n\n"})
        
    # 4) Alternativas
    alts = q.get("alternativas") or []
    for i, alt in enumerate(alts):
        label = alph[i] + ")" if i < len(alph) else f"{i+1})"
        s = str(alt or "")
        if _is_image_path(s):
            spec_p, wmm, hmm = _parse_img_spec(s)
            p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
            runs.append({"type":"text","text": f"  {label} "})
            if p.exists():
                runs.append({"type":"image","path": str(p), "width_mm": wmm, "height_mm": hmm})
            else:
                runs.append({"type":"text","text": "[imagem]\n"})
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
    """
    Gera a prova DOCX:
    - Resolve Tipo 3 com seed (bate com Preview/Beamer).
    - Embaralha questões (se 'shuffle=True'), mas numera 1..N.
    - Embaralha alternativas e garante a correta presente.
    - Tipo 2 com imagens (caminho relativo ao JSON) e placeholder quando não existir.
    """
    # 1) Carregar
    raw: List[Dict[str, Any]] = []
    for p in json_paths:
        raw.extend(_load_json_list(p))

    # 2) Resolver T3 (variáveis/resoluções e substituições <...>) mantendo _base_dir
    resolved: List[Dict[str, Any]] = []
    for q in raw:
        base = q.get("_base_dir")
        q_res, _env = resolve_all(q, seed=seed)
        q_res["_base_dir"] = base
        # Tipo 4: preparar linha de afirmativas para reuso (preview-like)
        line = _afirm_line(q_res)
        if line:
            q_res.setdefault("extra", {})["afirmacoes_line"] = line
        resolved.append(q_res)

    rng = random.Random(seed)

    # 3) Embaralhar questões (apenas na prova)
    if shuffle:
        rng.shuffle(resolved)

    # 4) Seleção (num)
    if isinstance(num, int) and num > 0:
        resolved = resolved[:num]

    # 5) Embaralhar alternativas por questão, garantindo correta presente
    for q in resolved:
        alts = _alts_with_correct(q)
        rng.shuffle(alts)
        q["alternativas"] = alts

    # 6) Renderizar no DOCX (substituição do placeholder)
    doc = Document(template)

    def replace_placeholder(document: Document, placeholder_text: str, blocks: List[List[Dict[str, Any]]]) -> bool:
        for para in document.paragraphs:
            if placeholder_text in para.text:
                p = para._p
                parent = p.getparent()
                idx = parent.index(p)
                parent.remove(p)
                # Inserir logo após o parágrafo removido
                for block in blocks:
                    pr = document.add_paragraph()
                    for run in block:
                        if run["type"] == "text":
                            pr.add_run(run["text"])
                        elif run["type"] == "image":
                            try:
                                wmm = run.get("width_mm"); hmm = run.get("height_mm")
                                if wmm and hmm:
                                    pr.add_run().add_picture(run["path"],
                                        width=Inches(mm_to_inches(wmm)),
                                        height=Inches(mm_to_inches(hmm)))
                                else:
                                    pr.add_run().add_picture(run["path"], width=Inches(5.5))
                            except Exception:
                                pr.add_run("[imagem]")
                return True
        return False

    blocks = _render_blocks_for_docx(resolved)
    if not replace_placeholder(doc, placeholder, blocks):
        # Se placeholder não encontrado, adiciona ao final
        for block in blocks:
            pr = doc.add_paragraph()
            for run in block:
                if run["type"] == "text":
                    pr.add_run(run["text"])
                elif run["type"] == "image":
                    try:
                        wmm = run.get("width_mm"); hmm = run.get("height_mm")
                        if wmm and hmm:
                            pr.add_run().add_picture(run["path"], width=Inches(mm_to_inches(wmm)), height=Inches(mm_to_inches(hmm)))
                        else:
                            pr.add_run().add_picture(run["path"], width=Inches(5.5))
                    except Exception:
                        pr.add_run("[imagem]")

    Path(out_docx).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_docx)
    return 0

# Backward compat para seu GUI
def jsons_to_docx(json_paths, template, out_docx, placeholder='{{QUESTOES}}', title='Prova', num=None, seed=None, shuffle=True):
    return json2docx(json_paths, template, out_docx, placeholder=placeholder, title=title, num=num, seed=seed, shuffle=shuffle)
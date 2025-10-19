# -*- coding: utf-8 -*-
"""
Geração de slides Beamer a partir de JSON de questões.

Regras:
- Ordena por id; título do frame: "<id>) <enunciado>".
- Dois frames por questão: (1) sem gabarito; (2) com gabarito.
- OBS. em frame adicional quando houver.
- Alternativas sempre a), b), c), ...
- Tipo 4: afirmativas uma por linha (itemize).
- Tipo 2: alternativas por imagem; se não existir arquivo, desenha quadro vazio.
- Caminhos de imagem relativos ao diretório do JSON.
- Suporte a imagens com "caminho;LxA" (mm) no enunciado e nas alternativas.
- Suporte a "alternativas;K" (K = colunas da 1ª linha).
- **NOVO**: a correta NÃO vem mais mesclada pelo core; aqui inserimos a correta
  em posição pseudo-aleatória determinística e destacamos no 2º slide:
  - texto: \alert{...}
  - imagem: borda vermelha (\fcolorbox{red}{white}{...})
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import hashlib
import random

from core.loader import load_quiz

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf')

def _rng_for_q(seed: Optional[int], q: Dict[str, Any]) -> random.Random:
    """
    RNG determinístico por questão (id + enunciado + tamanho atual de alternativas),
    para que o índice da correta seja reprodutível entre execuções.
    """
    base = str(0 if seed is None else seed)
    salt = f"{q.get('id','')}|{q.get('enunciado','')}|{len(q.get('alternativas') or [])}"
    h = hashlib.sha256((base + "|" + salt).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))  # 64 bits

# "caminho;LxA" (mm)
def _parse_img_spec(s: str):
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

def latex_escape(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = "".join(repl.get(ch, ch) for ch in s)
    # trata < e > (evita mojibake/inversões)
    out = out.replace("<", r"\textless{}").replace(">", r"\textgreater{}")
    return out

def _label(i: int) -> str:
    abc = "abcdefghijklmnopqrstuvwxyz"
    return abc[i] + ")" if i < len(abc) else f"{i+1})"

def _is_image_path(x: str) -> bool:
    p, _, _ = _parse_img_spec(x) if isinstance(x, str) else (x, None, None)
    return isinstance(p, str) and any(p.lower().endswith(ext) for ext in IMG_EXTS)

def render_images(imgs: List[str], base_dir: str | None = None) -> str:
    """
    Imagens do enunciado, centralizadas; se não houver arquivo, mostra quadro vazio 6x4 cm.
    """
    if not imgs:
        return ""
    lines = [r"\begin{center}"]
    for img in imgs:
        spec_p, wmm, hmm = _parse_img_spec(img)
        p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
        if p.exists():
            if wmm and hmm:
                lines.append(rf"\includegraphics[width={wmm}mm,height={hmm}mm]{{{p.as_posix()}}}")
            else:
                lines.append(rf"\includegraphics[width=0.9\linewidth]{{{p.as_posix()}}}")
        else:
            lines.append(r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{center}")
    return "\n".join(lines)

def render_afirmacoes_line(afirm: Dict[str, str]) -> str:
    """
    Tipo 4: afirmativas em múltiplas linhas (itemize). Ordem fixa I..X.
    """
    if not afirm:
        return ""
    order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
    itens = [f"{k}. {afirm[k]}" for k in order if k in afirm]
    if not itens:
        return ""
    safe = [latex_escape(x) for x in itens]
    return "\n".join([r"\begin{itemize}"] + [r"\item " + s for s in safe] + [r"\end{itemize}"])

def render_alts_text(alts: List[str], corretaIndex: int, highlight: bool = False) -> str:
    """
    Alternativas em texto, rotuladas a), b), c) ...; se highlight=True, \alert{correta}.
    """
    if not alts:
        return ""
    lines = [r"\begin{itemize}"]
    for i, alt in enumerate(alts):
        label = _label(i)
        content = latex_escape(alt or "")
        if highlight and corretaIndex == i:
            content = r"\alert{" + content + "}"
        lines.append(r"\item[" + label + "] " + content)
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

def render_alts_images(
    alts: List[str],
    base_dir: str | None = None,
    corretaIndex: int = -1,
    highlight_correct: bool = False,
) -> str:
    """
    Alternativas com imagens; rótulo a), b), c)…; se imagem não existir, quadro vazio.
    Quando highlight_correct=True, a alternativa correta (corretaIndex) recebe borda vermelha.

    Estratégia de destaque:
      - \fcolorbox{red}{white}{\includegraphics{...}}
      - Mantemos o rótulo normal (a), b), ...), só a figura recebe a borda.
    """
    if not alts:
        return ""
    lines = [r"\begin{itemize}"]
    for i, alt in enumerate(alts):
        label = _label(i)

        if _is_image_path(alt or ""):
            spec_p, wmm, hmm = _parse_img_spec(alt)
            p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
            if p.exists():
                if wmm and hmm:
                    img_cmd = rf"\includegraphics[width={wmm}mm,height={hmm}mm]{{{p.as_posix()}}}"
                else:
                    img_cmd = rf"\includegraphics[width=0.75\linewidth]{{{p.as_posix()}}}"

                # aplica borda vermelha na CORRETA quando highlight estiver ativo
                if highlight_correct and i == corretaIndex:
                    img_cmd = r"\fcolorbox{red}{white}{" + img_cmd + "}"

                lines.append(r"\item[" + label + "] " + img_cmd)
            else:
                # caixa vazia; se for a correta com highlight, usa borda vermelha
                empty_box = r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}"
                if highlight_correct and i == corretaIndex:
                    empty_box = r"\fcolorbox{red}{white}{" + empty_box + "}"
                lines.append(r"\item[" + label + "] " + empty_box)
        else:
            # não é caminho de imagem; mostra caixa vazia (ou poderia exibir texto escapado)
            empty_box = r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}"
            if highlight_correct and i == corretaIndex:
                empty_box = r"\fcolorbox{red}{white}{" + empty_box + "}"
            lines.append(r"\item[" + label + "] " + empty_box)

    lines.append(r"\end{itemize}")
    return "\n".join(lines)

def render_alts_grid_beamer_from_list(
    alts: List[str],
    corretaIndex: int,
    K: int | None,
    base_dir: str | None,
    highlight_correct: bool = False,
) -> str:
    """
    Renderiza 'alts' (lista final) em 2 linhas: 1ª com K colunas; 2ª com o restante.
    Mantém a ordem; rótulos a), b), c)...; se highlight_correct=True, aplica \alert
    APENAS no conteúdo textual da alternativa correta (nunca no label).
    Para imagens, a sinalização é feita na função render_alts_images (borda vermelha).
    """
    if not alts or not isinstance(K, int) or K <= 0 or K >= len(alts):
        return ""

    n = len(alts)
    first, rest = K, n - K
    labels = [_label(i) for i in range(n)]

    def _is_correct(index: int) -> bool:
        return (highlight_correct and corretaIndex == index)

    def _cell(i: int) -> str:
        a = alts[i]
        lab = labels[i]

        # Se for imagem ("path[;LxA]"), não aplicamos \alert aqui
        if _is_image_path(a or ""):
            spec_p, wmm, hmm = _parse_img_spec(a)
            p = Path(base_dir, spec_p) if base_dir else Path(spec_p)
            if p.exists():
                if wmm and hmm:
                    content = rf"\includegraphics[width={wmm}mm,height={hmm}mm]{{{p.as_posix()}}}"
                else:
                    content = rf"\includegraphics[width=0.9\linewidth]{{{p.as_posix()}}}"
            else:
                content = r"\fbox{\rule{0pt}{2.5cm}\rule{3.5cm}{0pt}}"
            # A borda vermelha para imagens é feita em render_alts_images (lista vertical),
            # aqui apenas exibimos a figura sem alert. Se desejar borda também no grid,
            # pode envolver 'content' em \fcolorbox na condição _is_correct(i).
            return r"\centering " + lab + " " + content

        # Texto: aplica \alert apenas no texto quando for a correta
        text = latex_escape(str(a))
        if _is_correct(i):
            text = r"\alert{" + text + "}"

        return r"\centering " + lab + " " + text

    parts: List[str] = []
    # Primeira linha (K colunas)
    parts.append(r"\begin{tabularx}{\linewidth}{" + ("C" * first) + r"}")
    parts.append(" & ".join(_cell(i) for i in range(0, first)) + r" \\")
    parts.append(r"\end{tabularx}")

    # Segunda linha (restante)
    if rest > 0:
        parts.append(r"\vspace{0.6em}")
        parts.append(r"\begin{tabularx}{\linewidth}{" + ("C" * rest) + r"}")
        parts.append(" & ".join(_cell(first + j) for j in range(0, rest)) + r" \\")
        parts.append(r"\end{tabularx}")

    return "\n".join(parts)

# --------------------------------------------------------------------
# Gerador principal
# --------------------------------------------------------------------
def json2beamer(
    input_json='assets/questoes_template.json',
    output_tex='assets/questoes_template_slides.tex',
    shuffle_seed=None,             # seed p/ core e para posicionar a correta aqui
    title='Exercícios – Apresentação',
    fsq='Large',
    fsa='normalsize',
    alert_color='red',             # \alert usa a cor do tema; mantido por compat
    **kwargs
) -> int:
    """
    Gera .tex Beamer conforme o padrão acordado.
    - A ordem das questões por id é mantida aqui (sem shuffle adicional no Beamer).
      OBS: o shuffle de alternativas já pode ter acontecido no CORE.
    - Caminhos de imagem relativos ao diretório do JSON.
    - A resolução de variáveis acontece no CORE.
    - **Novo fluxo**: a correta é inserida aqui, em posição determinística por questão, e
      só é destacada no segundo frame (texto = \alert; imagem = borda vermelha).
    """
    # Base dir para imagens (pega do primeiro JSON)
    if isinstance(input_json, (list, tuple)):
        base_dir = str(Path(input_json[0]).parent.resolve()) if input_json else None
        # Carrega e concatena todas as questões já normalizadas pelo CORE
        all_qs: List[Dict[str, Any]] = []
        for p in input_json:
            ds = load_quiz(p, shuffle_seed)
            all_qs.extend(ds.get("questions", []))
        qs = all_qs
    else:
        base_dir = str(Path(input_json).parent.resolve())
        ds = load_quiz(input_json, shuffle_seed)
        qs = ds.get("questions", [])

    # Ordenar por id (robusto)
    try:
        qs = sorted(qs, key=lambda q: int(q.get("id", 0)))
    except Exception:
        pass

    # PREÂMBULO com widescreen e Unicode
    preamble = (
        "\\documentclass[aspectratio=169]{beamer}\n"
        "\\usepackage{bookmark}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usetheme{Madrid}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{enumitem}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{lmodern}\n"
        "\\usepackage{textcomp}\n"
        "\\usepackage{upquote}\n"
        "\\usepackage{array}\n"
        "\\usepackage{tabularx}\n"
        "\\newcolumntype{C}{>{\\centering\\arraybackslash}X}\n"
        "\\usepackage{xcolor}\n"
        "\\usepackage{newunicodechar}\n"
        "\\DeclareUnicodeCharacter{03B1}{\\ensuremath{\\alpha}}\n"
        "\\DeclareUnicodeCharacter{03B2}{\\ensuremath{\\beta}}\n"
        "\\DeclareUnicodeCharacter{03B3}{\\ensuremath{\\gamma}}\n"
        "\\DeclareUnicodeCharacter{03B4}{\\ensuremath{\\delta}}\n"
        "\\DeclareUnicodeCharacter{03B5}{\\ensuremath{\\varepsilon}}\n"
        "\\DeclareUnicodeCharacter{03B8}{\\ensuremath{\\theta}}\n"
        "\\DeclareUnicodeCharacter{03BB}{\\ensuremath{\\lambda}}\n"
        "\\DeclareUnicodeCharacter{03BC}{\\ensuremath{\\mu}}\n"
        "\\DeclareUnicodeCharacter{03C0}{\\ensuremath{\\pi}}\n"
        "\\DeclareUnicodeCharacter{03C1}{\\ensuremath{\\rho}}\n"
        "\\DeclareUnicodeCharacter{03C3}{\\ensuremath{\\sigma}}\n"
        "\\DeclareUnicodeCharacter{03C6}{\\ensuremath{\\varphi}}\n"
        "\\DeclareUnicodeCharacter{03C9}{\\ensuremath{\\omega}}\n"
        "\\DeclareUnicodeCharacter{0394}{\\ensuremath{\\Delta}}\n"
        "\\DeclareUnicodeCharacter{03A9}{\\ensuremath{\\Omega}}\n"
        "\\DeclareUnicodeCharacter{00B0}{\\ensuremath{^{\\circ}}}\n"
        "\\DeclareUnicodeCharacter{00D7}{\\ensuremath{\\times}}\n"
        "\\DeclareUnicodeCharacter{2212}{-}\n"
        "\\DeclareUnicodeCharacter{00A0}{~}\n"
        "\\DeclareUnicodeCharacter{202F}{\\,}\n"
        "\\DeclareUnicodeCharacter{207B}{\\ensuremath{^{-}}}\n"
        "\\DeclareUnicodeCharacter{2070}{\\ensuremath{^{0}}}\n"
        "\\DeclareUnicodeCharacter{00B9}{\\ensuremath{^{1}}}\n"
        "\\DeclareUnicodeCharacter{00B2}{\\ensuremath{^{2}}}\n"
        "\\DeclareUnicodeCharacter{00B3}{\\ensuremath{^{3}}}\n"
        "\\DeclareUnicodeCharacter{2074}{\\ensuremath{^{4}}}\n"
        "\\DeclareUnicodeCharacter{2075}{\\ensuremath{^{5}}}\n"
        "\\DeclareUnicodeCharacter{2076}{\\ensuremath{^{6}}}\n"
        "\\DeclareUnicodeCharacter{2077}{\\ensuremath{^{7}}}\n"
        "\\DeclareUnicodeCharacter{2078}{\\ensuremath{^{8}}}\n"
        "\\DeclareUnicodeCharacter{2079}{\\ensuremath{^{9}}}\n"
        "\\DeclareUnicodeCharacter{2080}{\\ensuremath{_{0}}}\n"
        "\\DeclareUnicodeCharacter{2081}{\\ensuremath{_{1}}}\n"
        "\\DeclareUnicodeCharacter{2082}{\\ensuremath{_{2}}}\n"
        "\\DeclareUnicodeCharacter{2083}{\\ensuremath{_{3}}}\n"
        "\\DeclareUnicodeCharacter{2084}{\\ensuremath{_{4}}}\n"
        "\\DeclareUnicodeCharacter{2085}{\\ensuremath{_{5}}}\n"
        "\\DeclareUnicodeCharacter{2086}{\\ensuremath{_{6}}}\n"
        "\\DeclareUnicodeCharacter{2087}{\\ensuremath{_{7}}}\n"
        "\\DeclareUnicodeCharacter{2088}{\\ensuremath{_{8}}}\n"
        "\\DeclareUnicodeCharacter{2089}{\\ensuremath{_{9}}}\n"
        "\\title{" + latex_escape(title) + "}\n"
        "\\author{}\n"
        "\\date{}\n"
    )

    parts: List[str] = [
        preamble,
        "\\begin{document}\n",
        "\\frame{\\titlepage}\n",
        f"\\setbeamerfont{{frametitle}}{{size=\\{fsq}}}\n",
        f"\\newcommand{{\\BodySize}}{{\\{fsa}}}\n",
    ]

    for q_res in qs:
        qid = q_res.get("id", "?")
        enun = (q_res.get("enunciado", "") or "").strip()
        enun_tex = latex_escape(enun)
        tipo = int(q_res.get("tipo", 1))
        base_alts = q_res.get("alternativas", []) or []
        correta_val = q_res.get("correta", None)
        imgs = q_res.get("imagens") or []

        # --- Inserção da correta em posição determinística por questão (SEM procurar antes) ---
        alts: List[str] = list(base_alts)  # cópia
        correta_index = -1

        if correta_val is not None and correta_val != "":
            # posição determinística por questão
            rng = _rng_for_q(shuffle_seed, q_res)
            pos = rng.randrange(0, len(alts) + 1)

            # se já existe, remove a primeira ocorrência para controlarmos o índice de destaque
            try:
                # comparação robusta convertendo a str (cobre números, etc.)
                existing = next(i for i, a in enumerate(alts) if str(a) == str(correta_val))
                alts.pop(existing)
                if existing < pos:
                    pos -= 1  # ajuste se removemos antes da posição escolhida
            except StopIteration:
                pass

            # insere a correta
            alts.insert(pos, correta_val)
            correta_index = pos


        # ---------------- Frame 1: sem gabarito ----------------
        parts.append("\\begin{frame}")
        parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
        parts.append("{\\BodySize")

        if imgs:
            parts.append(render_images(imgs, base_dir=base_dir))

        if q_res.get("afirmacoes"):
            parts.append(render_afirmacoes_line(q_res["afirmacoes"]))
            sub = (q_res.get("subenunciado") or "").strip()
            if sub:
                parts.append(r"\medskip")
                parts.append("{\\BodySize " + latex_escape(sub) + r"\par}")
                parts.append(r"\medskip")

        if tipo == 2:
            # Imagens nas alternativas – sem destaque no 1º frame
            parts.append(
                render_alts_images(
                    alts, base_dir=base_dir,
                    corretaIndex=correta_index,
                    highlight_correct=False
                )
            )
        else:
            K = q_res.get('alternativas_firstrow')
            grid = render_alts_grid_beamer_from_list(
                alts=alts,
                corretaIndex=correta_index,
                K=K,
                base_dir=base_dir,
                highlight_correct=False
            )
            parts.append(grid if grid else render_alts_text(alts, correta_index, highlight=False))

        parts.append("}")
        parts.append("\\end{frame}\n")

        # ---------------- Frame 2: com gabarito ----------------
        parts.append("\\begin{frame}")
        parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
        parts.append("{\\BodySize")

        if imgs:
            parts.append(render_images(imgs, base_dir=base_dir))

        if q_res.get("afirmacoes"):
            parts.append(render_afirmacoes_line(q_res["afirmacoes"]))
            sub = (q_res.get("subenunciado") or "").strip()
            if sub:
                parts.append(r"\medskip")
                parts.append("{\\BodySize " + latex_escape(sub) + r"\par}")
                parts.append(r"\medskip")

        if tipo == 2:
            # Imagens nas alternativas – com borda vermelha na correta
            parts.append(
                render_alts_images(
                    alts, base_dir=base_dir,
                    corretaIndex=correta_index,
                    highlight_correct=True
                )
            )
        else:
            K = q_res.get('alternativas_firstrow')
            grid = render_alts_grid_beamer_from_list(
                alts=alts,
                corretaIndex=correta_index,
                K=K,
                base_dir=base_dir,
                highlight_correct=True
            )
            parts.append(grid if grid else render_alts_text(alts, correta_index, highlight=True))

        parts.append("}")
        parts.append("\\end{frame}\n")

        # ---------------- Frame 3: OBS (se houver) ----------------
        obs = q_res.get("obs")
        obs_items = []
        if isinstance(obs, str) and obs.strip():
            obs_items = [obs.strip()]
        elif isinstance(obs, (list, tuple)):
            obs_items = [str(x).strip() for x in obs if str(x).strip()]

        if obs_items:
            parts.append("\\begin{frame}")
            parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
            parts.append("{\\BodySize")
            parts.append("\\textbf{OBS.:}")
            parts.append("\\begin{itemize}")
            for it in obs_items:
                parts.append("\\item " + latex_escape(it))
            parts.append("\\end{itemize}")
            parts.append("}")
            parts.append("\\end{frame}\n")

    parts.append("\\end{document}\n")

    out = Path(output_tex)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return 0
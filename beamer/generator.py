# -*- coding: utf-8 -*-
"""
Geração de slides Beamer a partir de JSON de questões.

Padrões aplicados:
- Preâmbulo (beamer + Madrid) com widescreen e mapeamento Unicode.
- Ordena por id; título do frame: "<id>) <enunciado>".
- Dois frames por questão: (1) sem gabarito; (2) com gabarito (\alert{...}).
- OBS. em frame adicional quando houver.
- Alternativas sempre a), b), c), ...
- Tipo 4: afirmativas uma por linha (itemize).
- Tipo 2: alternativas por imagem; se não existir arquivo, desenha quadro vazio.
- Caminhos de imagem relativos ao diretório do JSON.
- Suporte a imagens com "caminho;LxA" (mm) no enunciado e nas alternativas.
- Suporte a "alternativas;K" (K = colunas da 1ª linha) — usando SEMPRE a lista final de
  alternativas em q_res["alternativas"] (merge + aleatoriedade feitos no pipeline).
"""

from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import json
import re

# resolvedor (Tipo 3: variáveis, resoluções e substituições <...>)
from core.variables import resolve_all

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf')

def _alternativas_firstrow(q: Dict[str, Any]) -> int | None:
    """
    Lê 'alternativas;K' (se existir) e retorna K; caso contrário None.
    Usado apenas como metadado de layout (nunca para pegar a lista).
    """
    for k in q.keys():
        if isinstance(k, str) and k.startswith("alternativas;"):
            try:
                return int(k.split(";", 1)[1])
            except Exception:
                return None
    return None

def _alts_final(q: Dict[str, Any]) -> List[str]:
    """
    Retorna a lista FINAL de alternativas (merge + aleatoriedade) do pipeline:
    - Prioriza q["alternativas"]
    - Se não existir, cai para a primeira 'alternativas;K'
    - Garante presença da 'correta' se por algum motivo ela não estiver
    """
    alts = None
    if isinstance(q.get("alternativas"), list):
        alts = list(q.get("alternativas") or [])
    if alts is None:
        for k, v in q.items():
            if isinstance(k, str) and k.startswith("alternativas;") and isinstance(v, list):
                alts = list(v or [])
                break
    if alts is None:
        alts = []
    cor = (q.get("correta") or "").strip()
    if cor and not any((a or "").strip() == cor for a in alts):
        alts.append(cor)
    # remove duplicatas preservando ordem
    seen, out = set(), []
    for a in alts:
        key = (a or "").strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out

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

def _read_text_any(p: Path) -> str:
    b = p.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")

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

def render_alts_text(alts: List[str], correta: str, highlight: bool = False) -> str:
    """
    Alternativas em texto, rotuladas a), b), c) ...; se highlight=True, \alert{correta}.
    """
    if not alts:
        return ""
    lines = [r"\begin{itemize}"]
    cor = (correta or "").strip()
    for i, alt in enumerate(alts):
        label = _label(i)
        content = latex_escape(alt or "")
        if highlight and (alt or "").strip() == cor:
            content = r"\alert{" + content + "}"
        lines.append(r"\item[" + label + "] " + content)
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

def render_alts_images(alts: List[str], base_dir: str | None = None) -> str:
    """
    Alternativas com imagens; rótulo a), b), c)…; se imagem não existir, quadro vazio.
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
                    lines.append(r"\item[" + label + "] " + rf"\includegraphics[width={wmm}mm,height={hmm}mm]{{{p.as_posix()}}}")
                else:
                    lines.append(r"\item[" + label + "] " + rf"\includegraphics[width=0.75\linewidth]{{{p.as_posix()}}}")
            else:
                lines.append(r"\item[" + label + "] " + r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
        else:
            lines.append(r"\item[" + label + "] " + r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

def render_alts_grid_beamer_from_list(
    alts: List[str],
    correta: str,
    K: int | None,
    base_dir: str | None,
    highlight_correct: bool = False,
) -> str:
    """
    Renderiza 'alts' (lista final) em 2 linhas: 1ª com K colunas; 2ª com o restante.
    Mantém a ordem; rótulos a), b), c)...; se highlight_correct=True, aplica \alert
    APENAS no conteúdo textual da alternativa correta (nunca no label).
    """
    if not alts or not isinstance(K, int) or K <= 0 or K >= len(alts):
        return ""

    n = len(alts)
    first, rest = K, n - K
    labels = [_label(i) for i in range(n)]
    cor = (str(correta) or "").strip()

    def _is_correct(a: str) -> bool:
        return highlight_correct and bool(cor) and (str(a).strip() == cor)

    def _cell(i: int) -> str:
        a = alts[i]
        lab = labels[i]

        # Se for imagem ("path[;LxA]"), não aplicamos \alert (apenas centralizamos)
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

            # label normal, conteúdo sem alert
            return r"\centering " + lab + " " + content

        # Texto: aplica \alert apenas no texto quando for a correta
        text = latex_escape(str(a))
        if _is_correct(a):
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

def _load_json_list(p: str) -> List[Dict[str, Any]]:
    text = _read_text_any(Path(p))
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{p}: o JSON deve ser um array de questões.")
    return data

def json2beamer(
    input_json='assets/questoes_template.json',
    output_tex='assets/questoes_template_slides.tex',
    shuffle_seed=None,             # seed do resolver T3 (não embaralhamos no Beamer)
    title='Exercícios – Apresentação',
    fsq='Large',
    fsa='normalsize',
    alert_color='red',             # compatibilidade; \alert usa cor do tema
    **kwargs
) -> int:
    """
    Gera .tex Beamer conforme o padrão acordado.
    - Ordem das questões por id (sem shuffle).
    - Caminhos de imagem relativos ao diretório do JSON.
    - Resolve Tipo 3 (variáveis/resoluções e substituições <...>) antes de renderizar.
    """
    # Carregar JSON(s) e detectar diretório base das imagens relativo ao JSON
    if isinstance(input_json, (list, tuple)):
        qs: List[Dict[str, Any]] = []
        json_dirs = []
        for p in input_json:
            qs.extend(_load_json_list(p))
            json_dirs.append(str(Path(p).parent.resolve()))
        base_dir = json_dirs[0] if json_dirs else None
    else:
        qs = _load_json_list(input_json)
        base_dir = str(Path(input_json).parent.resolve())

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
        # Unicode / fontes
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{lmodern}\n"
        "\\usepackage{textcomp}\n"
        "\\usepackage{upquote}\n"
        # tabularx para grade invisível (carregar ANTES do newcolumntype)
        "\\usepackage{array}\n"
        "\\usepackage{tabularx}\n"
        "\\newcolumntype{C}{>{\\centering\\arraybackslash}X}\n"
        # (opcional) mapeamentos Unicode úteis
        "\\usepackage{newunicodechar}\n"
        "% Grego minúsculo\n"
        "\\DeclareUnicodeCharacter{03B1}{\\ensuremath{\\alpha}}\n"      # α
        "\\DeclareUnicodeCharacter{03B2}{\\ensuremath{\\beta}}\n"       # β
        "\\DeclareUnicodeCharacter{03B3}{\\ensuremath{\\gamma}}\n"      # γ
        "\\DeclareUnicodeCharacter{03B4}{\\ensuremath{\\delta}}\n"      # δ
        "\\DeclareUnicodeCharacter{03B5}{\\ensuremath{\\varepsilon}}\n" # ε
        "\\DeclareUnicodeCharacter{03B8}{\\ensuremath{\\theta}}\n"      # θ
        "\\DeclareUnicodeCharacter{03BB}{\\ensuremath{\\lambda}}\n"     # λ
        "\\DeclareUnicodeCharacter{03BC}{\\ensuremath{\\mu}}\n"         # μ
        "\\DeclareUnicodeCharacter{03C0}{\\ensuremath{\\pi}}\n"         # π
        "\\DeclareUnicodeCharacter{03C1}{\\ensuremath{\\rho}}\n"        # ρ
        "\\DeclareUnicodeCharacter{03C3}{\\ensuremath{\\sigma}}\n"      # σ
        "\\DeclareUnicodeCharacter{03C6}{\\ensuremath{\\varphi}}\n"     # φ
        "\\DeclareUnicodeCharacter{03C9}{\\ensuremath{\\omega}}\n"      # ω
        "% Grego maiúsculo\n"
        "\\DeclareUnicodeCharacter{0394}{\\ensuremath{\\Delta}}\n"      # Δ
        "\\DeclareUnicodeCharacter{03A9}{\\ensuremath{\\Omega}}\n"      # Ω
        "% Símbolos comuns\n"
        "\\DeclareUnicodeCharacter{00B0}{\\ensuremath{^{\\circ}}}\n"    # °
        "\\DeclareUnicodeCharacter{00D7}{\\ensuremath{\\times}}\n"      # ×
        "\\DeclareUnicodeCharacter{2212}{-}\n"                          # − (minus sign U+2212) -> hífen
        "% Espaços especiais\n"
        "\\DeclareUnicodeCharacter{00A0}{~}\n"                          # NBSP
        "\\DeclareUnicodeCharacter{202F}{\\,}\n"                        # NNBSP -> espaço fino
        "% Sobrescritos Unicode comuns em unidades\n"
        "\\DeclareUnicodeCharacter{207B}{\\ensuremath{^{-}}}\n"         # ⁻ (superscript minus)
        "\\DeclareUnicodeCharacter{2070}{\\ensuremath{^{0}}}\n"
        "\\DeclareUnicodeCharacter{00B9}{\\ensuremath{^{1}}}\n"         # ¹
        "\\DeclareUnicodeCharacter{00B2}{\\ensuremath{^{2}}}\n"         # ²
        "\\DeclareUnicodeCharacter{00B3}{\\ensuremath{^{3}}}\n"         # ³
        "\\DeclareUnicodeCharacter{2074}{\\ensuremath{^{4}}}\n"
        "\\DeclareUnicodeCharacter{2075}{\\ensuremath{^{5}}}\n"
        "\\DeclareUnicodeCharacter{2076}{\\ensuremath{^{6}}}\n"
        "\\DeclareUnicodeCharacter{2077}{\\ensuremath{^{7}}}\n"
        "\\DeclareUnicodeCharacter{2078}{\\ensuremath{^{8}}}\n"
        "\\DeclareUnicodeCharacter{2079}{\\ensuremath{^{9}}}\n"
        "% Subscritos (U+2080..U+2089) — caso apareçam\n"
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

    for q in qs:
        # --- resolve Tipo 3 (variáveis + resoluções + substituições <...>) ---
        q_res, _env = resolve_all(q, seed=shuffle_seed)

        qid = q_res.get("id", "?")
        enun = (q_res.get("enunciado", "") or "").strip()
        enun_tex = latex_escape(enun)
        tipo = int(q_res.get("tipo", 1))

        # Alternativas (lista FINAL do pipeline, com garantia da correta presente)
        alts = _alts_final(q_res)

        # Imagens do enunciado
        imgs = q_res.get("imagens") or []

        # ---------------- Frame 1: sem gabarito ----------------
        parts.append("\\begin{frame}")
        parts.append(f"\\frametitle{{{qid}) {enun_tex}}}")
        parts.append("{\\BodySize")

        if imgs:
            parts.append(render_images(imgs, base_dir=base_dir))

        if q_res.get("afirmacoes"):
            parts.append(render_afirmacoes_line(q_res["afirmacoes"]))
            # SUBENUNCIADO (Tipo 4) — entre afirmações e alternativas
            sub = (q_res.get("subenunciado") or "").strip()
            if sub:
                parts.append(r"\medskip")
                parts.append("{\\BodySize " + latex_escape(sub) + "}")
                parts.append(r"\medskip")

        if tipo == 2:
            parts.append(render_alts_images(alts, base_dir=base_dir))
        else:
            # Lê K de 'alternativas;K' (apenas layout)
            K = _alternativas_firstrow(q_res)
            grid = render_alts_grid_beamer_from_list(
                alts=alts,
                correta=q_res.get('correta', ''),
                K=K,
                base_dir=base_dir,
                highlight_correct=False
            )
            parts.append(grid if grid else render_alts_text(alts, q_res.get('correta', ''), highlight=False))

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
            # SUBENUNCIADO (Tipo 4) — entre afirmações e alternativas
            sub = (q_res.get("subenunciado") or "").strip()
            if sub:
                parts.append(r"\medskip")
                parts.append("{\\BodySize " + latex_escape(sub) + "}")
                parts.append(r"\medskip")

        if tipo == 2:
            # Imagens: repetimos (sem highlight)
            parts.append(render_alts_images(alts, base_dir=base_dir))
        else:
            K = _alternativas_firstrow(q_res)
            grid = render_alts_grid_beamer_from_list(
                alts=alts,
                correta=q_res.get('correta', ''),
                K=K,
                base_dir=base_dir,
                highlight_correct=True
            )
            parts.append(grid if grid else render_alts_text(alts, q_res.get('correta', ''), highlight=True))

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

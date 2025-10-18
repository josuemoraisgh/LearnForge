# -*- coding: utf-8 -*-
"""
Geração de slides Beamer a partir de JSON de questões.

Padrões aplicados:
- Preâmbulo conforme template (beamer + Madrid, etc.) com mapeamento Unicode.
- Ordena por id; título do frame: "<id>) <enunciado>".
- Dois frames por questão: (1) sem gabarito; (2) com gabarito (\\alert{...}).
- Frame adicional de OBS. quando houver.
- Alternativas sempre a), b), c), d).
- Tipo 4: afirmativas em linha única "I. ...; II. ...; ..." (escapadas e com \\par).
- Tipo 2: alternativas por imagem; se arquivo não existir (relativo ao JSON), desenha um quadro vazio.
- Caminhos de imagem sempre relativos ao diretório do JSON.

Compatível com a GUI:
json2beamer(input_json, output_tex, shuffle_seed, title, fsq, fsa, alert_color, **kwargs)
"""

from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import json

# Importa o resolvedor do Tipo 3 (variáveis, resoluções e substituições <...>)
from core.variables import resolve_all

# --------------------------------------------------------------------
# Helpers internos
# --------------------------------------------------------------------

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf')

from pathlib import Path
import re

# Suporta "caminho;LxA" (em milímetros)
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
    return "".join(repl.get(ch, ch) for ch in s)

def _label(i: int) -> str:
    abc = "abcdefghijklmnopqrstuvwxyz"
    return abc[i] + ")" if i < len(abc) else f"{i+1})"

def _is_image_path(x: str) -> bool:
    p, _, _ = _parse_img_spec(x) if isinstance(x, str) else (x, None, None)
    return isinstance(p, str) and any(p.lower().endswith(ext) for ext in IMG_EXTS)

def _alts_with_correct(q: Dict[str, Any]) -> List[str]:
    """
    Garante que a alternativa correta esteja na lista (se não estiver),
    removendo duplicatas e preservando ordem.
    """
    alts = list(q.get("alternativas") or [])
    cor = (q.get("correta") or "").strip()
    if cor and not any((a or "").strip() == cor for a in alts):
        alts.append(cor)
    seen = set()
    out = []
    for a in alts:
        key = (a or "").strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out

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
    Renderiza as afirmativas (Tipo 4) em múltiplas linhas (lista itemize),
    mantendo a mesma assinatura para compatibilidade com os chamadores.
    Ordem fixa I, II, III… (sem embaralhar).
    """
    if not afirm:
        return ""
    order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
    itens = [f"{k}. {afirm[k]}" for k in order if k in afirm]
    if not itens:
        return ""

    # Escapa LaTeX e monta como lista
    safe_items = [latex_escape(x) for x in itens]
    lines = [r"\begin{itemize}"]
    lines += [r"\item " + s for s in safe_items]
    lines += [r"\end{itemize}"]
    return "\n".join(lines)


def render_alts_text(alts: List[str], correta: str, highlight: bool = False) -> str:
    """
    Alternativas em texto, rotuladas como a), b), c)…; se highlight=True, correta em \\alert{...}.
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
    Alternativas com imagens, rotuladas como a), b), c)…; se a imagem não existir, mostra quadro vazio.
    (Para imagens não aplicamos highlight via \\alert.)
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
            # Alternativa declarada como não-imagem em uma questão do tipo 2:
            # ainda assim mostramos um quadro (com rótulo), conforme orientação.
            lines.append(r"\item[" + label + "] " + r"\fbox{\rule{0pt}{4cm}\rule{6cm}{0pt}}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)

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
    shuffle_seed=None,             # não embaralhamos no Beamer; usado como seed do resolver T3
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

    # Ordenar por id
    try:
        qs = sorted(qs, key=lambda q: int(q.get("id", 0)))
    except Exception:
        pass

    # PREÂMBULO com mapeamento Unicode necessário ao pdfLaTeX
    preamble = (
        "\\documentclass[aspectratio=169]{beamer}\n"
        "\\usepackage{bookmark}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usetheme{Madrid}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{enumitem}\n"
        "% --- Unicode em pdfLaTeX ---\n"
        "\\usepackage{newunicodechar}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{lmodern}\n"
        "\\usepackage{textcomp}\n"
        "\\usepackage{upquote}\n"        
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
        # --- RESOLVE TIPO 3 (variáveis + resoluções + substituições <...>) ---
        q_res, _env = resolve_all(q, seed=shuffle_seed)

        qid = q_res.get("id", "?")
        enun = (q_res.get("enunciado", "") or "").strip()
        enun_tex = latex_escape(enun)
        tipo = int(q_res.get("tipo", 1))

        # Alternativas (no Beamer, sem embaralhar), garantindo correta presente
        alts = _alts_with_correct(q_res)

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
            sub = (q.get("subenunciado") or "").strip()
            if sub:
                parts.append(r"\medskip")
                parts.append("{\\BodySize " + latex_escape(sub) + "}")
                parts.append(r"\medskip")                     

        if tipo == 2:
            parts.append(render_alts_images(alts, base_dir=base_dir))
        else:
            parts.append(render_alts_text(alts, q_res.get('correta', ''), highlight=False))

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
            sub = (q.get("subenunciado") or "").strip()
            if sub:
                parts.append(r"\medskip")
                parts.append("{\\BodySize " + latex_escape(sub) + "}")
                parts.append(r"\medskip")              

        
        if tipo == 2:
            # Para imagem, mantemos sem highlight; apenas repetimos as imagens/quadro
            parts.append(render_alts_images(alts, base_dir=base_dir))
        else:
            # Para texto, destaca a correta
            parts.append(render_alts_text(alts, q_res.get('correta', ''), highlight=True))

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
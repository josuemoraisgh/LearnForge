# -*- coding: utf-8 -*-
r"""
Gera slides Beamer a partir de um JSON de questões com:
- 2 slides por questão (sem destaque / com a correta em vermelho via \alert{...})
- 3º slide opcional de OBS (se houver "obs")

Formato e tema:
- Usa preâmbulo fixo com \documentclass[12pt]{beamer}, bookmark, inputenc, amsmath, amssymb
- \usetheme{Madrid}  (mantém cabeçalho/rodapé e caixas azuis do template)
- \frametitle = "<ID>. <enunciado>"
- Enunciado NÃO se repete no corpo

Tamanhos (globais):
- FTITLE_SIZE controla o tamanho do \frametitle (vale para todos)
- fsq (parâmetro) controla o tamanho do corpo (\BodySize) — vale para todos
- fsa (parâmetro) mantém o tamanho das alternativas (se quiser ajustar o enumerate)

TIPO:
- Agora vem do JSON: q["tipo"] (1=textual, 2=imagens, 3=parametrizada, 4=afirmativas)
- Se não houver, assume 1

Uso (padrão):
    json2beamer()
"""

from typing import List, Dict, Any
import json, re, os, random

# ======= tamanhos globais =======
# tamanho do texto do \frametitle (Huge, huge, LARGE, Large, large, normalsize, small, ...)

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".bmp", ".webp")

def _norm_size(s: str, default: str) -> str:
    s = (s or "").strip()
    s = s.lstrip("\\")            # aceita "Large" ou "\Large"
    return s if s else default

def latex_escape(text: str) -> str:
    """Escapa LaTeX, preservando <PLACEHOLDERS>."""
    text = text or ""
    placeholders = re.findall(r"<[^<>]+>", text)
    tmp = text
    for i, ph in enumerate(placeholders):
        tmp = tmp.replace(ph, f"__PH{i}__")
    repl = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    out = "".join(repl.get(ch, ch) for ch in tmp)
    for i, ph in enumerate(placeholders):
        out = out.replace(f"__PH{i}__", ph)
    return out

def is_image_path(s: str) -> bool:
    return isinstance(s, str) and s.strip().lower().endswith(IMAGE_EXTS)

def beamer_title_block(title: str) -> str:
    return "\\title{{{}}}\n\\author{{}}\n\\date{{}}\n".format(latex_escape(title or "Exercícios"))

def render_images(imgs: List[str]) -> str:
    if not imgs: return ""
    lines = [r"\begin{center}"]
    for p in imgs:
        lines.append("\\includegraphics[width=0.85\\linewidth]{{{}}}\\\\[2mm]".format(latex_escape(p)))
    lines.append(r"\end{center}")
    return "\n".join(lines) + "\n"

def render_afirmacoes(afirm: Dict[str, str]) -> str:
    # if not afirm: return ""
    # # Ordena numeração romana (I, II, III, ...)
    # def roman_key(s: str) -> int:
    #     roman = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    #     s = s.strip().upper(); total = 0; prev = 0
    #     for ch in reversed(s):
    #         val = roman.get(ch,0)
    #         if val < prev: total -= val
    #         else: total += val; prev = val
    #     return total
    # items = sorted(afirm.items(), key=lambda kv: roman_key(kv[0]))
    # out = [r"\begin{itemize}"]
    # for k, v in items:
    #     out.append("\\item \\textbf{{{}}} {}".format(latex_escape(k), latex_escape(v)))
    # out.append(r"\end{itemize}")
    # return "\n".join(out) + "\n"

    """
    Renderiza afirmativas (tipo 4) a partir de dict OU lista.
       - dict {"I": "texto", "II": "texto", ...} -> ordena por romano
       - list/tuple ["texto I", "texto II", ...] -> rotula I, II, III, ...
    """
    if not afirm:
        return ""

    def int_to_roman(n: int) -> str:
        vals = [
            (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
        ]
        out = []
        x = n
        for v, sym in vals:
            while x >= v:
                out.append(sym)
                x -= v
        return "".join(out)

    if isinstance(afirm, (list, tuple)):
        itens = [(int_to_roman(i+1), s) for i, s in enumerate(afirm) if isinstance(s, str) and s.strip()]
        if not itens:
            return ""
        out = [r"\begin{itemize}"]
        for k, v in itens:
            out.append("\\item \\textbf{{{}}} {}".format(latex_escape(k), latex_escape(v)))
        out.append(r"\end{itemize}")
        return "\n".join(out) + "\n"

    if isinstance(afirm, dict):
        def roman_key(s: str) -> int:
            roman = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
            s = (s or "").strip().upper()
            total = 0
            prev = 0
            for ch in reversed(s):
                val = roman.get(ch,0)
                if val < prev:
                    total -= val
                else:
                    total += val
                    prev = val
            return total
        items = sorted(((str(k), str(v)) for k, v in afirm.items()), key=lambda kv: roman_key(kv[0]))
        if not items:
            return ""
        out = [r"\begin{itemize}"]
        for k, v in items:
            out.append("\\item \\textbf{{{}}} {}".format(latex_escape(k), latex_escape(v)))
        out.append(r"\end{itemize}")
        return "\n".join(out) + "\n"

    return ""    

def render_alts_text(alts: List[str], correta: str = "", highlight: bool = False) -> str:
    """Alternativas em texto com enumerate a), b), c) (requer enumitem no preâmbulo)."""
    if not alts:
        return r"\emph{(Sem alternativas no JSON.)}" + "\n"
    out = [r"\begin{enumerate}[label=\alph*)]"]
    for a in alts:
        t = latex_escape(a)
        if highlight and correta and a.strip() == correta.strip():
            out.append("\\item \\alert{{{}}}".format(t))
        else:
            out.append("\\item {}".format(t))
    out.append(r"\end{enumerate}")
    return "\n".join(out) + "\n"

def render_alts_images(alts: List[str], correta: str = "", highlight: bool = False) -> str:
    """Alternativas em 2 colunas de imagens/legendas."""
    if not alts:
        return r"\emph{(Sem alternativas no JSON.)}" + "\n"
    letters = "abcdefghijklmnopqrstuvwxyz"
    lines = [r"\begin{columns}"]
    for i, a in enumerate(alts):
        lines.append(r"\begin{column}{0.5\textwidth}")
        if is_image_path(a):
            lines.append(r"\begin{center}")
            lines.append("\\includegraphics[width=\\linewidth]{{{}}}".format(latex_escape(a)))
            cap = "\\textbf{{{} )}}".format(letters[i])
            if highlight and correta and a.strip() == (correta or "").strip():
                cap += r" \alert{(correta)}"
            lines.append(cap)
            lines.append(r"\end{center}")
        else:
            cap = "\\textbf{{{} )}} {}".format(letters[i], latex_escape(a))
            if highlight and correta and a.strip().lower().startswith('nenhuma') and (correta or '').strip().lower().startswith('nenhuma'):
                cap += r" \alert{(correta)}"
            lines.append(cap)
        lines.append(r"\end{column}")
        if (i % 2) == 1 and i != len(alts)-1:
            lines.append(r"\end{columns}")
            lines.append(r"\begin{columns}")
    lines.append(r"\end{columns}")
    return "\n".join(lines) + "\n"

def combine_and_shuffle_alternatives(q: Dict[str, Any], rng: random.Random) -> List[str]:
    """Inclui a correta (se faltar), remove duplicatas preservando ordem e embaralha."""
    alts = list(q.get("alternativas", []) or [])
    correta = (q.get("correta") or "").strip()
    if correta and not any((a or "").strip() == correta for a in alts):
        alts.append(correta)
    seen = set(); dedup = []
    for a in alts:
        key = (a or "").strip()
        if key in seen: continue
        seen.add(key); dedup.append(a)
    rng.shuffle(dedup)
    return dedup

def frame_title_text(q: Dict[str, Any]) -> str:
    qid = q.get("id","?")
    enun = (q.get("enunciado","") or "").strip()
    return "{}. {}".format(qid, latex_escape(enun))

def frame_question(q: Dict[str, Any], show_answer: bool, alts_shuffled: List[str]) -> str:
    """Um frame de questão. show_answer=True colore a correta com \alert{...} nas alternativas."""
    imgs = q.get("imagens", [])
    correta = (q.get("correta","") or "").strip()
    tipo = int(q.get("tipo", 1))  # AGORA vem do JSON; fallback = 1

    lines = [r"\begin{frame}", f"\\frametitle{{{frame_title_text(q)}}}"]
    # Corpo — aplica tamanho global \BodySize (um único grupo por frame)
    lines.append(r"{\BodySize")

    # Conteúdo extra por tipo
    if imgs: 
        lines.append(render_images(imgs))
    if tipo == 4:
        lines.append(render_afirmacoes(q.get("afirmacoes", {})))

    # Alternativas
    if tipo == 2:
        lines.append(render_alts_images(alts_shuffled, correta, highlight=show_answer))
    else:
        lines.append(render_alts_text(alts_shuffled, correta, highlight=show_answer))

    # (sem bloco "Gabarito: ...")
    lines.append("}")
    lines.append(r"\end{frame}")
    return "\n".join(lines) + "\n"

def frame_obs(q: Dict[str, Any]) -> str:
    """Slide de observações: \textbf{OBS.:} + \\item por linha."""
    obs_raw = q.get("obs")
    if isinstance(obs_raw, str):
        items = [obs_raw.strip()] if obs_raw.strip() else []
    elif isinstance(obs_raw, (list, tuple)):
        items = [str(x).strip() for x in obs_raw if isinstance(x, str) and str(x).strip()]
    else:
        items = []
    if not items: 
        return ""

    lines = [r"\begin{frame}", f"\\frametitle{{{frame_title_text(q)}}}"]
    lines.append(r"{\BodySize")
    lines.append(r"\textbf{OBS.:}")
    lines.append(r"\begin{itemize}")
    for it in items:
        lines.append("\\item " + latex_escape(it))
    lines.append(r"\end{itemize}")
    lines.append("}")
    lines.append(r"\end{frame}")
    return "\n".join(lines) + "\n"

def json2beamer(
    input_json = 'Exercicios_NS.json',
    output_tex  = 'Exercicios_NS_slides.tex',
    shuffle_seed = None,
    title = "Exercícios – Apresentação",
    fsq = "Large",          # tamanho do corpo (BODY)
    fsa = "normalsize",     # tamanho das alternativas (mantido pra compatibilidade)
    alert_color = "red"     # (não usado diretamente; \alert usa a cor do tema)
    ) -> int:

    # Carrega JSON
    data = json.load(open(input_json, "r", encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("O JSON deve ser um array de questões.")

    # --- PREÂMBULO FIXO (tema Madrid) — igual ao template que você descreveu ---
    preamble = (
        "\\documentclass[12pt]{beamer}\n"
        "\\usepackage{bookmark}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{amssymb}\n"
        "\\usetheme{Madrid}\n"
        # Pacotes utilitários necessários:
        "\\usepackage{graphicx}\n"
        "\\usepackage{enumitem}\n"   # para label=\alph*)
    )
    post = "\\end{document}\n"

    parts: List[str] = [
        preamble,
        beamer_title_block(title),
        r"\begin{document}",
        r"\frame{\titlepage}",
        # Tamanhos globais (sem criar grupos extras dentro dos frames)
        f"\\setbeamerfont{{frametitle}}{{size=\\{fsq}}}",
        f"\\newcommand{{\\BodySize}}{{\\{fsa}}}",
    ]

    rng = random.Random(shuffle_seed)
    qs = sorted(data, key=lambda q: q.get("id", 0))

    for q in qs:
        alts_shuffled = combine_and_shuffle_alternatives(q, rng)
        # 1) Sem destaque
        parts.append(frame_question(q, show_answer=False, alts_shuffled=alts_shuffled))
        # 2) Com correta em vermelho
        parts.append(frame_question(q, show_answer=True,  alts_shuffled=alts_shuffled))
        # 3) OBS (se houver)
        obs_frame = frame_obs(q)
        if obs_frame:
            parts.append(obs_frame)

    parts.append(post)

    with open(output_tex, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("Arquivo gerado:", output_tex)
    return 0

if __name__ == "__main__":
    json2beamer()
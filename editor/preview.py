# editor/preview.py
from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple, Optional
# --- ADICIONE ISTO PERTO DO TOPO ---
import hashlib
import random
import hashlib, random

_IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".pdf")

def _rng_for_q(seed, q: Dict[str, Any]) -> random.Random:
    """RNG determinístico por questão para posicionar a correta de forma reprodutível."""
    base = str(0 if seed is None else seed)
    salt = f"{q.get('id','')}|{q.get('enunciado','')}|{len(q.get('alternativas') or [])}"
    h = hashlib.sha256((base + "|" + salt).encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))  # 64 bits

def _to_int(x) -> Optional[int]:
    """Converte para int de forma segura; retorna None se não der."""
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return None

def _safe_img_spec(obj: Any) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Entende formatos:
      - "caminho|30x20"  (mm)  |  "caminho|30"
      - {"path": "...", "w": 30, "h": 20}  (ou file/src/img, width/height)
      - ("caminho", 30, 20)   /   ["caminho", 30, 20]
      - apenas "caminho"
    Nunca lança exceção.
    """
    # dict
    if isinstance(obj, dict):
        path = obj.get("path") or obj.get("file") or obj.get("src") or obj.get("img")
        w = obj.get("w") or obj.get("width")
        h = obj.get("h") or obj.get("height")
        return (str(path).strip() if path else None, _to_int(w), _to_int(h))

    # tuple/list
    if isinstance(obj, (tuple, list)) and obj:
        path = str(obj[0]).strip() if obj[0] is not None else None
        w = _to_int(obj[1]) if len(obj) > 1 else None
        h = _to_int(obj[2]) if len(obj) > 2 else None
        return (path, w, h)

    # string
    if isinstance(obj, str):
        s = obj.strip()
        m = re.match(r"^(.*?)(?:\|(\d+)(?:x(\d+))?)?\s*$", s)
        if m:
            path = (m.group(1) or "").strip() or None
            w = _to_int(m.group(2))  # pode ser None
            h = _to_int(m.group(3))  # pode ser None
            return (path, w, h)
        return (s or None, None, None)

    # fallback
    try:
        s = str(obj).strip()
        return (s or None, None, None)
    except Exception:
        return (None, None, None)

def _is_img_path(p: Optional[str]) -> bool:
    return isinstance(p, str) and p.lower().endswith(_IMG_EXTS)

def _flatten_to_questions(items: Any) -> List[Dict[str, Any]]:
    """
    Aceita:
      - lista de questões
      - lista contendo questões e/ou datasets {"questions":[...]}
      - um único dataset
      - uma única questão
    Retorna sempre lista de questões (dicts).
    """
    qs: List[Dict[str, Any]] = []

    def _extend_from(obj: Any):
        if isinstance(obj, dict) and isinstance(obj.get("questions"), list):
            for it in obj["questions"]:
                if isinstance(it, dict):
                    qs.append(it)
        elif isinstance(obj, dict):
            qs.append(obj)
        elif isinstance(obj, list):
            for it in obj:
                _extend_from(it)

    _extend_from(items)
    return qs

def preview_text(questions: List[Dict[str, Any]], title: str | None = None, **kwargs) -> str:
    """
    Preview:
    - Achata datasets para lista de questões.
    - Ordena por id.
    - Faz MERGE da 'correta' com as 'alternativas' em posição pseudo-aleatória determinística.
    - Prefixa a alternativa correta com a macro textual: "[correta] ".
    """
    alph = "abcdefghijklmnopqrstuvwxyz"
    lines: List[str] = []

    seed = kwargs.get("seed", kwargs.get("shuffle_seed", None))

    qs_raw = _flatten_to_questions(questions or [])
    qs = sorted(qs_raw, key=lambda q: int(q.get("id") or 0))

    if title:
        t = title.strip()
        lines.append(t)
        lines.append("=" * max(4, len(t)))
        lines.append("")

    for q in qs:
        # Cabeçalho da questão
        enun = (q.get("enunciado") or "").strip()
        try:
            qid = int(q.get("id")) if q.get("id") is not None else "?"
        except Exception:
            qid = "?"
        lines.append(f"{qid}) {enun}")

        # Imagens do enunciado (marcadores)
        imgs = q.get("imagens") or []
        if isinstance(imgs, (list, tuple)) and imgs:
            lines.append("")
            for img in imgs:
                p, w, h = _safe_img_spec(img)
                if _is_img_path(p):
                    size = f" {w}x{h}mm" if (w and h) else ""
                    lines.append(f"   [imagem: {p}{size}]")
                elif p:
                    lines.append(f"   [imagem: {p}]")
                else:
                    lines.append("   [imagem inválida]")

        # Afirmacoes + subenunciado
        afirm = q.get("afirmacoes") or {}
        if isinstance(afirm, dict) and afirm:
            lines.append("")
            order = ["I","II","III","IV","V","VI","VII","VIII","IX","X"]
            for k in order:
                if k in afirm:
                    lines.append(f"   {k}. {str(afirm[k]).strip()}")
            sub = (q.get("subenunciado") or "").strip()
            if sub:
                lines.append("")
                lines.append(f"   {sub}")

        # Alternativas + MERGE da correta em posição determinística
        base_alts = q.get("alternativas") or []
        correta_val = q.get("correta", None)

        alts = list(base_alts)  # cópia
        correta_index = -1
        if correta_val is not None and correta_val != "":
            rng = _rng_for_q(seed, q)
            pos = rng.randrange(0, len(alts) + 1)
            # Se já existe, remove a 1ª ocorrência para não duplicar
            try:
                existing = next(i for i, a in enumerate(alts) if str(a) == str(correta_val))
                alts.pop(existing)
                if existing < pos:
                    pos -= 1
            except StopIteration:
                pass
            alts.insert(pos, correta_val)
            correta_index = pos

        # Render das alternativas — correta com prefixo [correta]
        for i, alt in enumerate(alts):
            label = alph[i] + ")" if i < len(alph) else f"{i+1})"
            p, w, h = _safe_img_spec(alt)
            if _is_img_path(p):
                size = f" {w}x{h}mm" if (w and h) else ""
                s_view = f"[imagem: {p}{size}]"
            else:
                s_view = p if isinstance(alt, (dict, list, tuple)) else (str(alt) if alt is not None else "")
            if i == correta_index and s_view:
                s_view = f"[correta] {s_view}"
            lines.append(f"   {label} {s_view}")

        lines.append("")

    if lines:
        return "\n".join(lines)
    return (title.strip() + "\n" + "=" * max(4, len(title.strip())) + "\n\n(sem conteúdo)") if title else "(sem conteúdo)"

# -*- coding: utf-8 -*-
"""
Editor de Questões (Tk + ttk)
- Compatível com o JSON antigo (tipo, enunciado, alternativas, correta, variaveis/resolucoes, afirmacoes)
- Preview integrado ao core para tipos 1/2/4; fallback do preview antigo para tipo 3.
"""

import json, re, tkinter as tk
from codecs import decode as _dec
from tkinter import ttk, messagebox
from pathlib import Path
from copy import deepcopy

def _read_text_any(path: Path) -> str:
    b = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("utf-8", errors="replace")
from copy import deepcopy

# ==== utilitários existentes do seu projeto ====
from .question_utils import ensure_lists, tipo_of

# ==== core preview (para tipos 1/2/4) ====
#  -> editor.preview.preview_text chama core.parsers.to_ir internamente
try:
    from editor.preview import preview_text as core_preview_text
    _HAS_CORE_PREVIEW = True
except Exception:
    _HAS_CORE_PREVIEW = False

APP_TITLE = "Editor de Questões (JSON)"
ALPH = "abcdefghijklmnopqrstuvwxyz"


class QuestionEditor(tk.Toplevel):
    def __init__(self, master, json_path, on_saved=None):
        super().__init__(master)
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.json_path = Path(json_path)
        self.on_saved = on_saved
        self._loading = False

        # carrega JSON
        try:
            self.data = json.loads(_read_text_any(self.json_path))
            if not isinstance(self.data, list):
                raise ValueError("JSON não é um array de questões.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Erro ao abrir JSON:\n{e}", parent=self)
            self.destroy()
            return

        self.idx = 0
        self.var_dirty = tk.BooleanVar(value=False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_notebook()

        self.bind("<Left>", lambda e: self.prev())
        self.bind("<Right>", lambda e: self.next())
        self.bind("<Control-s>", lambda e: self.save())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.load_current()

    # ----------------- UI -----------------
    def _build_topbar(self):
        bar = ttk.Frame(self, padding=(10,10,10,10))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(3, weight=1)

        ttk.Button(bar, text="◀", width=3, command=self.prev).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(bar, text="▶", width=3, command=self.next).grid(row=0, column=1, padx=(0, 10))

        ttk.Label(bar, text="Ir para questão:").grid(row=0, column=2, sticky="e")
        self.cmb_go = ttk.Combobox(bar, state="readonly", width=40)
        self.cmb_go.grid(row=0, column=3, sticky="ew", padx=(6, 10))
        self.cmb_go.bind("<<ComboboxSelected>>", self.on_go_selected)

        ttk.Button(bar, text="Novo", command=self.new_after_current).grid(row=0, column=4, padx=4)
        ttk.Button(bar, text="Salvar (Ctrl+S)", command=self.save).grid(row=0, column=5, padx=4)
        ttk.Button(bar, text="Clonar", command=self.clone_current).grid(row=0, column=6, padx=4)
        ttk.Button(bar, text="Excluir", command=self.delete_current).grid(row=0, column=7, padx=4)

        self.lbl_pos = ttk.Label(bar, text="—")
        self.lbl_pos.grid(row=0, column=8, padx=(10, 0))

    def _build_notebook(self):
        self.nb = ttk.Notebook(self, padding=(10, 10, 10, 10))
        self.nb.grid(row=1, column=0, sticky="nsew")

        # formulário
        self.tab_form = ttk.Frame(self.nb)
        self.nb.add(self.tab_form, text="Formulário")

        left = self.tab_form
        left.columnconfigure(1, weight=1)
        r = 0
        PADY_LINHA = 6  # <-- espaçamento vertical entre linhas

        ttk.Label(left, text="ID:").grid(row=r, column=0, sticky="w", pady=(0, PADY_LINHA))
        self.ent_id = ttk.Entry(left, width=10)
        self.ent_id.grid(row=r, column=1, sticky="w", pady=(0, PADY_LINHA))
        r += 1

        ttk.Label(left, text="Tipo (1/2/3/4):").grid(row=r, column=0, sticky="w", pady=(0, PADY_LINHA))
        self.cmb_tipo = ttk.Combobox(left, values=["1", "2", "3", "4"], state="readonly", width=6)
        self.cmb_tipo.grid(row=r, column=1, sticky="w", pady=(0, PADY_LINHA))
        r += 1

        ttk.Label(left, text="Dificuldade:").grid(row=r, column=0, sticky="w", pady=(0, PADY_LINHA))
        self.cmb_diff = ttk.Combobox(left, values=["fácil", "média", "difícil"], state="readonly")
        self.cmb_diff.grid(row=r, column=1, sticky="ew", pady=(0, PADY_LINHA))
        r += 1

        ttk.Label(left, text="Enunciado:").grid(row=r, column=0, sticky="nw", pady=(0, PADY_LINHA))
        self.txt_enun = tk.Text(left, height=2, wrap="word")
        self.txt_enun.grid(row=r, column=1, sticky="nsew", pady=(0, PADY_LINHA))
        left.rowconfigure(r, weight=1)
        r += 1

        ttk.Label(left, text="Imagens:\n(uma por linha)").grid(row=r, column=0, sticky="nw", pady=(0, PADY_LINHA))
        self.txt_imgs = tk.Text(left, height=3, wrap="none")
        self.txt_imgs.grid(row=r, column=1, sticky="ew", pady=(0, PADY_LINHA))
        r += 1

        ttk.Label(left, text="Alternativas:\n(uma por linha)").grid(row=r, column=0, sticky="nw", pady=(0, PADY_LINHA))
        self.txt_alts = tk.Text(left, height=10, wrap="word")
        self.txt_alts.grid(row=r, column=1, sticky="nsew", pady=(0, PADY_LINHA))
        left.rowconfigure(r, weight=2)
        r += 1

        ttk.Label(left, text="Correta:").grid(row=r, column=0, sticky="w", pady=(0, PADY_LINHA))
        self.ent_correct = ttk.Entry(left)
        self.ent_correct.grid(row=r, column=1, sticky="ew", pady=(0, PADY_LINHA))
        r += 1

        # tipo 3 (variáveis e resoluções)
        self.frm_tipo3 = ttk.LabelFrame(left, text="Tipo 3 – Variáveis & Resoluções")
        self.frm_tipo3.columnconfigure(1, weight=1)
        self.frm_tipo3.grid(row=r, column=0, columnspan=2, sticky="nsew", pady=(8, PADY_LINHA))
        r += 1

        ttk.Label(self.frm_tipo3, text="Variáveis: VAR=min:max:step (uma por linha)").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, PADY_LINHA))
        self.txt_vars = tk.Text(self.frm_tipo3, height=4, wrap="none")
        self.txt_vars.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, PADY_LINHA))

        ttk.Label(self.frm_tipo3, text="Resoluções: NOME=expressão (uma por linha)").grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, PADY_LINHA))
        self.txt_res = tk.Text(self.frm_tipo3, height=4, wrap="none")
        self.txt_res.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, PADY_LINHA))

        # tipo 4 (afirmações)
        self.frm_tipo4 = ttk.LabelFrame(left, text="Tipo 4 – Afirmações (chave=texto)")
        self.frm_tipo4.columnconfigure(0, weight=1)
        self.txt_aff = tk.Text(self.frm_tipo4, height=6, wrap="word")
        self.txt_aff.grid(row=0, column=0, sticky="nsew", pady=(0, PADY_LINHA))
        self.frm_tipo4.grid(row=r, column=0, columnspan=2, sticky="nsew", pady=(8, PADY_LINHA))
        r += 1

        ttk.Label(left, text="Observações:\n(uma linha por item)").grid(row=r, column=0, sticky="nw", pady=(0, PADY_LINHA))
        self.txt_obs = tk.Text(left, height=4, wrap="word")
        self.txt_obs.grid(row=r, column=1, sticky="ew", pady=(0, PADY_LINHA))
        r += 1

        # preview
        self.tab_prev = ttk.Frame(self.nb)
        self.nb.add(self.tab_prev, text="Preview")
        self.tab_prev.columnconfigure(0, weight=1)
        self.tab_prev.rowconfigure(0, weight=1)

        self.txt_preview = tk.Text(self.tab_prev, height=24, wrap="word", state="disabled")
        self.txt_preview.grid(row=0, column=0, sticky="nsew")

        # eventos p/ marcar alteração
        for txt in (self.txt_enun, self.txt_imgs, self.txt_alts, self.txt_obs, self.txt_vars, self.txt_res, self.txt_aff):
            txt.bind("<KeyRelease>", self._mark_dirty, add="+")

        self.cmb_tipo.bind("<<ComboboxSelected>>", self._on_tipo_changed, add="+")
        self.cmb_diff.bind("<<ComboboxSelected>>", self._mark_dirty, add="+")
        self.ent_correct.bind("<KeyRelease>", self._mark_dirty, add="+")
        self.ent_id.bind("<FocusOut>", lambda e: self._on_id_focusout(), add="+")
        self.ent_id.bind("<Return>", lambda e: self._on_id_focusout(), add="+")

        self.nb.bind("<<NotebookTabChanged>>", lambda e: (self.update_preview() if self.nb.select() == str(self.tab_prev) else None))

    # ----------------- navegação -----------------
    def _on_close(self):
        if self.var_dirty.get():
            if not messagebox.askyesno(APP_TITLE, "Há alterações não salvas. Deseja descartar?", parent=self):
                return
        self.destroy()

    def _confirm_unsaved(self):
        if self.var_dirty.get():
            return messagebox.askyesno(APP_TITLE, "Há alterações não salvas. Deseja descartar?", parent=self)
        return True

    def _mark_dirty(self, *_):
        if getattr(self, "_loading", False):
            return
        self.var_dirty.set(True)

    def _populate_dropdown(self):
        items = [f"{q.get('id')} – {q.get('enunciado','')[:40].replace('\n',' ')}" for q in self.data]
        self.cmb_go["values"] = items
        if items:
            self.cmb_go.current(self.idx)

    def on_go_selected(self, _=None):
        new_idx = self.cmb_go.current()
        if new_idx != -1 and new_idx != self.idx:
            if not self._confirm_unsaved():
                self._populate_dropdown()
                return
            self.idx = new_idx
            self.load_current()

    def prev(self):
        if self.idx <= 0:
            return
        if not self._confirm_unsaved():
            return
        self.idx -= 1
        self.load_current()

    def next(self):
        if self.idx >= len(self.data) - 1:
            return
        if not self._confirm_unsaved():
            return
        self.idx += 1
        self.load_current()

    # ----------------- helpers de texto -----------------
    def _set_text(self, txt: tk.Text, content: str):
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("1.0", content or "")
        txt.configure(state="normal")

    def _get_lines(self, txt: tk.Text):
        raw = txt.get("1.0", "end").strip()
        return [line for line in raw.splitlines()] if raw else []

    # ----------------- carga/armazenamento -----------------
    def load_current(self):
        self._loading = True
        try:
            q = self.data[self.idx]
            ensure_lists(q)

            # form
            self.ent_id.delete(0, "end")
            self.ent_id.insert(0, str(q.get("id", "")))
            self.cmb_tipo.set(str(tipo_of(q)))
            self.cmb_diff.set(q.get("dificuldade", "média"))
            self._set_text(self.txt_enun, q.get("enunciado", ""))
            self._set_text(self.txt_imgs, "\n".join(q.get("imagens") or []))
            self._set_text(self.txt_alts, "\n".join(q.get("alternativas") or []))
            self.ent_correct.delete(0, "end")
            self.ent_correct.insert(0, q.get("correta", ""))
            self._set_text(self.txt_obs, "\n".join(q.get("obs") or []))

            # tipo3
            vars_lines = []
            for name, cfg in (q.get("variaveis") or {}).items():
                vars_lines.append(f"{name}={cfg.get('min',0)}:{cfg.get('max',0)}:{cfg.get('step',1)}")
            self._set_text(self.txt_vars, "\n".join(vars_lines))

            res_lines = []
            for name, expr in (q.get("resolucoes") or {}).items():
                res_lines.append(f"{name}={expr}")
            self._set_text(self.txt_res, "\n".join(res_lines))

            # tipo4
            aff_lines = []
            for k, v in (q.get("afirmacoes") or {}).items():
                aff_lines.append(f"{k}={v}")
            self._set_text(self.txt_aff, "\n".join(aff_lines))

            self._toggle_panels(int(self.cmb_tipo.get()))
            self.lbl_pos.configure(text=f"Questão {self.idx+1} de {len(self.data)}")
            self._populate_dropdown()
            self.var_dirty.set(False)

            self.update_preview()
        finally:
            self._loading = False

    def _toggle_panels(self, t: int):
        (self.frm_tipo3.grid if t == 3 else self.frm_tipo3.grid_remove)()
        (self.frm_tipo4.grid if t == 4 else self.frm_tipo4.grid_remove)()

    def _on_tipo_changed(self, _=None):
        try:
            t = int(self.cmb_tipo.get())
        except Exception:
            t = tipo_of(self.data[self.idx])
        self._toggle_panels(t)
        self._mark_dirty()

    def _on_id_focusout(self):
        self._mark_dirty()

    def collect_form(self):
        q = self.data[self.idx]

        # id
        try:
            new_id = int(self.ent_id.get().strip())
            if new_id < 1:
                raise ValueError
        except Exception:
            raise ValueError("ID inválido (use inteiro >= 1).")
        q["id"] = new_id

        # tipo/dificuldade
        q["tipo"] = int(self.cmb_tipo.get()) if self.cmb_tipo.get() else tipo_of(q)
        q["dificuldade"] = self.cmb_diff.get().strip() or "média"

        # textos
        q["enunciado"] = self.txt_enun.get("1.0", "end").strip()
        q["imagens"] = [l for l in self._get_lines(self.txt_imgs) if l.strip()]
        q["alternativas"] = [l for l in self._get_lines(self.txt_alts) if l.strip()]
        q["correta"] = self.ent_correct.get().strip()
        q["obs"] = [l for l in self._get_lines(self.txt_obs)]

        # tipo3
        if q["tipo"] == 3:
            vs = {}
            for line in self._get_lines(self.txt_vars):
                if not line.strip():
                    continue
                if "=" not in line or ":" not in line:
                    raise ValueError(f"Variável inválida: {line}")
                name, rng = line.split("=", 1)
                try:
                    mn, mx, st = [float(x) for x in rng.split(":")]
                    if st <= 0 or mn > mx:
                        raise ValueError
                except Exception:
                    raise ValueError(f"Variável {name}: faixa inválida.")
                vs[name.strip()] = {"min": mn, "max": mx, "step": st}
            q["variaveis"] = vs

            rs = {}
            for line in self._get_lines(self.txt_res):
                if "=" not in line:
                    continue
                name, expr = line.split("=", 1)
                if name.strip() and expr.strip():
                    rs[name.strip()] = expr.strip()
            q["resolucoes"] = rs
            q.pop("afirmacoes", None)

        # tipo4
        elif q["tipo"] == 4:
            aff = {}
            for line in self._get_lines(self.txt_aff):
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() and v.strip():
                    aff[k.strip()] = v.strip()
            q["afirmacoes"] = aff
            q.pop("variaveis", None)
            q.pop("resolucoes", None)

        else:
            q.pop("variaveis", None)
            q.pop("resolucoes", None)
            q.pop("afirmacoes", None)

        return q

    def validate_question(self, q):
        if not q.get("enunciado"):
            raise ValueError("Enunciado não pode ser vazio.")
        if not isinstance(q.get("alternativas"), list):
            raise ValueError("Alternativas deve ser uma lista.")
        if q.get("tipo") == 3:
            if not q.get("variaveis") or not q.get("resolucoes"):
                raise ValueError("Tipo 3: requer variaveis e resolucoes.")
        if q.get("tipo") == 4:
            if not q.get("afirmacoes"):
                raise ValueError("Tipo 4: requer afirmacoes.")

    def _normalize_and_reorder_ids(self):
        self.data.sort(key=lambda q: int(q.get("id", 1)))
        for i, q in enumerate(self.data, start=1):
            q["id"] = i

    def save(self):
        try:
            current = self.collect_form()
            self.validate_question(current)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Erro de validação:\n{e}", parent=self)
            return

        # reposiciona conforme ID
        try:
            new_pos = int(current["id"]) - 1
        except Exception:
            new_pos = self.idx

        item = self.data.pop(self.idx)
        self.data.insert(max(0, min(new_pos, len(self.data))), item)
        self._normalize_and_reorder_ids()
        self.idx = min(max(0, new_pos), len(self.data) - 1)

        try:
            self.json_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.var_dirty.set(False)
            if self.on_saved:
                self.on_saved()
            messagebox.showinfo(APP_TITLE, "Questão salva e JSON atualizado.", parent=self)
            self._populate_dropdown()
            self.load_current()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Erro ao salvar JSON:\n{e}", parent=self)

    def delete_current(self):
        if not messagebox.askyesno(APP_TITLE, "Excluir esta questão? A operação não pode ser desfeita.", parent=self):
            return
        del self.data[self.idx]
        if not self.data:
            messagebox.showinfo(APP_TITLE, "Todas as questões foram removidas.", parent=self)
            self.destroy()
            return
        self._normalize_and_reorder_ids()
        self.idx = min(self.idx, len(self.data) - 1)
        self.save()

    def clone_current(self):
        clone = deepcopy(self.data[self.idx])
        self.data.insert(self.idx + 1, clone)
        self._normalize_and_reorder_ids()
        self.idx = self.idx + 1
        self.save()

    def new_after_current(self):
        new_q = {
            "id": self.data[self.idx]["id"] + 1,
            "tipo": 1,
            "dificuldade": "média",
            "enunciado": "",
            "imagens": [],
            "alternativas": [],
            "correta": "",
            "obs": [],
        }
        self.data.insert(self.idx + 1, new_q)
        self._normalize_and_reorder_ids()
        self.idx = self.idx + 1
        self.var_dirty.set(True)
        self.load_current()

    # ----------------- PREVIEW -----------------
    def update_preview(self):
        """Gera preview; usa core (tipos 1/2/4) e fallback local para tipo 3."""
        try:
            q = self.collect_form()
        except Exception:
            q = self.data[self.idx]

        # monta uma cópia do conjunto, com a questão atual atualizada
        qs = deepcopy(self.data)
        qs[self.idx] = deepcopy(q)

        # divide em tipo3 e demais
        non_t3 = []
        only_t3 = []
        for item in qs:
            if int(tipo_of(item)) == 3:
                only_t3.append(item)
            else:
                non_t3.append(self._normalize_for_core(item))

        lines = []

        # Renderização unificada via core (todos os tipos 1/2/3/4)
        try:
            text_core = core_preview_text(qs, title="Pré-visualização")
            lines = [text_core.strip()]
        except Exception as e:
            lines = [f"[preview via core falhou]: {e}"]

        # imprime
        out = ("\n\n" + ("-" * 28) + "\n\n").join([s for s in lines if s]) or "(sem conteúdo)"
        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", out)
        self.txt_preview.configure(state="disabled")

    # -------- normalização para o core (tipos 1,2,4) --------
    def _normalize_for_core(self, q):
        """Converte do seu formato para o esperado pelo core.preview."""
        t = int(tipo_of(q))
        base = {"prompt": q.get("enunciado", ""), "meta": {"dificuldade": q.get("dificuldade", "")}}

        if t == 1:
            obj = {
                **base,
                "type": "type1",
                "options": q.get("alternativas") or [],
            }
            corr = q.get("correta", "").strip()
            if corr:
                try:
                    # se veio 'a','b','c'... mapeia; se veio inteiro 1..n mapeia
                    idx = self._norm_index(corr, len(obj["options"]))
                    obj["answer"] = idx + 1 if idx >= 0 else corr
                except Exception:
                    obj["answer"] = corr
            return obj

        if t == 2:
            ans = q.get("correta", "").strip()
            truth = None
            if ans:
                s = ans.lower()
                if s in ("v", "verdadeiro", "true", "t", "sim", "s", "yes", "y", "1"):
                    truth = True
                elif s in ("f", "falso", "false", "n", "nao", "não", "no", "0"):
                    truth = False
            return {**base, "type": "type2", "answer": truth}

        if t == 4:
            if q.get("afirmacoes"):
                return {**base, "type": "type4", "pairs": [[k, v] for k, v in q["afirmacoes"].items()]}
            answers = []
            if q.get("correta"):
                answers = [q["correta"]]
            return {**base, "type": "type4", "answers": answers}

        # fallback tratá-lo como type1
        return {**base, "type": "type1", "options": q.get("alternativas") or []}

    def _norm_index(self, x, n):
        if isinstance(x, int):
            if 0 <= x < n:
                return x
            if 1 <= x <= n:
                return x - 1
        if isinstance(x, str) and x:
            ch = x.strip().lower()
            if ch.isalpha() and len(ch) == 1:
                return ord(ch) - 97
            if ch.isdigit():
                k = int(ch)
                return k - 1 if 1 <= k <= n else k
            # tenta achar pelo texto da alternativa
        return -1

    # -------- preview local do tipo 3 (o seu formato) --------
    def _render_local_tipo3(self, q):
        """Renderiza tipo 3 com variáveis/resoluções e placeholders <...>."""
        lines = []
        first = f"{q.get('id')}) {q.get('enunciado','').strip()}"
        lines.append(first)
        lines.append("")

        # valores "fixos" (usa mínimo como referência na prévia)
        vals = {}
        for name, cfg in (q.get("variaveis") or {}).items():
            try:
                vals[name] = float(cfg.get("min", 0))
            except Exception:
                vals[name] = 0.0

        # derivados
        derived = {}
        for name, expr in (q.get("resolucoes") or {}).items():
            expr_clean = self._expr_clean(expr, vals, {})
            try:
                derived[name] = self._safe_eval(expr_clean)
            except Exception:
                derived[name] = float("nan")

        # alternativas (correta primeiro se existir)
        alts = q.get("alternativas") or []
        corr = q.get("correta", "")
        ordered = []
        if corr:
            ordered.append(corr)
        ordered += [a for a in alts if a != corr]

        for i, a in enumerate(ordered):
            letter = ALPH[i % len(ALPH)]
            s = self._render_text(a, vals, derived)
            lines.append(f"{letter}) {s}")

        if q.get("obs"):
            lines.append("")
            lines.append("OBS.:")
            for line in q["obs"]:
                lines.append(line)

        return "\n".join(lines)

    # avaliação simples: só números + operadores seguros
    def _safe_eval(self, expr):
        expr = re.sub(r"[^0-9+\-*/(). ]", "", expr)
        return eval(expr, {"__builtins__": {}}, {})

    def _expr_clean(self, expr, vals, derived):
        def replace_token(m):
            token = m.group(1)
            if token in vals:
                return str(vals[token])
            if token in derived:
                return str(derived[token])
            return "0"

        expr2 = re.sub(r"<\s*([A-Za-z0-9_]+)\s*>", replace_token, expr)
        expr2 = re.sub(r"[^0-9+\-*/(). ]", "", expr2)
        return expr2

    def _render_text(self, text, vals, derived):
        def repl(m):
            inner = m.group(1).strip()
            m2 = re.match(r"^([A-Za-z0-9_]+)\s*([+\-*/])\s*([0-9.]+)$", inner)
            if m2:
                name, op, num = m2.groups()
                base = vals.get(name, derived.get(name, 0.0))
                try:
                    num = float(num)
                except Exception:
                    num = 0.0
                try:
                    ex = f"{base}{op}{num}"
                    return f"{self._safe_eval(ex):.6f}"
                except Exception:
                    return inner
            base = vals.get(inner, derived.get(inner, None))
            if base is None:
                return inner
            try:
                return f"{float(base):.6f}"
            except Exception:
                return str(base)

        return re.sub(r"<([^>]+)>", repl, text)

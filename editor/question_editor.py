# -*- coding: utf-8 -*-
"""
Editor de Questões (Tk + ttk) — formulário genérico com scrollbar e largura total.
- Renderiza dinamicamente cada campo conforme o TIPO do valor:
    int          -> Entry (1 linha)
    'dificuldade'-> Combobox (fácil/média/difícil) [único caso especial]
    str          -> Text (2 linhas)
    list         -> Text (5 linhas) — 1 item por linha
    dict         -> "tabela" 2 colunas (chave/valor), 5 linhas visíveis (colunas 1:3)
- Todos os frames se expandem na largura disponível (canvas ajusta o inner frame).
- Ordem dos campos = ordem das chaves no JSON.
- Preview integrado ao core (editor.preview.preview_text).

>>> Alteração solicitada:
- Remover os botões "Novo", "Salvar (Ctrl+S)", "Clonar" e "Excluir" da topbar.
- Inserir esses botões no INÍCIO da aba "Formulário".
"""

from __future__ import annotations
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from core.loader import load_quiz
from editor.preview import preview_text
from editor.raw import format_question_json

APP_TITLE = "Editor de Questões (JSON)"
DIFF_OPTIONS = ["fácil", "média", "difícil"]
# -------- Campos que podem ser inseridos automaticamente e seus valores padrão --------
_ALLOWED_FIELDS_DEFAULTS = {
    # básicos
    "dificuldade": "média",
    "enunciado": "",
    "subenunciado": "",
    "imagens": [],
    "alternativas": [],
    "correta": "",
    "obs": [],
    # de uso avançado (caso utilize)
    "afirmacoes": {},     # ex.: {"I": "", "II": ""}
    "variaveis": {},      # core valida formato no momento da resolução
    "resolucoes": {},     # idem
    # "id" propositalmente fora para não ser inserido/excluído por aqui
}
class QuestionEditor(tk.Toplevel):
    def __init__(self, master, json_path, on_saved=None):
        super().__init__(master)
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.json_path = Path(json_path)
        self.on_saved = on_saved

        # Carregar via core
        try:
            ds = load_quiz(self.json_path, isMath=False)
            self.dataset: Dict[str, Any] = ds
            self.data: List[Dict[str, Any]] = ds.get("questions", [])
            self.meta: Dict[str, Any] = ds.get("meta", {})
            if not isinstance(self.data, list):
                raise ValueError("JSON não é uma lista de questões após normalização.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Erro ao abrir JSON:\n{e}", parent=self)
            self.destroy()
            return

        self.idx = 0
        self.var_dirty = tk.BooleanVar(value=False)
        self._loading = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_notebook()

        self.bind("<Left>", lambda e: self.prev())
        self.bind("<Right>", lambda e: self.next())
        self.bind("<Control-s>", lambda e: self.save())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.load_current()

    # ----------------- UI (barra superior) -----------------
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


    # ----------------- UI (tabs + formulário com scroll) -----------------
    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.grid(row=1, column=0, sticky="nsew")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # --------------- Aba: Formulário ---------------
        self.tab_form = ttk.Frame(self.nb)
        self.nb.add(self.tab_form, text="Formulário")
        self.tab_form.columnconfigure(0, weight=1)
        self.tab_form.rowconfigure(1, weight=1)  # <- o container do form fica na linha 1


        # -------- Formulário (scrollable) --------
        # Toolbar PEDIDA dentro da aba Formulário (no topo)
        toolbar = ttk.Frame(self.tab_form, padding=(2, 6, 2, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=0)
        toolbar.columnconfigure(1, weight=1)
        toolbar.columnconfigure(2, weight=0)
        toolbar.columnconfigure(3, weight=0)

        # Combobox para escolher o campo a excluir
        ttk.Label(toolbar, text="Campo:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.cmb_field = ttk.Combobox(toolbar, state="readonly", width=28)
        self.cmb_field.grid(row=0, column=1, sticky="w")

        # Botões (criar SEM encadear .grid/.pack)
        self.btn_field_insert = ttk.Button(toolbar, text="Inserir", command=self._insert_field_menu)
        self.btn_field_insert.grid(row=0, column=2, padx=(12, 6))

        self.btn_field_delete = ttk.Button(toolbar, text="Excluir", command=self._remove_field_selected)
        self.btn_field_delete.grid(row=0, column=3)
        self.btn_field_delete.state(["disabled"])


        # Container com canvas + scrollbar (formulário)
        container = ttk.Frame(self.tab_form)
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.form_canvas = tk.Canvas(container, highlightthickness=0)
        self.form_canvas.grid(row=0, column=0, sticky="nsew")

        self.form_vsb = ttk.Scrollbar(container, orient="vertical", command=self.form_canvas.yview)
        self.form_vsb.grid(row=0, column=1, sticky="ns")
        self.form_canvas.configure(yscrollcommand=self.form_vsb.set)

        self.form_frame = ttk.Frame(self.form_canvas)
        self.form_frame.columnconfigure(0, weight=1)  # <- permite que cada field ocupe a largura
        # Atualiza a scrollregion ao crescer
        self.form_frame.bind(
            "<Configure>",
            lambda e: self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all")),
        )
        # Cria o frame dentro do canvas e guarda o window_id
        self._form_window_id = self.form_canvas.create_window((0, 0), window=self.form_frame, anchor="nw")

        # Ajusta a largura do inner frame para ocupar 100% da área visível do CANVAS
        def _resize_inner(ev=None):
            width = ev.width if ev and hasattr(ev, "width") else self.form_canvas.winfo_width()
            if width > 0:
                self.form_canvas.itemconfig(self._form_window_id, width=width)
        self.form_canvas.bind("<Configure>", _resize_inner)

        # Scroll do mouse (somente nesta aba)
        def _on_mousewheel(event):
            if self.nb.select() == str(self.tab_form):
                self.form_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        self.form_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Dicionário de editores renderizados dinamicamente
        self.editors: Dict[str, Dict[str, Any]] = {}

        # -------- Preview --------
        self.tab_prev = ttk.Frame(self.nb)
        self.nb.add(self.tab_prev, text="Preview")
        self.tab_prev.columnconfigure(0, weight=1)
        self.tab_prev.rowconfigure(0, weight=1)

        self.txt_preview = tk.Text(self.tab_prev, height=24, wrap="word", state="disabled")
        self.txt_preview.grid(row=0, column=0, sticky="nsew")

        self.nb.bind(
            "<<NotebookTabChanged>>",
            lambda e: (self.update_preview() if self.nb.select() == str(self.tab_prev) else None),
        )

        # -------- Raw (JSON da questão atual) --------
        self.tab_raw = ttk.Frame(self.nb)
        self.nb.add(self.tab_raw, text="Raw")
        self.tab_raw.columnconfigure(0, weight=1)
        self.tab_raw.rowconfigure(0, weight=1)

        raw_container = ttk.Frame(self.tab_raw)
        raw_container.grid(row=0, column=0, sticky="nsew")
        raw_container.columnconfigure(0, weight=1)
        raw_container.rowconfigure(0, weight=1)

        self.txt_raw = tk.Text(raw_container, wrap="none", state="disabled")
        self.txt_raw.grid(row=0, column=0, sticky="nsew")

        # barras de rolagem horizontais e verticais
        raw_vsb = ttk.Scrollbar(raw_container, orient="vertical", command=self.txt_raw.yview)
        raw_vsb.grid(row=0, column=1, sticky="ns")
        raw_hsb = ttk.Scrollbar(raw_container, orient="horizontal", command=self.txt_raw.xview)
        raw_hsb.grid(row=1, column=0, sticky="ew")
        self.txt_raw.configure(yscrollcommand=raw_vsb.set, xscrollcommand=raw_hsb.set)

        try:
            import tkinter.font as tkfont
            self.txt_raw.configure(font=tkfont.nametofont("TkFixedFont"))
        except Exception:
            pass

        # Atualiza o Raw quando a aba for selecionada
        self.nb.bind(
            "<<NotebookTabChanged>>",
            lambda e: (self.update_raw() if self.nb.select() == str(self.tab_raw) else None),
        )

    # ----------------- navegação -----------------
    def _on_close(self):
        if self.var_dirty.get():
            if not messagebox.askyesno(APP_TITLE, "Há alterações não salvas. Deseja descartar?", parent=self):
                return
        self.destroy()

    def _confirm_unsaved(self) -> bool:
        return (not self.var_dirty.get()) or messagebox.askyesno(
            APP_TITLE, "Há alterações não salvas. Deseja descartar?", parent=self
        )

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

    # ----------------- utils UI -----------------
    def _mark_dirty(self, *_):
        if self._loading:
            return
        self.var_dirty.set(True)

    def _populate_dropdown(self):
        items = [f"{q.get('id')} – {str(q.get('enunciado','')).splitlines()[0][:60]}" for q in self.data]
        self.cmb_go["values"] = items
        if items:
            self.cmb_go.current(self.idx)

    def _clear_form(self):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.editors.clear()

    def _label_frame(self, parent, title: str):
        frm = ttk.LabelFrame(parent, text=title)
        frm.columnconfigure(0, weight=1)  # permite esticar horizontalmente
        return frm

    # ----------------- renderização dinâmica -----------------
    def _render_field(self, row: int, key: str, value: Any):
        """Cria um LabelFrame + widget adequado ao tipo do valor."""
        # Caso especial: dificuldade (Combobox)
        if key == "dificuldade":
            frm = self._label_frame(self.form_frame, "Dificuldade")
            frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
            cmb = ttk.Combobox(frm, values=DIFF_OPTIONS, state="readonly")
            cmb.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
            cmb.set(value if value in DIFF_OPTIONS else "média")
            cmb.bind("<<ComboboxSelected>>", self._mark_dirty, add="+")
            self.editors[key] = {"type": "dificuldade", "widget": cmb}
            return

        # int -> Entry
        if isinstance(value, int):
            frm = self._label_frame(self.form_frame, key.upper() if key == "id" else key)
            frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
            ent = ttk.Entry(frm)
            ent.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
            ent.insert(0, str(value))
            ent.bind("<KeyRelease>", self._mark_dirty, add="+")
            self.editors[key] = {"type": "int", "widget": ent}
            return

        # str -> Text (2 linhas)
        if isinstance(value, str):
            frm = self._label_frame(self.form_frame, key.capitalize())
            frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
            frm.rowconfigure(0, weight=1)
            txt = tk.Text(frm, height=2, wrap="word")
            txt.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            txt.insert("1.0", value)
            txt.bind("<KeyRelease>", self._mark_dirty, add="+")
            self.editors[key] = {"type": "str", "widget": txt}
            return

        # list -> Text (5 linhas) — 1 item por linha
        if isinstance(value, list):
            frm = self._label_frame(self.form_frame, key.capitalize() + " (uma por linha)")
            frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
            frm.rowconfigure(0, weight=1)
            txt = tk.Text(frm, height=5, wrap="none")
            txt.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            txt.insert("1.0", "\n".join(str(x) for x in value))
            txt.bind("<KeyRelease>", self._mark_dirty, add="+")
            self.editors[key] = {"type": "list", "widget": txt}
            return

        # dict -> “tabela” (duas colunas, 1:3)
        if isinstance(value, dict):
            frm = self._label_frame(self.form_frame, key.capitalize() + " (chave : valor)")
            frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
            # Proporção 1/3 x 2/3 usando pesos uniformes
            frm.columnconfigure(0, weight=1, uniform="cols")
            frm.columnconfigure(1, weight=3, uniform="cols")

            items = list(value.items())  # ordem do JSON preservada
            rows = len(items)

            ttk.Label(frm, text="Chave").grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
            ttk.Label(frm, text="Valor").grid(row=0, column=1, sticky="w", padx=6, pady=(6, 2))

            row_entries: List[Tuple[ttk.Entry, ttk.Entry]] = []
            selected_row = {"idx": -1}  # mutável para fechar sobre as funções

            def _bind_row_focus(idx: int, ek: ttk.Entry, ev: ttk.Entry):
                def _on_focus_in(_evt=None):
                    selected_row["idx"] = idx
                    # habilita o Delete quando há seleção
                    btn_del.state(["!disabled"])
                ek.bind("<FocusIn>", _on_focus_in, add="+")
                ev.bind("<FocusIn>", _on_focus_in, add="+")
                # qualquer edição marca como sujo
                ek.bind("<KeyRelease>", self._mark_dirty, add="+")
                ev.bind("<KeyRelease>", self._mark_dirty, add="+")
            
            # cria as linhas iniciais
            for i in range(rows):
                ek = ttk.Entry(frm)
                ev = ttk.Entry(frm)
                ek.grid(row=i + 1, column=0, sticky="ew", padx=6, pady=2)
                ev.grid(row=i + 1, column=1, sticky="ew", padx=6, pady=2)
                if i < len(items):
                    k, v = items[i]
                    ek.insert(0, str(k))
                    ev.insert(0, str(v))
                _bind_row_focus(i, ek, ev)
                row_entries.append((ek, ev))

            # --- barra de ações (abaixo da tabela) ---
            bar = ttk.Frame(frm)
            # linha logo após as entradas (+1 do cabeçalho, +rows de dados)
            bar.grid(row=rows + 1, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 6))
            bar.columnconfigure(0, weight=0)
            bar.columnconfigure(1, weight=0)
            bar.columnconfigure(2, weight=1)

            btn_field_insert = ttk.Button(bar, text="Insert Line")
            btn_del = ttk.Button(bar, text="Delete Line")

            def _regrid_rows():
                """Reatribui grid das linhas após inserção/remoção e reindexa binds."""
                for i, (ek, ev) in enumerate(row_entries):
                    ek.grid_configure(row=i + 1, column=0)
                    ev.grid_configure(row=i + 1, column=1)
                    # rebinda para ajustar índice correto
                    for seq in ("<FocusIn>",):
                        ek.unbind(seq)
                        ev.unbind(seq)
                    _bind_row_focus(i, ek, ev)
                # reposiciona a barra logo após a última linha
                last = len(row_entries)
                bar.grid_configure(row=last + 1, column=0, columnspan=2)
                # se nada selecionado, desabilita delete
                if selected_row["idx"] < 0 or selected_row["idx"] >= len(row_entries):
                    btn_del.state(["disabled"])

            def _insert_line():
                """Insere linha vazia ao final e seleciona-a."""
                ek = ttk.Entry(frm)
                ev = ttk.Entry(frm)
                row_entries.append((ek, ev))
                ek.grid(row=len(row_entries), column=0, sticky="ew", padx=6, pady=2)
                ev.grid(row=len(row_entries), column=1, sticky="ew", padx=6, pady=2)
                _bind_row_focus(len(row_entries) - 1, ek, ev)
                selected_row["idx"] = len(row_entries) - 1
                btn_del.state(["!disabled"])
                self._mark_dirty()
                _regrid_rows()
                ek.focus_set()

            def _delete_line():
                """Apaga a linha selecionada, se houver."""
                idx = selected_row["idx"]
                if 0 <= idx < len(row_entries):
                    ek, ev = row_entries.pop(idx)
                    try:
                        ek.destroy()
                        ev.destroy()
                    except Exception:
                        pass
                    selected_row["idx"] = -1
                    self._mark_dirty()
                    _regrid_rows()

            btn_field_insert.configure(command=_insert_line)
            btn_del.configure(command=_delete_line)

            # estado inicial: delete desabilitado
            btn_del.state(["disabled"])

            btn_field_insert.grid(row=0, column=0, padx=(0, 6))
            btn_del.grid(row=0, column=1, padx=(0, 6))
            ttk.Label(bar, text=" ").grid(row=0, column=2, sticky="ew")  # expansor

            # registra no dicionário de editores
            self.editors[key] = {"type": "dict", "rows": row_entries}
            return


        # fallback: tratar como string
        frm = self._label_frame(self.form_frame, key.capitalize())
        frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
        frm.rowconfigure(0, weight=1)
        txt = tk.Text(frm, height=2, wrap="word")
        txt.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        txt.insert("1.0", str(value))
        txt.bind("<KeyRelease>", self._mark_dirty, add="+")
        self.editors[key] = {"type": "str", "widget": txt}

    def _render_form_for_question(self, q: Dict[str, Any]):
        """Limpa e recria todos os campos conforme os valores atuais da questão (ordem do JSON)."""
        self._clear_form()

        # ordem exata do JSON (inserção)
        ordered_keys = list(q.keys())
        row = 0
        for k in ordered_keys:
            self._render_field(row, k, q.get(k))
            row += 1

        # espaçador no final para o scroll parar melhor
        ttk.Frame(self.form_frame, height=10).grid(row=row, column=0, sticky="ew")

    # ----------------- coleta e validações -----------------
    def _text_to_lines(self, txt: tk.Text) -> List[str]:
        raw = txt.get("1.0", "end").strip("\n")
        if not raw.strip():
            return []
        return [line.rstrip("\n") for line in raw.splitlines()]

    def _collect_from_editors(self, base: Dict[str, Any]) -> Dict[str, Any]:
        q = dict(base)  # cópia rasa

        for key, info in self.editors.items():
            t = info["type"]

            if t == "dificuldade":
                q[key] = info["widget"].get().strip() or "média"

            elif t == "int":
                s = info["widget"].get().strip()
                if s == "":
                    q[key] = 0
                else:
                    try:
                        q[key] = int(s)
                    except Exception:
                        raise ValueError(f"Campo '{key}': esperado inteiro.")

            elif t == "str":
                txt: tk.Text = info["widget"]
                q[key] = txt.get("1.0", "end").strip()

            elif t == "list":
                txt: tk.Text = info["widget"]
                q[key] = [l for l in self._text_to_lines(txt) if l.strip()]

            elif t == "dict":
                rows = info["rows"]
                d: Dict[str, Any] = {}
                for ek, ev in rows:
                    k = ek.get().strip()
                    v = ev.get().strip()
                    if k:
                        d[k] = v
                if d:
                    q[key] = d
                else:
                    q.pop(key, None)

            else:
                widget = info.get("widget")
                if isinstance(widget, tk.Text):
                    q[key] = widget.get("1.0", "end").strip()
                elif hasattr(widget, "get"):
                    q[key] = widget.get().strip()
                else:
                    q[key] = base.get(key)

        return q

    # ----------------- carga/armazenamento -----------------
    def load_current(self):
        self._loading = True
        try:
            if not self.data:
                self._clear_form()
                self._set_preview("(sem conteúdo)")
                # mantém Raw coerente quando não há dados
                if hasattr(self, "tab_raw") and self.nb.select() == str(self.tab_raw):
                    self._set_raw("(sem conteúdo)")
                return

            q = self.data[self.idx]
            self._render_form_for_question(q)

            self.lbl_pos.configure(text=f"Questão {self.idx + 1} de {len(self.data)}")
            self._populate_dropdown()
            self.var_dirty.set(False)

            # Preview sempre atualizado
            self.update_preview()

            # Se a aba atual for Raw, atualiza também o JSON formatado
            if hasattr(self, "tab_raw") and self.nb.select() == str(self.tab_raw):
                self.update_raw()
        finally:
            self._loading = False


    def collect_form(self) -> Dict[str, Any]:
        if not self.data:
            raise ValueError("Não há questão para salvar.")
        base = self.data[self.idx]
        q = self._collect_from_editors(base)

        # Validações mínimas
        if "id" in q:
            if not isinstance(q["id"], int) or q["id"] < 1:
                raise ValueError("ID inválido (use inteiro >= 1).")
        else:
            raise ValueError("Campo 'id' obrigatório.")

        if "alternativas" in q and not isinstance(q["alternativas"], list):
            raise ValueError("Alternativas deve ser uma lista.")
        if "enunciado" in q and not str(q["enunciado"]).strip():
            raise ValueError("Enunciado não pode ser vazio.")

        # Se usar variáveis/resolucoes, exigir ambos e não vazios
        has_vars = "variaveis" in q
        has_res = "resolucoes" in q
        if has_vars ^ has_res:
            raise ValueError("Quando usar variáveis/resoluções, preencha ambos (variaveis e resolucoes).")
        if has_vars and not q["variaveis"]:
            raise ValueError("Campo 'variaveis' não pode estar vazio quando presente.")
        if has_res and not q["resolucoes"]:
            raise ValueError("Campo 'resolucoes' não pode estar vazio quando presente.")

        if "afirmacoes" in q and not q["afirmacoes"]:
            raise ValueError("Campo 'afirmacoes' não pode estar vazio quando presente.")

        return q

    def _normalize_and_reorder_ids(self):
        self.data.sort(key=lambda x: int(x.get("id", 1)))
        for i, q in enumerate(self.data, start=1):
            q["id"] = i

    def save(self):
        try:
            current = self.collect_form()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Erro de validação:\n{e}", parent=self)
            return

        # Reposiciona conforme novo ID
        try:
            new_pos = int(current["id"]) - 1
        except Exception:
            new_pos = self.idx

        # Aplica edição no item corrente
        self.data[self.idx] = current
        item = self.data.pop(self.idx)
        self.data.insert(max(0, min(new_pos, len(self.data))), item)
        self._normalize_and_reorder_ids()
        self.idx = min(max(0, new_pos), len(self.data) - 1)

        try:
            # Mantém compat: salva lista de questões
            self.json_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.var_dirty.set(False)
            if callable(self.on_saved):
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
        try:
            clone["id"] = int(self.data[self.idx].get("id", 0)) + 1
        except Exception:
            pass
        self.data.insert(self.idx + 1, clone)
        self._normalize_and_reorder_ids()
        self.idx = self.idx + 1
        self.save()

    def new_after_current(self):
        new_id = 1
        if self.data:
            try:
                new_id = int(self.data[self.idx].get("id", 0)) + 1
            except Exception:
                new_id = len(self.data) + 1
        new_q = {
            "id": new_id,
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
    def _set_preview(self, text: str):
        self.txt_preview.configure(state="normal")
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", text or "")
        self.txt_preview.configure(state="disabled")

    def update_preview(self):
        try:
            a = self.collect_form()
            q = load_quiz(a)
        except Exception:
            q = self.data[self.idx]

        # Mostra somente a questão corrente no preview
        try:
            text_core = preview_text([deepcopy(q)], title="Pré-visualização")
            self._set_preview(text_core.strip() or "(sem conteúdo)")
        except Exception as e:
            self._set_preview(f"[preview via core falhou]: {e}")

    def _set_raw(self, text: str):
        self.txt_raw.configure(state="normal")
        self.txt_raw.delete("1.0", "end")
        self.txt_raw.insert("1.0", text or "")
        self.txt_raw.configure(state="disabled")

    def update_raw(self):
        """Renderiza o JSON da questão atual com identação e acentos preservados."""
        try:
            q = self.collect_form()
        except Exception:
            q = self.data[self.idx]
        try:
            raw_text = format_question_json(q)
            self._set_raw(raw_text)
        except Exception as e:
            self._set_raw(f"[raw falhou]: {e}")
            
    def _refresh_field_toolbar(self):
        """Atualiza a combo de campos e o estado do botão Excluir."""
        if not self.data:
            self.cmb_field["values"] = []
            self.cmb_field.set("")
            self.btn_field_delete.state(["disabled"])
            return

        q = self.data[self.idx]
        keys = list(q.keys())
        show_keys = [k for k in keys if k != "id"]  # não permitimos excluir 'id'
        self.cmb_field["values"] = show_keys

        cur = self.cmb_field.get()
        if cur not in show_keys:
            self.cmb_field.set(show_keys[0] if show_keys else "")

        if self.cmb_field.get():
            self.btn_field_delete.state(["!disabled"])
        else:
            self.btn_field_delete.state(["disabled"])
           
    def _insert_field_menu(self):
        """Abre um menu com campos faltantes; ao clicar insere com valor padrão."""
        if not self.data:
            return
        q = self.data[self.idx]
        existing = set(q.keys())

        missing = [k for k in _ALLOWED_FIELDS_DEFAULTS.keys() if k not in existing]
        if not missing:
            messagebox.showinfo(APP_TITLE, "Não há campos disponíveis para inserir.", parent=self)
            return

        menu = tk.Menu(self, tearoff=False)
        for name in missing:
            def _add_field(n=name):
                q[n] = deepcopy(_ALLOWED_FIELDS_DEFAULTS[n])
                self.var_dirty.set(True)
                self._render_form_for_question(q)
                self._refresh_field_toolbar()
                self.cmb_field.set(n)
                self.btn_field_delete.state(["!disabled"])
            menu.add_command(label=name, command=_add_field)

        # Coordenadas do botão (com fallback caso não esteja mapeado ainda)
        try:
            bx = self.btn_field_insert.winfo_rootx()
            by = self.btn_field_insert.winfo_rooty() + self.btn_field_insert.winfo_height()
        except Exception:
            bx = self.winfo_rootx() + 100
            by = self.winfo_rooty() + 80

        try:
            menu.tk_popup(bx, by)
        finally:
            menu.grab_release()

    def _remove_field_selected(self):
        """Remove o campo selecionado na combo (exceto 'id')."""
        if not self.data:
            return
        field = self.cmb_field.get().strip()
        if not field:
            return
        if field == "id":
            messagebox.showwarning(APP_TITLE, "O campo 'id' não pode ser excluído.", parent=self)
            return

        q = self.data[self.idx]
        if field not in q:
            self._refresh_field_toolbar()
            return

        if not messagebox.askyesno(APP_TITLE, f"Remover o campo '{field}' desta questão?", parent=self):
            return

        try:
            q.pop(field, None)
            self.var_dirty.set(True)
            # Recarrega formulário & toolbar
            self._render_form_for_question(q)
            self._refresh_field_toolbar()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Não foi possível remover o campo:\n{e}", parent=self)
            
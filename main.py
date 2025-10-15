"""
GUI responsiva (Tk + ttk) para gerar Beamer a partir de um JSON,
chamando diretamente a função json2beamer.json2beamer(...) do arquivo json2beamer.py.

Ajustes solicitados:
- Log inicia ocupando o MÁXIMO possível, sem comprometer o formulário.
- Log tem altura mínima (5 linhas) e não encolhe abaixo disso.
- Se o formulário crescer, ele usa a scrollbar (não reduz o log abaixo do mínimo).
- Divisória arrastável (PanedWindow). Log somente leitura.

Preferências salvas em ~/.json2beamer_gui.ini
"""

import io
import json
import os
import sys
import threading
import configparser
from pathlib import Path
import subprocess
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import tkinter.font as tkfont

# Importa o gerador local (json2beamer.py na mesma pasta)
# json2beamer.json2beamer(input_json, output_tex, shuffle_seed, title, fsq, fsa, alert_color) -> int
import json2beamer

APP_NAME = "json2beamer – GUI"
INI_PATH = Path.home() / ".json2beamer_gui.ini"

FONT_SIZES = [
    "Huge", "HUGE", "huge",
    "LARGE", "Large", "large",
    "normalsize",
    "small", "footnotesize", "scriptsize", "tiny"
]

DEFAULTS = {
    "title": "Exercícios – Apresentação",
    "fsq": "Large",
    "fsa": "normalsize",
    "alert_color": "red",
    "shuffle_seed": "",
}

def load_prefs():
    cfg = configparser.ConfigParser()
    if INI_PATH.exists():
        try:
            cfg.read(INI_PATH, encoding="utf-8")
            section = cfg["main"]
            return {
                "title": section.get("title", DEFAULTS["title"]),
                "fsq": section.get("fsq", DEFAULTS["fsq"]),
                "fsa": section.get("fsa", DEFAULTS["fsa"]),
                "alert_color": section.get("alert_color", DEFAULTS["alert_color"]),
                "shuffle_seed": section.get("shuffle_seed", DEFAULTS["shuffle_seed"]),
            }
        except Exception:
            pass
    return DEFAULTS.copy()

def save_prefs(values):
    cfg = configparser.ConfigParser()
    cfg["main"] = values
    try:
        with open(INI_PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
    except Exception:
        pass

class ScrollableFrame(ttk.Frame):
    """Frame rolável verticalmente para não cortar conteúdo em janelas pequenas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._inner = ttk.Frame(self._canvas)
        self._inner.bind("<Configure>", self._on_frame_configure)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")

        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)               # Windows
        self._canvas.bind_all("<Button-4>", self._on_mousewheel_linux)           # Linux
        self._canvas.bind_all("<Button-5>", self._on_mousewheel_linux)           # Linux

    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfigure(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")

    @property
    def content(self):
        return self._inner

class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=(10,10,10,6))
        self.master.title(APP_NAME)
        self.master.geometry("980x640")
        self.master.minsize(820, 540)

        self.grid(sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self._style()

        # PanedWindow vertical: topo (form) + base (log) — altura ajustável
        # sashwidth maior para facilitar pegar a divisória
        self.paned = tk.PanedWindow(self, orient="vertical", sashrelief="raised", sashwidth=6)
        self.paned.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Top scrollable (form)
        self.top_container = ttk.Frame(self.paned)
        self.top_container.columnconfigure(0, weight=1)
        self.top_container.rowconfigure(0, weight=1)

        self.scroll = ScrollableFrame(self.top_container)
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.top = self.scroll.content
        self.top.columnconfigure(0, weight=1)

        # Bottom log
        self.bottom = ttk.Frame(self.paned, padding=(0,6,0,0))
        self.bottom.columnconfigure(0, weight=1)
        self.bottom.rowconfigure(1, weight=1)

        self.paned.add(self.top_container)
        self.paned.add(self.bottom)

        # Prefs/vars
        self.prefs = load_prefs()
        self.var_json = tk.StringVar()
        self.var_title = tk.StringVar(value=self.prefs["title"])
        self.var_fsq = tk.StringVar(value=self.prefs["fsq"])
        self.var_fsa = tk.StringVar(value=self.prefs["fsa"])
        self.var_alert = tk.StringVar(value=self.prefs["alert_color"])
        self.var_seed = tk.StringVar(value=self.prefs["shuffle_seed"])
        self.var_output = tk.StringVar(value="")
        self.var_status = tk.StringVar(value="Pronto.")

        self._build_top()
        self._build_bottom()
        self._bind_events()

        # Definir minsize dos panes e posicionamento inicial do sash
        self.after_idle(self._apply_pane_constraints_and_place_sash)

    def _style(self):
        style = ttk.Style()
        for theme in ("vista", "clam", "alt", "default"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("TButton", padding=6)
        style.configure("Accent.TButton", padding=6)
        style.configure("TEntry", padding=4)
        style.configure("TLabel", padding=2)
        style.configure("TCombobox", padding=2)

    # ====== UI Top (form) ======
    def _build_top(self):
        files = ttk.LabelFrame(self.top, text="Arquivo", padding=8)
        files.grid(row=0, column=0, sticky="ew", padx=0, pady=(0,10))
        files.columnconfigure(1, weight=1)

        ttk.Label(files, text="JSON de questões:").grid(row=0, column=0, sticky="w")
        ttk.Entry(files, textvariable=self.var_json).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(files, text="Procurar…", command=self.browse_json).grid(row=0, column=2, padx=4)

        out = ttk.LabelFrame(self.top, text="Saída", padding=8)
        out.grid(row=1, column=0, sticky="ew", pady=(0,10))
        out.columnconfigure(1, weight=1)
        ttk.Label(out, text="Arquivo .tex de saída:").grid(row=0, column=0, sticky="w", padx=(6,2), pady=6)
        ttk.Entry(out, textvariable=self.var_output, state="readonly").grid(row=0, column=1, sticky="ew", padx=(0,6), pady=6)
        ttk.Button(out, text="Abrir Pasta", command=self.open_output_dir).grid(row=0, column=2, padx=(0,6))

        opts = ttk.LabelFrame(self.top, text="Opções", padding=8)
        opts.grid(row=2, column=0, sticky="ew")
        for c in range(6):
            opts.columnconfigure(c, weight=(1 if c in (1,3,5) else 0))

        ttk.Label(opts, text="Título:").grid(row=0, column=0, sticky="w", padx=(6,2), pady=6)
        ttk.Entry(opts, textvariable=self.var_title).grid(row=0, column=1, columnspan=5, sticky="ew", padx=(0,6))

        ttk.Label(opts, text="Fonte Enunciado (fsq):").grid(row=1, column=0, sticky="w", padx=(6,2), pady=6)
        ttk.Combobox(opts, values=FONT_SIZES, textvariable=self.var_fsq, state="readonly")\
            .grid(row=1, column=1, sticky="ew", padx=(0,12))

        ttk.Label(opts, text="Fonte Alternativas (fsa):").grid(row=1, column=2, sticky="w", padx=(6,2))
        ttk.Combobox(opts, values=FONT_SIZES, textvariable=self.var_fsa, state="readonly")\
            .grid(row=1, column=3, sticky="ew", padx=(0,12))

        ttk.Label(opts, text="Cor do \\alert{…}:").grid(row=1, column=4, sticky="w", padx=(6,2))
        frm_color = ttk.Frame(opts)
        frm_color.grid(row=1, column=5, sticky="ew")
        ttk.Entry(frm_color, textvariable=self.var_alert).pack(side="left", fill="x", expand=True)
        ttk.Button(frm_color, text="🎨", width=3, command=self.pick_color).pack(side="left", padx=(6,0))

        ttk.Label(opts, text="Seed de Embaralhamento (opcional):").grid(row=2, column=0, sticky="w", padx=(6,2), pady=(0,8))
        ttk.Entry(opts, textvariable=self.var_seed).grid(row=2, column=1, sticky="ew", padx=(0,12), pady=(0,8))
        ttk.Label(opts, text="(vazio = aleatório a cada execução)").grid(row=2, column=2, columnspan=4, sticky="w", pady=(0,8))

        actions = ttk.Frame(self.top, padding=(0,8,0,0))
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="Gerar .tex", command=self.on_run, style="Accent.TButton").grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Gerar PDF", command=self.on_run_pdf, style="Accent.TButton").grid(row=0, column=1, padx=8, sticky="w")
        ttk.Button(actions, text="Salvar Preferências", command=self.on_save).grid(row=0, column=2, padx=8, sticky="w")

        # --- NEW: botão para abrir o editor de questões ---
        ttk.Button(actions, text="Revisar/Editar Questões…", command=self.open_editor).grid(row=0, column=3, padx=8, sticky="w")

    # ====== UI Bottom (log) ======
    def _build_bottom(self):
        ttk.Label(self.bottom, text="Log").grid(row=0, column=0, sticky="w")

        # LOG somente leitura; altura min controlada por pane minsize (5 linhas)
        self.txt_log = tk.Text(self.bottom, height=5, wrap="word", undo=False)
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=(0,0), pady=6)
        vbar = ttk.Scrollbar(self.bottom, orient="vertical", command=self.txt_log.yview)
        vbar.grid(row=1, column=1, sticky="ns", pady=6)
        self.txt_log.configure(yscrollcommand=vbar.set)

        self.txt_log.configure(state="disabled")
        self.txt_log.bind("<Key>", lambda e: "break")
        self.txt_log.bind("<Control-v>", lambda e: "break")
        self.txt_log.bind("<Button-2>", lambda e: "break")

        # Menu de contexto (copiar)
        self._log_menu = tk.Menu(self.txt_log, tearoff=0)
        self._log_menu.add_command(label="Copiar", command=lambda: self.txt_log.event_generate("<<Copy>>"))
        self._log_menu.add_command(label="Copiar tudo", command=self._copy_all_log)
        self.txt_log.bind("<Button-3>", self._show_log_menu)

        # Status bar
        status = ttk.Frame(self.bottom)
        status.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(status, textvariable=self.var_status).grid(row=0, column=0, sticky="w")

    # ====== constraints e sash ======
    def _apply_pane_constraints_and_place_sash(self):
        """Define minsize dos panes e posiciona o sash para maximizar o log sem esconder o form."""
        # Altura mínima do LOG = 5 linhas reais do Text
        try:
            f = tkfont.nametofont(self.txt_log.cget("font"))
            line_h = max(14, f.metrics("linespace"))   # fallback mínimo visual
        except Exception:
            line_h = 16
        log_min_px = int(line_h * 5 + 24)   # 5 linhas + margens/scrollbar

        # Altura mínima do FORM (topo) – suficiente p/ ver os controles principais
        top_min_px = 400  # você pode ajustar; top tem scroll se faltar espaço

        # Aplicar minsize nos panes
        self.paned.paneconfigure(self.bottom, minsize=log_min_px)
        self.paned.paneconfigure(self.top_container, minsize=top_min_px)

        # Calcular posição do sash:
        self.update_idletasks()
        total_h = max(0, self.winfo_height())

        # Altura "necessária" do topo (tamanho do conteúdo, mas com scroll se passar)
        top_req = self.top_container.winfo_reqheight()
        # Não deixar o topo menor que top_min_px, nem maior que total_h - log_min_px
        sash_y = max(top_min_px, min(top_req, total_h - log_min_px - 8))
        # Posicionar: topo fica na altura requerida, e o restante é do log
        try:
            self.paned.sash_place(0, 0, sash_y)
        except Exception:
            pass

        # Ao redimensionar a janela, manter o log no máximo possível sem violar minsize
        def _on_resize(_evt=None):
            self.update_idletasks()
            total = max(0, self.winfo_height())
            top_req2 = self.top_container.winfo_reqheight()
            sash = max(top_min_px, min(top_req2, total - log_min_px - 8))
            try:
                self.paned.sash_place(0, 0, sash)
            except Exception:
                pass

        # Vincula no container principal (uma vez)
        if not hasattr(self, "_resize_bound"):
            self.bind("<Configure>", _on_resize)
            self._resize_bound = True

    # ====== binds util ======
    def _show_log_menu(self, event):
        try:
            self._log_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._log_menu.grab_release()

    def _copy_all_log(self):
        self.txt_log.configure(state="normal")
        try:
            self.txt_log.tag_add("sel", "1.0", "end-1c")
            self.txt_log.event_generate("<<Copy>>")
            self.txt_log.tag_remove("sel", "1.0", "end")
        finally:
            self.txt_log.configure(state="disabled")

    def _bind_events(self):
        for w in (self, self.top_container, self.bottom, self.top):
            w.grid_propagate(True)
        self.var_json.trace_add("write", lambda *_: self.update_output_path())

    # ====== utils ======
    def pick_color(self):
        _, hexcolor = colorchooser.askcolor()
        if hexcolor:
            self.var_alert.set(hexcolor)

    def browse_json(self):
        p = filedialog.askopenfilename(
            title="Escolher JSON de questões",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        if p:
            self.var_json.set(p)
            self.update_output_path()

    def update_output_path(self):
        j = self.var_json.get().strip()
        if not j:
            self.var_output.set("")
            return
        jpath = Path(j)
        out = jpath.with_name(jpath.stem + "_slides.tex")
        self.var_output.set(str(out))

    def open_output_dir(self):
        out = self.var_output.get().strip()
        if not out:
            return
        folder = str(Path(out).resolve().parent)
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore
            elif sys.platform == "darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Não foi possível abrir a pasta:\n{e}")

    # ====== log ======
    def log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        self.txt_log.configure(state="normal")
        try:
            self.txt_log.insert("end", line)
            self.txt_log.see("end")
        finally:
            self.txt_log.configure(state="disabled")

    # ====== execução ======
    def validate_inputs(self):
        json_in = self.var_json.get().strip()
        if not json_in:
            messagebox.showerror(APP_NAME, "Selecione o arquivo JSON de questões.")
            return False
        if not Path(json_in).exists():
            messagebox.showerror(APP_NAME, "O arquivo JSON indicado não existe.")
            return False
        try:
            with open(json_in, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("O JSON deve ser um array de questões.")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"JSON inválido:\n{e}")
            return False
        return True

    def on_run(self):
        if not self.validate_inputs():
            return

        json_in = self.var_json.get().strip()
        out = self.var_output.get().strip()
        title = self.var_title.get().strip() or DEFAULTS["title"]
        fsq = self.var_fsq.get().strip() or DEFAULTS["fsq"]
        fsa = self.var_fsa.get().strip() or DEFAULTS["fsa"]
        alert = self.var_alert.get().strip() or DEFAULTS["alert_color"]
        seed = self.var_seed.get().strip() or None

        self.var_status.set("Gerando .tex…")
        self.log(f"Iniciando geração para: {json_in}")

        t = threading.Thread(
            target=self._run_json2beamer,
            args=(json_in, out, seed, title, fsq, fsa, alert),
            daemon=True
        )
        t.start()
        
    def on_run_pdf(self):
        if not self.validate_inputs():
            return
        import shutil
        if shutil.which("pdflatex") is None:
            messagebox.showerror(APP_NAME, "pdflatex não encontrado no PATH. Verifique a instalação do LaTeX.")
            return
        json_in = self.var_json.get().strip()
        out_tex = self.var_output.get().strip()
        title = self.var_title.get().strip() or DEFAULTS["title"]
        fsq = self.var_fsq.get().strip() or DEFAULTS["fsq"]
        fsa = self.var_fsa.get().strip() or DEFAULTS["fsa"]
        alert = self.var_alert.get().strip() or DEFAULTS["alert_color"]
        seed = self.var_seed.get().strip() or None
        self.var_status.set("Gerando .tex e compilando PDF…")
        self.log(f"Iniciando geração e compilação para: {json_in}")
        t = threading.Thread(
            target=self._run_json2beamer_and_pdflatex,
            args=(json_in, out_tex, seed, title, fsq, fsa, alert),
            daemon=True
        )
        t.start()

    def _run_json2beamer_and_pdflatex(self, json_in, out_tex, seed, title, fsq, fsa, alert):
        import io, sys, subprocess
        old_stdout = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = json2beamer.json2beamer(
                input_json=json_in,
                output_tex=out_tex,
                shuffle_seed=seed,
                title=title,
                fsq=fsq,
                fsa=fsa,
                alert_color=alert
            )
        except Exception as e:
            sys.stdout = old_stdout
            self.var_status.set("Erro.")
            self.log(f"❌ Erro gerando .tex: {e}")
            return
        sys.stdout = old_stdout
        out_text = buf.getvalue().strip()
        if out_text:
            self.log(out_text)
        if rc != 0:
            self.var_status.set("Falhou ao gerar .tex (veja o log).")
            self.log(f"❌ Retorno: {rc}")
            return
        self.log(f"✅ .tex gerado: {out_tex}")
        try:
            tex_path = Path(out_tex).resolve()
            workdir = tex_path.parent
            pdf_name = tex_path.with_suffix(".pdf").name
            cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
            for i in range(2):
                self.log(f"Compilando (passagem {i+1}/2)…")
                proc = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)
                if proc.stdout:
                    self.log(proc.stdout.strip())
                if proc.returncode != 0:
                    if proc.stderr:
                        self.log(proc.stderr.strip())
                    raise RuntimeError(f"pdflatex retornou código {proc.returncode}")
            pdf_path = workdir / pdf_name
            if pdf_path.exists():
                self.var_status.set("PDF gerado com sucesso.")
                self.log(f"✅ PDF gerado em: {pdf_path}")
            else:
                self.var_status.set("Compilação terminou, mas o PDF não foi localizado.")
                self.log("⚠️ pdflatex executou, mas o arquivo .pdf não foi encontrado.")
        except Exception as e:
            self.var_status.set("Erro na compilação do PDF.")
            self.log(f"❌ Erro no pdflatex: {e}")

    def on_save(self):
        """Salva preferências do formulário no ~/.json2beamer_gui.ini."""
        values = {
            "title": self.var_title.get().strip(),
            "fsq": self.var_fsq.get().strip(),
            "fsa": self.var_fsa.get().strip(),
            "alert_color": self.var_alert.get().strip(),
            "shuffle_seed": self.var_seed.get().strip(),
        }
        save_prefs(values)
        self.log(f"Preferências salvas em {INI_PATH}")
        self.var_status.set("Preferências salvas.")

    def _run_json2beamer(self, json_in, out, seed, title, fsq, fsa, alert):
        old_stdout = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = json2beamer.json2beamer(
                input_json=json_in,
                output_tex=out,
                shuffle_seed=seed,
                title=title,
                fsq=fsq,
                fsa=fsa,
                alert_color=alert
            )
        except Exception as e:
            sys.stdout = old_stdout
            self.var_status.set("Erro.")
            self.log(f"❌ Erro: {e}")
            return
        sys.stdout = old_stdout

        out_text = buf.getvalue().strip()
        if out_text:
            self.log(out_text)
        if rc == 0:
            self.var_status.set("Concluído com sucesso.")
            self.log(f"✅ Arquivo gerado em: {out}")
        else:
            self.var_status.set("Falhou (veja o log).")
            self.log(f"❌ Retorno: {rc}")

    # --- NEW: handler do botão de edição ---
    def open_editor(self):
        path = self.var_json.get().strip()
        if not path:
            messagebox.showwarning(APP_NAME, "Selecione primeiro o arquivo JSON de questões.")
            return
        if not Path(path).exists():
            messagebox.showerror(APP_NAME, "O arquivo JSON indicado não existe.")
            return
        try:
            import question_editor
            question_editor.QuestionEditor(self.master, path, on_saved=lambda: self.log("JSON atualizado pelo editor."))
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Não foi possível abrir o editor:\n{e}")

def main():
    root = tk.Tk()

    # FIX Windows: configure fontes padrão (evita "expected integer but got 'UI'")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
        try:
            f = tkfont.nametofont(name)
            f.configure(family="Segoe UI", size=10)
        except tk.TclError:
            pass

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
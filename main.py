
# -*- coding: utf-8 -*-
"""
Ponto de entrada da aplicação.
Responsabilidade: criar Tk() e instanciar a janela principal.
"""
import tkinter as tk
import tkinter.font as tkfont
from gui.app_window import App

def main():
    root = tk.Tk()
    # Ajuste de fontes padrão (Windows)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
        try:
            f = tkfont.nametofont(name)
            f.configure(family="Segoe UI", size=10)
        except Exception:
            pass
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()

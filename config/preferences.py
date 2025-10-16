# -*- coding: utf-8 -*-
"""
Carregar/salvar preferências da GUI.
Melhoria: procura o INI no diretório atual do projeto (config.ini, json2beamer.ini, .json2beamer_gui.ini)
e, se não encontrar, usa o arquivo na HOME (~/.json2beamer_gui.ini). O caminho efetivo pode ser obtido
por get_ini_path().
"""
import configparser
from pathlib import Path
from typing import Dict

APP_NAME = "json2beamer – GUI"

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

_INI_PATH = None  # type: ignore

def get_ini_path() -> Path:
    """Retorna o caminho do INI que será usado (detecta uma vez e memoriza)."""
    global _INI_PATH
    if _INI_PATH is not None:
        return _INI_PATH

    # 1) procurar no diretório atual (onde o app está sendo executado)
    cwd = Path.cwd()
    candidates = [
        cwd / "config.ini",
        cwd / "json2beamer.ini",
        cwd / ".json2beamer_gui.ini",
    ]
    for c in candidates:
        if c.exists():
            _INI_PATH = c
            return _INI_PATH

    # 2) se não existir, usar HOME
    _INI_PATH = Path.home() / ".json2beamer_gui.ini"
    return _INI_PATH

def load_prefs():
    """Carrega preferências do INI detectado ou usa DEFAULTS."""
    path = get_ini_path()
    cfg = configparser.ConfigParser()
    if path.exists():
        try:
            cfg.read(path, encoding="utf-8")
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
    """Salva preferências no INI detectado (cria se necessário)."""
    cfg = configparser.ConfigParser()
    cfg["main"] = values
    path = get_ini_path()
    with open(path, "w", encoding="utf-8") as f:
        cfg.write(f)

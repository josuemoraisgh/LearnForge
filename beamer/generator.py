from pathlib import Path
from core.parsers import load_jsons, to_ir
from beamer.renderer import render_quiz

def jsons_to_tex(json_paths, out_tex, *, title, fsq, fsa):
    raw = load_jsons(json_paths)
    quiz = to_ir(raw, title=title)
    tex = render_quiz(quiz, title=title, fsq=fsq, fsa=fsa)
    Path(out_tex).write_text(tex, encoding="utf-8")
    return 0

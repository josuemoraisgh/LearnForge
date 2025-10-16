from core.parsers import load_jsons, to_ir
from testgen.renderer import render_to_docx

def jsons_to_docx(json_paths, template, out_docx, *, title, placeholder="{{QUESTOES}}"):
    raw = load_jsons(json_paths)
    quiz = to_ir(raw, title=title)
    render_to_docx(quiz, template, out_docx, placeholder=placeholder)
    return 0

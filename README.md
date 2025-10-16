
# json2beamer_app – divisão por SRP

Estrutura criada para separar responsabilidades (Single Responsibility Principle).

- `core/` – geração de LaTeX/Beamer (puro, testável)
- `gui/` – interface Tk/ttk
- `editor/` – janela do editor e widgets auxiliares
- `config/` – preferências (.ini)

Execute com:

```bash
python -m json2beamer_app.main
```

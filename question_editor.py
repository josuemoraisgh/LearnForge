# question_editor.py
# -*- coding: utf-8 -*-
"""
Editor de questões (Tk + ttk) com:
- Abas: Formulário / Preview
- Campo ID (editável) e Tipo (1..4) logo após
- Botões: Nova questão • Salvar (Ctrl+S) • Clonar • Excluir
- OBS textarea (array de strings, 1 linha = 1 item)
- Preview: "id) enunciado", alternativas a), b), c) (a = correta, apenas visual),
  sem "Correta:", e bloco final "OBS.:" com linhas.
- Inserção após a atual e renumeração 1..N; mudança de ID reordena e renumera.
- Tipo controla painéis (3=variáveis/resoluções, 4=afirmações).
"""

import json, re, tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from copy import deepcopy
APP_TITLE = "Editor de Questões (JSON)"
ALPH = "abcdefghijklmnopqrstuvwxyz"

TOKEN = re.compile(r'\s*(?:(\d+(?:\.\d*)?|\.\d+)|([+\-*/()]))')
class SafeEval:
    def parse(self, expr):
        self.tokens = TOKEN.findall(expr); self.pos = 0; return self._expr()
    def _peek(self):
        if self.pos >= len(self.tokens): return None, None
        n, op = self.tokens[self.pos]; return (n or ''), (op or '')
    def _eat_number(self):
        n,_ = self._peek()
        if n: self.pos+=1; return float(n)
        raise ValueError('Número esperado')
    def _eat_op(self,ch=None):
        _,op = self._peek()
        if op and (ch is None or op==ch): self.pos+=1; return op
        raise ValueError(f"Operador '{ch}' esperado")
    def _factor(self):
        n,op = self._peek()
        if n: return self._eat_number()
        if op=='(':
            self._eat_op('('); v=self._expr(); self._eat_op(')'); return v
        if op in '+-':
            self.pos+=1; v=self._factor(); return v if op=='+' else -v
        raise ValueError('Fator inválido')
    def _term(self):
        v=self._factor()
        while True:
            _,op=self._peek()
            if op=='*': self._eat_op('*'); v*=self._factor()
            elif op=='/': self._eat_op('/'); d=self._factor(); 
            elif op not in '*/': break
            if op=='/':
                d=self._factor()
                if d==0: raise ZeroDivisionError('Divisão por zero')
                v/=d
        return v
    def _expr(self):
        v=self._term()
        while True:
            _,op=self._peek()
            if op=='+': self._eat_op('+'); v+=self._term()
            elif op=='-': self._eat_op('-'); v-=self._term()
            else: break
        return v
def safe_eval(expr:str)->float: return SafeEval().parse(expr)

def ensure_lists(item):
    item.setdefault('imagens', [])
    item.setdefault('alternativas', [])
    item.setdefault('correta', '')
    item.setdefault('obs', [])
def tipo_of(q:dict)->int:
    t=q.get('tipo',None)
    if isinstance(t,int) and t in (1,2,3,4): return t
    if 'variaveis' in q or 'resolucoes' in q: return 3
    if 'afirmacoes' in q: return 4
    alts=q.get('alternativas') or []
    if any(isinstance(a,str) and a.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp','.svg')) for a in alts): return 2
    return 1

class KVTable(ttk.Frame):
    def __init__(self, master, columns, widths=None):
        super().__init__(master); self.columns=columns; self.widths=widths or [120]*len(columns)
        self.tree=ttk.Treeview(self, columns=columns, show='headings', height=6, selectmode='browse')
        for c,w in zip(columns,self.widths): self.tree.heading(c,text=c); self.tree.column(c,width=w,stretch=True)
        vsb=ttk.Scrollbar(self, orient='vertical', command=self.tree.yview); self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0,column=0,sticky='nsew'); vsb.grid(row=0,column=1,sticky='ns')
        self.grid_rowconfigure(0,weight=1); self.grid_columnconfigure(0,weight=1)
        tb=ttk.Frame(self); tb.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(4,0))
        ttk.Button(tb,text='+',width=3,command=self.add_row).pack(side='left')
        ttk.Button(tb,text='−',width=3,command=self.del_row).pack(side='left')
        self._edit_var=None; self._edit_ent=None
        self.tree.bind('<Double-1>', self._on_dclick)
        self.tree.bind('<F2>', self._on_f2)
        self.tree.bind('<Return>', self._on_return_edit)
    def set_data(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows: self.tree.insert('', 'end', values=r)
    def get_data(self):
        out=[]; 
        for iid in self.tree.get_children(): out.append(self.tree.item(iid,'values'))
        return out
    def add_row(self): self.tree.insert('', 'end', values=('','','')); self.event_generate('<<KVTableEdited>>')
    def del_row(self):
        sel=self.tree.selection()
        if sel: self.tree.delete(sel[0]); self.event_generate('<<KVTableEdited>>')
    def _on_f2(self,_=None):
        sel=self.tree.selection()
        if not sel: return
        self._begin_edit(sel[0],0)
    def _on_return_edit(self,_=None):
        if self._edit_ent is not None: self._commit_edit()
        else: self._on_f2()
    def _on_dclick(self,evt):
        iid=self.tree.identify_row(evt.y); col=self.tree.identify_column(evt.x)
        if not iid or not col: return
        self._begin_edit(iid, int(col[1:])-1)
    def _begin_edit(self,iid,col_idx):
        if self._edit_ent is not None: self._commit_edit()
        bbox=self.tree.bbox(iid, f'#{col_idx+1}')
        if not bbox: return
        x,y,w,h=bbox; vals=list(self.tree.item(iid,'values')); cur=vals[col_idx] if col_idx<len(vals) else ''
        self._edit_var=tk.StringVar(value=cur); self._edit_ent=ttk.Entry(self.tree,textvariable=self._edit_var)
        self._edit_ent.place(x=x,y=y,width=w,height=h); self._edit_ent.focus(); self._edit_ent.icursor(tk.END)
        self._edit_ent.bind('<Return>', lambda e: self._commit_edit())
        self._edit_ent.bind('<Escape>', lambda e: self._cancel_edit())
        self._edit_ent.bind('<FocusOut>', lambda e: self._commit_edit())
        self._edit_iid=iid; self._edit_col=col_idx
    def _commit_edit(self):
        if self._edit_ent is None: return
        newv=self._edit_var.get(); vals=list(self.tree.item(self._edit_iid,'values'))
        while len(vals)<len(self.columns): vals.append('')
        vals[self._edit_col]=newv; self.tree.item(self._edit_iid, values=tuple(vals))
        self._edit_ent.destroy(); self._edit_ent=None; self.event_generate('<<KVTableEdited>>')
    def _cancel_edit(self):
        if self._edit_ent is not None: self._edit_ent.destroy(); self._edit_ent=None

class QuestionEditor(tk.Toplevel):
    def __init__(self, master, json_path, on_saved=None):
        super().__init__(master); self.title(APP_TITLE); self.geometry('1100x720'); self.minsize(900,600)
        self.json_path=Path(json_path); self.on_saved=on_saved; self._loading=False
        try:
            self.data=json.loads(self.json_path.read_text(encoding='utf-8'))
            if not isinstance(self.data,list): raise ValueError('JSON não é um array de questões.')
        except Exception as e:
            messagebox.showerror(APP_TITLE, f'Erro ao abrir JSON:\n{e}', parent=self); self.destroy(); return
        self.idx=0; self.var_dirty=tk.BooleanVar(value=False)
        self.columnconfigure(0,weight=1); self.rowconfigure(1,weight=1)
        self._build_topbar(); self._build_notebook()
        self.bind('<Left>', lambda e: self.prev()); self.bind('<Right>', lambda e: self.next())
        self.bind('<Control-s>', lambda e: self.save()); self.protocol('WM_DELETE_WINDOW', self._on_close)
        self.load_current()

    def _build_topbar(self):
        bar=ttk.Frame(self,padding=6); bar.grid(row=0,column=0,sticky='ew'); bar.columnconfigure(3,weight=1)
        ttk.Button(bar,text='◀',width=3,command=self.prev).grid(row=0,column=0,padx=(0,4))
        ttk.Button(bar,text='▶',width=3,command=self.next).grid(row=0,column=1,padx=(0,10))
        ttk.Label(bar,text='Ir para questão:').grid(row=0,column=2,sticky='e')
        self.cmb_go=ttk.Combobox(bar,state='readonly',width=40); self.cmb_go.grid(row=0,column=3,sticky='ew',padx=(6,10))
        self.cmb_go.bind('<<ComboboxSelected>>', self.on_go_selected)
        ttk.Button(bar,text='Novo',command=self.new_after_current).grid(row=0,column=4,padx=4)
        ttk.Button(bar,text='Salvar (Ctrl+S)',command=self.save).grid(row=0,column=5,padx=4)
        ttk.Button(bar,text='Clonar',command=self.clone_current).grid(row=0,column=6,padx=4)
        ttk.Button(bar,text='Excluir',command=self.delete_current).grid(row=0,column=7,padx=4)
        self.lbl_pos=ttk.Label(bar,text='—'); self.lbl_pos.grid(row=0,column=8,padx=(10,0))

    def _build_notebook(self):
        self.nb=ttk.Notebook(self); self.nb.grid(row=1,column=0,sticky='nsew')
        self.tab_form=ttk.Frame(self.nb); self.nb.add(self.tab_form,text='Formulário')
        self.tab_prev=ttk.Frame(self.nb); self.nb.add(self.tab_prev,text='Preview')
        left=self.tab_form; left.columnconfigure(1,weight=1); r=0
        ttk.Label(left,text='ID:').grid(row=r,column=0,sticky='w'); self.ent_id=ttk.Entry(left,width=10)
        self.ent_id.grid(row=r,column=1,sticky='w'); r+=1
        ttk.Label(left,text='Tipo (1/2/3/4):').grid(row=r,column=0,sticky='w')
        self.cmb_tipo=ttk.Combobox(left,values=['1','2','3','4'],state='readonly',width=6)
        self.cmb_tipo.grid(row=r,column=1,sticky='w'); r+=1
        ttk.Label(left,text='Dificuldade:').grid(row=r,column=0,sticky='w')
        self.cmb_diff=ttk.Combobox(left,values=['fácil','média','difícil'],state='readonly')
        self.cmb_diff.grid(row=r,column=1,sticky='ew'); r+=1
        ttk.Label(left,text='Enunciado:').grid(row=r,column=0,sticky='nw')
        self.txt_enun=tk.Text(left,height=2,wrap='word'); self.txt_enun.grid(row=r,column=1,sticky='nsew'); left.rowconfigure(r,weight=1); r+=1
        ttk.Label(left,text='Imagens (uma por linha):').grid(row=r,column=0,sticky='nw')
        self.txt_imgs=tk.Text(left,height=3,wrap='none'); self.txt_imgs.grid(row=r,column=1,sticky='ew'); r+=1
        ttk.Label(left,text='Alternativas (uma por linha):').grid(row=r,column=0,sticky='nw')
        self.txt_alts=tk.Text(left,height=10,wrap='word'); self.txt_alts.grid(row=r,column=1,sticky='nsew'); left.rowconfigure(r,weight=2); r+=1
        ttk.Label(left,text='Correta:').grid(row=r,column=0,sticky='w')
        self.ent_correct=ttk.Entry(left); self.ent_correct.grid(row=r,column=1,sticky='ew'); r+=1
        self.frm_tipo3=ttk.LabelFrame(left,text='Tipo 3 – Variáveis & Resoluções'); self.frm_tipo3.columnconfigure(0,weight=1)
        ttk.Label(self.frm_tipo3,text='Variáveis (VAR, min, max, step)').grid(row=0,column=0,sticky='w')
        self.tbl_vars=KVTable(self.frm_tipo3,columns=['VAR','min','max','step'],widths=[120,90,90,70])
        self.tbl_vars.grid(row=1,column=0,sticky='nsew',pady=(0,6))
        ttk.Label(self.frm_tipo3,text='Resoluções (NOME, expressão)').grid(row=2,column=0,sticky='w')
        self.tbl_res=KVTable(self.frm_tipo3,columns=['NOME','expressao'],widths=[140,320])
        self.tbl_res.grid(row=3,column=0,sticky='nsew')
        self.frm_tipo3.grid(row=r,column=0,columnspan=2,sticky='nsew',pady=(8,0)); r+=1
        self.frm_tipo4=ttk.LabelFrame(left,text='Tipo 4 – Afirmações'); self.frm_tipo4.columnconfigure(0,weight=1)
        ttk.Label(self.frm_tipo4,text='Afirmações (chave, texto)').grid(row=0,column=0,sticky='w')
        self.tbl_aff=KVTable(self.frm_tipo4,columns=['CHAVE','TEXTO'],widths=[80,380])
        self.tbl_aff.grid(row=1,column=0,sticky='nsew')
        self.frm_tipo4.grid(row=r,column=0,columnspan=2,sticky='nsew',pady=(8,0)); r+=1
        ttk.Label(left,text='Observações (uma linha por item):').grid(row=r,column=0,sticky='nw')
        self.txt_obs=tk.Text(left,height=4,wrap='word'); self.txt_obs.grid(row=r,column=1,sticky='ew'); r+=1
        right=self.tab_prev; right.columnconfigure(0,weight=1); right.rowconfigure(2,weight=1)
        self.frm_sim=ttk.LabelFrame(right,text='Simular parâmetros (Tipo 3)'); self.frm_sim.grid(row=0,column=0,sticky='ew',pady=(4,8)); self.frm_sim.columnconfigure(0,weight=1)
        self.btn_update_preview=ttk.Button(right,text='Atualizar Preview',command=self.update_preview); self.btn_update_preview.grid(row=1,column=0,sticky='w')
        self.txt_preview=tk.Text(right,height=24,wrap='word',state='disabled'); self.txt_preview.grid(row=2,column=0,sticky='nsew')
        self.tbl_vars.bind('<<KVTableEdited>>', lambda e: self._mark_dirty(), add='+')
        self.tbl_res.bind('<<KVTableEdited>>', lambda e: self._mark_dirty(), add='+')
        self.tbl_aff.bind('<<KVTableEdited>>', lambda e: self._mark_dirty(), add='+')
        self.nb.bind('<<NotebookTabChanged>>', lambda e: (self.update_preview() if self.nb.select()==str(self.tab_prev) else None))

    def _on_close(self):
        if self.var_dirty.get():
            if not messagebox.askyesno(APP_TITLE,'Há alterações não salvas. Deseja descartar?', parent=self): return
        self.destroy()
    def _confirm_unsaved(self):
        if self.var_dirty.get(): return messagebox.askyesno(APP_TITLE,'Há alterações não salvas. Deseja descartar?', parent=self)
        return True
    def _mark_dirty(self,*_):
        if getattr(self,'_loading',False): return
        self.var_dirty.set(True)
    def _populate_dropdown(self):
        items=[f"{q.get('id')} – {q.get('enunciado','')[:40].replace('\n',' ')}" for q in self.data]
        self.cmb_go['values']=items
        if items: self.cmb_go.current(self.idx)
    def on_go_selected(self,_=None):
        new_idx=self.cmb_go.current()
        if new_idx!=-1 and new_idx!=self.idx:
            if not self._confirm_unsaved(): self._populate_dropdown(); return
            self.idx=new_idx; self.load_current()

    def prev(self):
        if self.idx<=0: return
        if not self._confirm_unsaved(): return
        self.idx-=1; self.load_current()
    def next(self):
        if self.idx>=len(self.data)-1: return
        if not self._confirm_unsaved(): return
        self.idx+=1; self.load_current()

    def _set_text(self, txt: tk.Text, content: str):
        txt.configure(state='normal'); txt.delete('1.0','end'); txt.insert('1.0', content or ''); txt.configure(state='normal')
    def _get_lines(self, txt: tk.Text):
        raw=txt.get('1.0','end').strip(); return [line for line in raw.splitlines()] if raw else []

    def load_current(self):
        self._loading=True
        try:
            q=self.data[self.idx]; ensure_lists(q)
            self.ent_id.delete(0,'end'); self.ent_id.insert(0, str(q.get('id','')))
            self.cmb_tipo.set(str(tipo_of(q))); self.cmb_diff.set(q.get('dificuldade','média'))
            self._set_text(self.txt_enun, q.get('enunciado','')); self._set_text(self.txt_imgs, '\n'.join(q.get('imagens') or []))
            self._set_text(self.txt_alts, '\n'.join(q.get('alternativas') or [])); self.ent_correct.delete(0,'end'); self.ent_correct.insert(0, q.get('correta',''))
            self._set_text(self.txt_obs, '\n'.join(q.get('obs') or []))
            self._toggle_panels(int(self.cmb_tipo.get()))
            self.build_sim_controls(q if int(self.cmb_tipo.get())==3 else None)
            self.lbl_pos.configure(text=f'Questão {self.idx+1} de {len(self.data)}')
            self._populate_dropdown(); self.var_dirty.set(False)
            self.cmb_tipo.bind('<<ComboboxSelected>>', self._on_tipo_changed, add='+')
            self.cmb_diff.bind('<<ComboboxSelected>>', self._mark_dirty, add='+')
            for txt in (self.txt_enun,self.txt_imgs,self.txt_alts,self.txt_obs): txt.bind('<KeyRelease>', self._mark_dirty, add='+')
            self.ent_correct.bind('<KeyRelease>', self._mark_dirty, add='+')
            self.ent_id.bind('<FocusOut>', lambda e: self._on_id_focusout(), add='+'); self.ent_id.bind('<Return>', lambda e: self._on_id_focusout(), add='+')
            self.update_preview()
        finally:
            self._loading=False

    def _toggle_panels(self,t:int):
        if t==3: self.frm_tipo3.grid()
        else: self.frm_tipo3.grid_remove()
        if t==4: self.frm_tipo4.grid()
        else: self.frm_tipo4.grid_remove()
    def _on_tipo_changed(self,_=None):
        try: t=int(self.cmb_tipo.get())
        except Exception: t=tipo_of(self.data[self.idx])
        self._toggle_panels(t); self._mark_dirty()
    def _on_id_focusout(self): self._mark_dirty()

    def collect_form(self):
        q=self.data[self.idx]
        try:
            new_id=int(self.ent_id.get().strip())
            if new_id<1: raise ValueError
        except Exception:
            raise ValueError('ID inválido (use inteiro >= 1).')
        q['id']=new_id
        q['tipo']=int(self.cmb_tipo.get()) if self.cmb_tipo.get() else tipo_of(q)
        q['dificuldade']=self.cmb_diff.get().strip() or 'média'
        q['enunciado']=self.txt_enun.get('1.0','end').strip()
        q['imagens']=[l for l in self._get_lines(self.txt_imgs) if l.strip()]
        q['alternativas']=[l for l in self._get_lines(self.txt_alts) if l.strip()]
        q['correta']=self.ent_correct.get().strip()
        q['obs']=[l for l in self._get_lines(self.txt_obs)]
        if q['tipo']==3:
            vs={}
            for VAR,MIN,MAX,STEP in self.tbl_vars.get_data():
                if VAR.strip():
                    try:
                        mn=float(MIN); mx=float(MAX); st=float(STEP)
                        if st<=0 or mn>mx: raise ValueError
                    except Exception: raise ValueError(f'Variável {VAR}: faixas inválidas.')
                    vs[VAR.strip()]={'min':mn,'max':mx,'step':st}
            q['variaveis']=vs
            rs={}
            for NOME,EXPR in self.tbl_res.get_data():
                if NOME.strip() and EXPR.strip(): rs[NOME.strip()]=EXPR.strip()
            q['resolucoes']=rs; q.pop('afirmacoes',None)
        elif q['tipo']==4:
            aff={}
            for CH,TXT in self.tbl_aff.get_data():
                if CH.strip() and TXT.strip(): aff[CH.strip()]=TXT.strip()
            q['afirmacoes']=aff; q.pop('variaveis',None); q.pop('resolucoes',None)
        else:
            q.pop('variaveis',None); q.pop('resolucoes',None); q.pop('afirmacoes',None)
        return q

    def validate_question(self,q):
        if not q.get('enunciado'): raise ValueError('Enunciado não pode ser vazio.')
        if not isinstance(q.get('alternativas'),list): raise ValueError('Alternativas deve ser uma lista.')
        if q.get('tipo')==3:
            if not q.get('variaveis') or not q.get('resolucoes'): raise ValueError('Tipo 3: requer variaveis e resolucoes.')
        if q.get('tipo')==4:
            if not q.get('afirmacoes'): raise ValueError('Tipo 4: requer afirmacoes.')

    def _normalize_and_reorder_ids(self):
        self.data.sort(key=lambda q: int(q.get('id',1)))
        for i,q in enumerate(self.data,start=1): q['id']=i
    def save(self):
        try:
            current=self.collect_form(); self.validate_question(current)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f'Erro de validação:\n{e}', parent=self); return
        try: new_pos=int(current['id'])-1
        except Exception: new_pos=self.idx
        item=self.data.pop(self.idx); self.data.insert(max(0,min(new_pos,len(self.data))), item)
        self._normalize_and_reorder_ids(); self.idx=min(max(0,new_pos),len(self.data)-1)
        try:
            self.json_path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
            self.var_dirty.set(False)
            if self.on_saved: self.on_saved()
            messagebox.showinfo(APP_TITLE,'Questão salva e JSON atualizado.', parent=self)
            self._populate_dropdown(); self.load_current()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f'Erro ao salvar JSON:\n{e}', parent=self)

    def delete_current(self):
        if not messagebox.askyesno(APP_TITLE,'Excluir esta questão? A operação não pode ser desfeita.', parent=self): return
        del self.data[self.idx]
        if not self.data: messagebox.showinfo(APP_TITLE,'Todas as questões foram removidas.', parent=self); self.destroy(); return
        self._normalize_and_reorder_ids(); self.idx=min(self.idx,len(self.data)-1); self.save()
    def clone_current(self):
        clone=deepcopy(self.data[self.idx]); self.data.insert(self.idx+1, clone)
        self._normalize_and_reorder_ids(); self.idx=self.idx+1; self.save()
    def new_after_current(self):
        new_q={'id': self.data[self.idx]['id']+1, 'tipo':1, 'dificuldade':'média', 'enunciado':'', 'imagens':[], 'alternativas':[], 'correta':'', 'obs':[]}
        self.data.insert(self.idx+1, new_q); self._normalize_and_reorder_ids(); self.idx=self.idx+1; self.var_dirty.set(True); self.load_current()

    def build_sim_controls(self,q_tipo3):
        for child in list(self.frm_sim.children.values()): child.destroy()
        if not q_tipo3: ttk.Label(self.frm_sim,text='— (não aplicável)').grid(row=0,column=0,sticky='w'); return
        vars=q_tipo3.get('variaveis') or {}; self.sim_vars={}; r=0
        for name,cfg in vars.items():
            row=ttk.Frame(self.frm_sim); row.grid(row=r,column=0,sticky='ew',pady=2)
            ttk.Label(row,text=name).pack(side='left')
            val=tk.DoubleVar(value=float(cfg.get('min',0))); self.sim_vars[name]=(val,cfg)
            try:
                mn=float(cfg.get('min',0)); mx=float(cfg.get('max',0))
                scl=ttk.Scale(row,from_=mn,to=mx,orient='horizontal'); scl.pack(side='left',fill='x',expand=True,padx=6)
                ent=ttk.Entry(row,width=10,textvariable=val); ent.pack(side='left')
            except Exception: pass
            r+=1

    def update_preview(self):
        q=self.data[self.idx]; t=tipo_of(q); lines=[]
        first=f"{q.get('id')}) {q.get('enunciado','').strip()}"; lines.append(first); lines.append('')
        if t==4 and q.get('afirmacoes'):
            for k in sorted(q['afirmacoes'].keys(), key=lambda x: (len(str(x)), str(x))):
                lines.append(f"{k}) {q['afirmacoes'][k]}")
            lines.append('')
        alts=q.get('alternativas') or []; corr=q.get('correta',''); ordered=[]
        if corr: ordered.append(corr)
        ordered += [a for a in alts if a != corr]
        if t==3:
            vals={}
            for name,(var,cfg) in (getattr(self,'sim_vars',{}) or {}).items():
                try: vals[name]=float(var.get())
                except Exception: vals[name]=float(cfg.get('min',0))
            derived={}
            for name,expr in (q.get('resolucoes') or {}).items():
                expr_clean=self._expr_clean(expr, vals, {})
                try: derived[name]=safe_eval(expr_clean)
                except Exception: derived[name]=float('nan')
            for i,a in enumerate(ordered):
                letter=ALPH[i%len(ALPH)]; s=self._render_text(a, vals, derived); lines.append(f"{letter}) {s}")
        else:
            for i,a in enumerate(ordered):
                letter=ALPH[i%len(ALPH)]; lines.append(f"{letter}) {a}")
        if q.get('obs'):
            lines.append(''); lines.append('OBS.:')
            for line in q['obs']: lines.append(line)
        self.txt_preview.configure(state='normal'); self.txt_preview.delete('1.0','end'); self.txt_preview.insert('1.0','\n'.join(lines)); self.txt_preview.configure(state='disabled')

    def _expr_clean(self, expr, vals, derived):
        def replace_token(m):
            token=m.group(1)
            if token in vals: return str(vals[token])
            if token in derived: return str(derived[token])
            return '0'
        expr2=re.sub(r'<\s*([A-Za-z0-9_]+)\s*>', replace_token, expr)
        expr2=re.sub(r'[^0-9+\-*/(). ]','', expr2)
        return expr2
    def _render_text(self, text, vals, derived):
        def repl(m):
            inner=m.group(1).strip()
            m2=re.match(r'^([A-Za-z0-9_]+)\s*([+\-*/])\s*([0-9.]+)$', inner)
            if m2:
                name,op,num=m2.groups(); base=vals.get(name, derived.get(name,0.0))
                try: num=float(num)
                except Exception: num=0.0
                try: ex=f"{base}{op}{num}"; return f"{safe_eval(ex):.6f}"
                except Exception: return inner
            base=vals.get(inner, derived.get(inner, None))
            if base is None: return inner
            try: return f"{float(base):.6f}"
            except Exception: return str(base)
        return re.sub(r'<([^>]+)>', repl, text)

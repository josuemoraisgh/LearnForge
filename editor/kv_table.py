
# -*- coding: utf-8 -*-
"""
Tabela genérica editável (ttk.Treeview) para pares/linhas.
Responsabilidade: widget reutilizável.
"""
import tkinter as tk
from tkinter import ttk

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

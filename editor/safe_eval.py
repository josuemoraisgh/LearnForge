
# -*- coding: utf-8 -*-
"""
Avaliador matemático seguro (apenas +, -, *, /, parênteses e números).
"""
import re

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
            elif op=='/':
                self._eat_op('/')
                d=self._factor()
                if d==0: raise ZeroDivisionError('Divisão por zero')
                v/=d
            else: break
        return v
    def _expr(self):
        v=self._term()
        while True:
            _,op=self._peek()
            if op=='+': self._eat_op('+'); v+=self._term()
            elif op=='-': self._eat_op('-'); v-=self._term()
            else: break
        return v

def safe_eval(expr:str)->float:
    return SafeEval().parse(expr)

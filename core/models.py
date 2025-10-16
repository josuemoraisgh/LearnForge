
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Dict, Any, Optional

class QuestionType(IntEnum):
    TYPE1 = 1  # alternativas texto
    TYPE2 = 2  # alternativas imagem (ou mistas)
    TYPE3 = 3  # parametrizada (variáveis e resoluções)
    TYPE4 = 4  # afirmativas (I, II, III...)

@dataclass
class Question:
    id: int
    enunciado: str
    dificuldade: str = "média"
    imagens: List[str] = field(default_factory=list)
    alternativas: List[str] = field(default_factory=list)
    correta: str = ""
    tipo: QuestionType = QuestionType.TYPE1
    variaveis: Dict[str, Any] = field(default_factory=dict)
    resolucoes: Dict[str, str] = field(default_factory=dict)
    afirmacoes: Dict[str, str] = field(default_factory=dict)
    obs: List[str] = field(default_factory=list)

    @staticmethod
    def infer_tipo(data: Dict[str, Any]) -> QuestionType:
        t = data.get("tipo", None)
        if isinstance(t, int) and t in (1,2,3,4):
            return QuestionType(t)
        if data.get("variaveis") or data.get("resolucoes"):
            return QuestionType.TYPE3
        if data.get("afirmacoes"):
            return QuestionType.TYPE4
        alts = data.get("alternativas") or []
        if any(isinstance(a, str) and a.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp','.svg')) for a in alts):
            return QuestionType.TYPE2
        return QuestionType.TYPE1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Question":
        tipo = cls.infer_tipo(data)
        return cls(
            id = int(data.get("id", 0)),
            enunciado = str(data.get("enunciado","")).strip(),
            dificuldade = (data.get("dificuldade") or "média").strip(),
            imagens = list(data.get("imagens") or []),
            alternativas = list(data.get("alternativas") or []),
            correta = str(data.get("correta") or ""),
            tipo = tipo,
            variaveis = dict(data.get("variaveis") or {}),
            resolucoes = dict(data.get("resolucoes") or {}),
            afirmacoes = dict(data.get("afirmacoes") or {}),
            obs = list(data.get("obs") or []),
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "dificuldade": self.dificuldade or "média",
            "enunciado": self.enunciado,
            "imagens": [*self.imagens] if self.imagens else [],
            "alternativas": [*self.alternativas],
            "correta": self.correta,
            "tipo": int(self.tipo),
        }
        if self.variaveis: d["variaveis"] = self.variaveis
        if self.resolucoes: d["resolucoes"] = self.resolucoes
        if self.afirmacoes: d["afirmacoes"] = self.afirmacoes
        if self.obs: d["obs"] = self.obs
        return d

@dataclass
class RenderOptions:
    target: str  # "preview" | "testgen" | "beamer"
    shuffle_questions: bool = False
    shuffle_alternatives: bool = False
    seed: Optional[int] = None  # deterministic shuffling

@dataclass
class RenderedQuestion:
    id: int
    tipo: QuestionType
    enunciado: str
    imagens: List[str]
    alternativas: List[str]
    correta: str
    extra: Dict[str, Any] = field(default_factory=dict)

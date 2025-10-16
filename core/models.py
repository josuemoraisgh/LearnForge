from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

class QuestionKind(str, Enum):
    TYPE1 = "type1"
    TYPE2 = "type2"
    TYPE3 = "type3"
    TYPE4 = "type4"

@dataclass
class Choice:
    text: str
    is_correct: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Asset:
    kind: str            # "image", "audio", "equation", etc.
    src: str             # caminho/ID
    alt: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QuestionIR:
    id: int
    kind: QuestionKind
    prompt: str                  # texto plano com marcação leve (**negrito**, _itálico_, \LaTeX opcional)
    choices: List[Choice] = field(default_factory=list)
    solution: Optional[str] = None
    assets: List[Asset] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # dificuldade, tags, etc.

@dataclass
class QuizIR:
    title: str
    questions: List[QuestionIR]

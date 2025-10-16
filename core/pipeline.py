
from __future__ import annotations
from typing import List, Dict, Any
import random
from .models import Question, RenderOptions, RenderedQuestion
from .loader import load_questions
from .strategies import HANDLERS

def render_all(raw_questions: List[Dict[str, Any]], options: RenderOptions) -> List[RenderedQuestion]:
    qs = load_questions(raw_questions)
    rnd = random.Random(options.seed)

    # shuffle questions depending on target
    if options.shuffle_questions:
        qs = qs[:]
        rnd.shuffle(qs)

    rendered: List[RenderedQuestion] = []
    for q in qs:
        handler = HANDLERS[q.tipo]
        rq = handler.render(q, {"rnd": rnd, "target": options.target})
        # shuffle alternatives if requested (beamer keeps original order)
        if options.shuffle_alternatives:
            alts = rq.alternativas[:]
            rnd.shuffle(alts)
            rq.alternativas = alts
        rendered.append(rq)

    return rendered

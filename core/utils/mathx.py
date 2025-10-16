# Tudo que falta para o tipo 3 vai aqui — centralizado.
# Exemplos de helpers: simplificar frações, gerar distratores numéricos, formatar unidades etc.

from fractions import Fraction
from math import gcd

def simplify_fraction(n: int, d: int) -> str:
    f = Fraction(n, d).limit_denominator()
    return f"{f.numerator}/{f.denominator}"

def lcm(a: int, b: int) -> int:
    return abs(a*b) // gcd(a, b)

def round_sig(x: float, sig: int = 3) -> float:
    from math import log10, floor
    if x == 0:
        return 0.0
    return round(x, sig - int(floor(log10(abs(x)))) - 1)

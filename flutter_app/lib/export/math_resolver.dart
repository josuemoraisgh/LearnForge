import 'dart:math';
import '../domain/entities/question.dart';

/// Resolve variáveis e expressões matemáticas nas questões.
/// Replica a lógica do core/math.py do projeto Python original.
class MathResolver {
  MathResolver._();

  /// Processa todas as questões resolvendo <VAR> e <EXPRESSÃO>.
  static List<Question> resolveAll(List<Question> questions, int seed) {
    return questions.asMap().entries.map((entry) {
      return _resolveQuestion(entry.value, seed + entry.key);
    }).toList();
  }

  static Question _resolveQuestion(Question q, int seed) {
    if (q.variaveis.isEmpty && q.resolucoes.isEmpty) return q;

    final rng = Random(seed);
    final env = <String, double>{};

    // 1) Resolve variáveis com range min:step:max
    for (final entry in q.variaveis.entries) {
      final parts = entry.value.split(':');
      if (parts.length == 3) {
        final min = double.tryParse(parts[0]) ?? 0;
        final step = double.tryParse(parts[1]) ?? 1;
        final max = double.tryParse(parts[2]) ?? 0;
        final count = step == 0 ? 1 : ((max - min) / step).floor() + 1;
        final idx = rng.nextInt(count.clamp(1, 100000));
        env[entry.key] = min + step * idx;
      } else {
        env[entry.key] = double.tryParse(entry.value) ?? 0;
      }
    }

    // 2) Resolve expressões (resolucoes)
    for (final entry in q.resolucoes.entries) {
      try {
        env[entry.key] = _evalWithEnv(entry.value, env);
      } catch (_) {}
    }

    // 3) Substitui nos campos de texto
    String sub(String t) => _replaceVars(t, env);
    List<String> subList(List<String> l) => l.map(sub).toList();

    return q.copyWith(
      enunciado: sub(q.enunciado),
      alternativas: subList(q.alternativas),
      correta: sub(q.correta),
      obs: subList(q.obs),
    );
  }

  static String _replaceVars(String text, Map<String, double> env) {
    return text.replaceAllMapped(RegExp(r'<([^>]+)>'), (m) {
      final expr = m.group(1)!;
      // Tenta variável direta
      if (env.containsKey(expr)) {
        return _fmt(env[expr]!);
      }
      // Tenta avaliar como expressão
      try {
        return _fmt(_evalWithEnv(expr, env));
      } catch (_) {
        return m.group(0)!;
      }
    });
  }

  static double _evalWithEnv(String expr, Map<String, double> env) {
    // Substitui variáveis por seus valores (mais longa primeiro)
    var processed = expr.replaceAll(' ', '');
    final sorted = env.keys.toList()
      ..sort((a, b) => b.length.compareTo(a.length));
    for (final key in sorted) {
      processed = processed.replaceAll(key, env[key].toString());
    }
    return _ExprParser(processed).parse();
  }

  static String _fmt(double v) =>
      v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(2);
}

// ── Parser de expressões aritméticas (recursive descent) ─────────────────────

class _ExprParser {
  final String input;
  int _pos = 0;

  _ExprParser(this.input);

  double parse() {
    final result = _expr();
    if (_pos < input.length) {
      throw FormatException('Unexpected char at pos $_pos: ${input[_pos]}');
    }
    return result;
  }

  double _expr() {
    var result = _term();
    while (_pos < input.length && (input[_pos] == '+' || input[_pos] == '-')) {
      final op = input[_pos++];
      final right = _term();
      result = op == '+' ? result + right : result - right;
    }
    return result;
  }

  double _term() {
    var result = _unary();
    while (_pos < input.length && (input[_pos] == '*' || input[_pos] == '/')) {
      final op = input[_pos++];
      final right = _unary();
      result = op == '*' ? result * right : result / right;
    }
    return result;
  }

  double _unary() {
    if (_pos < input.length && input[_pos] == '-') {
      _pos++;
      return -_primary();
    }
    if (_pos < input.length && input[_pos] == '+') {
      _pos++;
    }
    return _primary();
  }

  double _primary() {
    if (_pos < input.length && input[_pos] == '(') {
      _pos++; // '('
      final result = _expr();
      if (_pos < input.length && input[_pos] == ')') _pos++;
      return result;
    }
    // Número
    final start = _pos;
    while (_pos < input.length &&
        (input[_pos] == '.' ||
            (input[_pos].codeUnitAt(0) >= 48 &&
                input[_pos].codeUnitAt(0) <= 57))) {
      _pos++;
    }
    if (_pos == start) {
      throw FormatException('Expected number at pos $_pos in "$input"');
    }
    return double.parse(input.substring(start, _pos));
  }
}

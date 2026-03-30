import 'dart:convert';

/// Entidade imutável que representa uma questão educacional.
/// Segue o princípio de Single Responsibility: apenas modela os dados da questão.
class Question {
  final int? id;
  final int tipo;
  final String dificuldade;
  final String enunciado;
  final List<String> alternativas;
  final String correta;

  /// Observações / feedback exibidos APÓS a resolução da questão.
  /// Exportado como generalfeedback no Moodle XML e como frame de OBS no Beamer.
  final List<String> obs;

  final List<String> imagens;
  final Map<String, String> afirmacoes;
  final String? subenunciado;
  final Map<String, String> variaveis;
  final Map<String, String> resolucoes;

  const Question({
    this.id,
    this.tipo = 1,
    this.dificuldade = 'média',
    required this.enunciado,
    this.alternativas = const [],
    this.correta = '',
    this.obs = const [],
    this.imagens = const [],
    this.afirmacoes = const {},
    this.subenunciado,
    this.variaveis = const {},
    this.resolucoes = const {},
  });

  Question copyWith({
    int? id,
    int? tipo,
    String? dificuldade,
    String? enunciado,
    List<String>? alternativas,
    String? correta,
    List<String>? obs,
    List<String>? imagens,
    Map<String, String>? afirmacoes,
    String? subenunciado,
    Map<String, String>? variaveis,
    Map<String, String>? resolucoes,
  }) =>
      Question(
        id: id ?? this.id,
        tipo: tipo ?? this.tipo,
        dificuldade: dificuldade ?? this.dificuldade,
        enunciado: enunciado ?? this.enunciado,
        alternativas: alternativas ?? List.unmodifiable(this.alternativas),
        correta: correta ?? this.correta,
        obs: obs ?? List.unmodifiable(this.obs),
        imagens: imagens ?? List.unmodifiable(this.imagens),
        afirmacoes: afirmacoes ?? Map.unmodifiable(this.afirmacoes),
        subenunciado: subenunciado ?? this.subenunciado,
        variaveis: variaveis ?? Map.unmodifiable(this.variaveis),
        resolucoes: resolucoes ?? Map.unmodifiable(this.resolucoes),
      );

  factory Question.fromJson(Map<String, dynamic> json) {
    return Question(
      id: json['id'] as int?,
      tipo: (json['tipo'] as int?) ?? 1,
      dificuldade: (json['dificuldade'] as String?) ?? 'média',
      enunciado: (json['enunciado'] as String?) ?? '',
      alternativas: _parseStringList(json['alternativas']),
      correta: _parseString(json['correta']),
      obs: _parseStringList(json['obs']),
      imagens: _parseStringList(json['imagens']),
      afirmacoes: _parseStringMap(json['afirmacoes']),
      subenunciado: json['subenunciado'] as String?,
      variaveis: _parseStringMap(json['variaveis']),
      resolucoes: _parseStringMap(json['resolucoes']),
    );
  }

  Map<String, dynamic> toJson() => {
        if (id != null) 'id': id,
        'tipo': tipo,
        'dificuldade': dificuldade,
        'enunciado': enunciado,
        if (alternativas.isNotEmpty) 'alternativas': alternativas,
        if (correta.isNotEmpty) 'correta': correta,
        if (obs.isNotEmpty) 'obs': obs,
        if (imagens.isNotEmpty) 'imagens': imagens,
        if (afirmacoes.isNotEmpty) 'afirmacoes': afirmacoes,
        if (subenunciado != null) 'subenunciado': subenunciado,
        if (variaveis.isNotEmpty) 'variaveis': variaveis,
        if (resolucoes.isNotEmpty) 'resolucoes': resolucoes,
      };

  String toJsonString() => const JsonEncoder.withIndent('  ').convert(toJson());

  // ── helpers de parse ──────────────────────────────────────────────────────

  static List<String> _parseStringList(dynamic value) {
    if (value == null) return const [];
    if (value is List) return List<String>.from(value.map((e) => e.toString()));
    if (value is String && value.isNotEmpty) return [value];
    return const [];
  }

  static String _parseString(dynamic value) {
    if (value == null) return '';
    return value.toString();
  }

  static Map<String, String> _parseStringMap(dynamic value) {
    if (value == null) return const {};
    if (value is Map) {
      return Map<String, String>.fromEntries(
        value.entries.map((e) => MapEntry(e.key.toString(), e.value.toString())),
      );
    }
    return const {};
  }

  /// Converte uma lista de questões a partir de JSON bruto (arquivo).
  static List<Question> listFromJsonSource(dynamic json) {
    if (json is List) {
      return json
          .whereType<Map<String, dynamic>>()
          .map(Question.fromJson)
          .toList();
    }
    if (json is Map<String, dynamic>) {
      final qs = json['questions'];
      if (qs is List) {
        return qs
            .whereType<Map<String, dynamic>>()
            .map(Question.fromJson)
            .toList();
      }
      // Trata o próprio mapa como uma única questão
      return [Question.fromJson(json)];
    }
    return const [];
  }
}

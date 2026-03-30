import '../domain/entities/question.dart';

/// Interface para exportadores — respeita Open/Closed e Liskov Substitution.
/// Adicione novos formatos implementando esta interface sem alterar o código existente.
abstract class IExporter {
  /// Rótulo legível para a UI (ex.: "Moodle XML", "LaTeX Beamer").
  String get label;

  /// Extensão do arquivo gerado (ex.: ".xml", ".tex").
  String get fileExtension;

  /// Ícone Material exibido na tela de exportação.
  String get iconAsset;

  /// Gera o conteúdo exportado como string.
  String export(List<Question> questions, ExportConfig config);
}

/// Configurações usadas por todos os exportadores.
class ExportConfig {
  final String title;
  final int seed;
  final int fontSizeQuestion;
  final int fontSizeAnswer;
  final String alertColor;
  final bool shuffle;

  const ExportConfig({
    this.title = 'Quiz LearnForge',
    this.seed = 42,
    this.fontSizeQuestion = 12,
    this.fontSizeAnswer = 11,
    this.alertColor = 'red',
    this.shuffle = false,
  });

  ExportConfig copyWith({
    String? title,
    int? seed,
    int? fontSizeQuestion,
    int? fontSizeAnswer,
    String? alertColor,
    bool? shuffle,
  }) =>
      ExportConfig(
        title: title ?? this.title,
        seed: seed ?? this.seed,
        fontSizeQuestion: fontSizeQuestion ?? this.fontSizeQuestion,
        fontSizeAnswer: fontSizeAnswer ?? this.fontSizeAnswer,
        alertColor: alertColor ?? this.alertColor,
        shuffle: shuffle ?? this.shuffle,
      );
}

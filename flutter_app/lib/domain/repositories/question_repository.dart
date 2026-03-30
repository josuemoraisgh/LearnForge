import '../entities/question.dart';

/// Contrato abstrato para carregamento e persistência de questões.
/// Dependency Inversion Principle: camadas superiores dependem desta abstração,
/// não de implementações concretas de I/O.
abstract interface class IQuestionRepository {
  /// Carrega questões a partir de um arquivo JSON ou ZIP.
  Future<List<Question>> loadFromFile(String filePath);

  /// Salva as questões de volta ao arquivo JSON de origem.
  Future<void> saveToFile(String filePath, List<Question> questions);
}

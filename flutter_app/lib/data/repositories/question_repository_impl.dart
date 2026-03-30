import '../../domain/entities/question.dart';
import '../../domain/repositories/question_repository.dart';
import '../datasources/json_file_datasource.dart';

/// Implementação concreta do repositório, usando o datasource de arquivo.
/// Dependency Inversion: implementa a interface definida no domínio.
class QuestionRepositoryImpl implements IQuestionRepository {
  final JsonFileDatasource _datasource;

  const QuestionRepositoryImpl(this._datasource);

  @override
  Future<List<Question>> loadFromFile(String filePath) =>
      _datasource.readQuestions(filePath);

  @override
  Future<void> saveToFile(String filePath, List<Question> questions) =>
      _datasource.writeQuestions(filePath, questions);
}

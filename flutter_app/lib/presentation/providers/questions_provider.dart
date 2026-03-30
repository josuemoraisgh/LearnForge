import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/json_file_datasource.dart';
import '../../data/repositories/question_repository_impl.dart';
import '../../domain/entities/question.dart';
import '../../domain/repositories/question_repository.dart';
import '../../export/exporter_interface.dart';
import '../../export/math_resolver.dart';

// ── Providers de infraestrutura (Dependency Inversion via Riverpod) ────────────

final datasourceProvider = Provider<JsonFileDatasource>(
  (_) => const JsonFileDatasource(),
);

final repositoryProvider = Provider<IQuestionRepository>(
  (ref) => QuestionRepositoryImpl(ref.watch(datasourceProvider)),
);

// ── Estado principal ──────────────────────────────────────────────────────────

class QuestionsState {
  final List<Question> questions;
  final List<String> filePaths; // arquivos carregados
  final bool isLoading;
  final String? error;
  final String? successMessage;

  const QuestionsState({
    this.questions = const [],
    this.filePaths = const [],
    this.isLoading = false,
    this.error,
    this.successMessage,
  });

  QuestionsState copyWith({
    List<Question>? questions,
    List<String>? filePaths,
    bool? isLoading,
    String? error,
    String? successMessage,
    bool clearError = false,
    bool clearSuccess = false,
  }) =>
      QuestionsState(
        questions: questions ?? this.questions,
        filePaths: filePaths ?? this.filePaths,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        successMessage:
            clearSuccess ? null : (successMessage ?? this.successMessage),
      );

  int get count => questions.length;
  bool get isEmpty => questions.isEmpty;
}

// ── StateNotifier ─────────────────────────────────────────────────────────────

class QuestionsNotifier extends StateNotifier<QuestionsState> {
  final IQuestionRepository _repo;

  QuestionsNotifier(this._repo) : super(const QuestionsState());

  // ── Carregamento ────────────────────────────────────────────────────────────

  Future<void> addFile(String path) async {
    if (state.filePaths.contains(path)) return;

    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final loaded = await _repo.loadFromFile(path);
      state = state.copyWith(
        isLoading: false,
        questions: [...state.questions, ...loaded],
        filePaths: [...state.filePaths, path],
        successMessage: '${loaded.length} questão(ões) carregada(s) de '
            '${path.split(Platform.pathSeparator).last}',
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Erro ao carregar $path: $e',
      );
    }
  }

  void removeFile(String path) {
    // Remove questões associadas ao arquivo
    final remainingPaths =
        state.filePaths.where((p) => p != path).toList();
    state = state.copyWith(
      filePaths: remainingPaths,
      // Reloading seria ideal, mas por simplicidade removemos todas e
      // o usuário pode recarregar. Para produção, mapeie questão→arquivo.
      successMessage: 'Arquivo removido: ${path.split(Platform.pathSeparator).last}',
    );
  }

  void clearAll() {
    state = const QuestionsState();
  }

  // ── Edição ──────────────────────────────────────────────────────────────────

  void updateQuestion(int index, Question updated) {
    if (index < 0 || index >= state.questions.length) return;
    final questions = List<Question>.from(state.questions);
    questions[index] = updated;
    state = state.copyWith(questions: questions);
  }

  void addQuestion(Question q) {
    state = state.copyWith(questions: [...state.questions, q]);
  }

  void removeQuestion(int index) {
    if (index < 0 || index >= state.questions.length) return;
    final questions = List<Question>.from(state.questions)..removeAt(index);
    state = state.copyWith(questions: questions);
  }

  // ── Resolução de variáveis ──────────────────────────────────────────────────

  List<Question> resolveQuestions(int seed) {
    return MathResolver.resolveAll(state.questions, seed);
  }

  // ── Persistência ────────────────────────────────────────────────────────────

  Future<void> saveFile(String path) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _repo.saveToFile(path, state.questions);
      state = state.copyWith(
        isLoading: false,
        successMessage: 'Salvo em ${path.split(Platform.pathSeparator).last}',
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Erro ao salvar: $e');
    }
  }

  // ── Exportação ──────────────────────────────────────────────────────────────

  Future<void> exportTo(
    IExporter exporter,
    String outputPath,
    ExportConfig config,
  ) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final resolved = resolveQuestions(config.seed);
      final content = exporter.export(resolved, config);
      final file = File(outputPath);
      await file.writeAsString(content, flush: true);
      state = state.copyWith(
        isLoading: false,
        successMessage:
            'Exportado para ${outputPath.split(Platform.pathSeparator).last}',
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Erro na exportação: $e');
    }
  }

  // ── Utilitários ─────────────────────────────────────────────────────────────

  void clearMessages() {
    state = state.copyWith(clearError: true, clearSuccess: true);
  }
}

// ── Provider público ──────────────────────────────────────────────────────────

final questionsProvider =
    StateNotifierProvider<QuestionsNotifier, QuestionsState>(
  (ref) => QuestionsNotifier(ref.watch(repositoryProvider)),
);

// ── Providers derivados (Interface Segregation) ───────────────────────────────

final questionCountProvider = Provider<int>(
  (ref) => ref.watch(questionsProvider).count,
);

final questionListProvider = Provider<List<Question>>(
  (ref) => ref.watch(questionsProvider).questions,
);

final isLoadingProvider = Provider<bool>(
  (ref) => ref.watch(questionsProvider).isLoading,
);

// ── Configuração de exportação ────────────────────────────────────────────────

class ExportConfigNotifier extends StateNotifier<ExportConfig> {
  ExportConfigNotifier() : super(const ExportConfig());

  void update({
    String? title,
    int? seed,
    int? fontSizeQuestion,
    int? fontSizeAnswer,
    String? alertColor,
    bool? shuffle,
  }) {
    state = state.copyWith(
      title: title,
      seed: seed,
      fontSizeQuestion: fontSizeQuestion,
      fontSizeAnswer: fontSizeAnswer,
      alertColor: alertColor,
      shuffle: shuffle,
    );
  }
}

final exportConfigProvider =
    StateNotifierProvider<ExportConfigNotifier, ExportConfig>(
  (_) => ExportConfigNotifier(),
);

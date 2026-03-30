import 'dart:convert';
import 'dart:io';
import 'package:archive/archive_io.dart';
import '../../domain/entities/question.dart';

/// Fonte de dados responsável por ler/escrever arquivos JSON e ZIP.
/// Single Responsibility: só sabe ler/escrever arquivos.
class JsonFileDatasource {
  const JsonFileDatasource();

  Future<List<Question>> readQuestions(String filePath) async {
    final file = File(filePath);
    if (!await file.exists()) {
      throw FileSystemException('Arquivo não encontrado', filePath);
    }

    final lower = filePath.toLowerCase();

    if (lower.endsWith('.zip')) {
      return _readFromZip(file);
    }

    if (lower.endsWith('.json')) {
      return _readFromJson(file);
    }

    throw UnsupportedError('Formato não suportado: $filePath');
  }

  Future<void> writeQuestions(String filePath, List<Question> questions) async {
    final file = File(filePath);
    final json = questions.length == 1
        ? questions.first.toJson()
        : {'questions': questions.map((q) => q.toJson()).toList()};
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(json),
      encoding: utf8,
    );
  }

  // ── privados ───────────────────────────────────────────────────────────────

  Future<List<Question>> _readFromJson(File file) async {
    final content = await file.readAsString(encoding: utf8);
    final dynamic parsed = jsonDecode(content);
    return _normalize(parsed);
  }

  Future<List<Question>> _readFromZip(File file) async {
    final bytes = await file.readAsBytes();
    final archive = ZipDecoder().decodeBytes(bytes);
    final questions = <Question>[];

    for (final entry in archive) {
      if (!entry.isFile) continue;
      if (!entry.name.toLowerCase().endsWith('.json')) continue;

      try {
        final content = utf8.decode(entry.content as List<int>);
        final dynamic parsed = jsonDecode(content);
        questions.addAll(_normalize(parsed));
      } catch (_) {
        // Ignora arquivos JSON inválidos dentro do ZIP
      }
    }

    return questions;
  }

  List<Question> _normalize(dynamic parsed) {
    try {
      return Question.listFromJsonSource(parsed);
    } catch (_) {
      return const [];
    }
  }
}

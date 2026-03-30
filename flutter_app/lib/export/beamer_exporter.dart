import 'dart:math';
import '../domain/entities/question.dart';
import 'exporter_interface.dart';

/// Exporta questões como apresentação LaTeX Beamer.
/// Replica a lógica do beamer/generator.py original.
class BeamerExporter implements IExporter {
  const BeamerExporter();

  @override
  String get label => 'LaTeX Beamer';

  @override
  String get fileExtension => '.tex';

  @override
  String get iconAsset => 'slideshow';

  @override
  String export(List<Question> questions, ExportConfig config) {
    final buf = StringBuffer();
    _writePreamble(buf, config);

    var qIndex = 0;
    for (final q in questions) {
      qIndex++;
      _writeQuestionFrames(buf, q, qIndex, config);
    }

    buf.writeln(r'\end{document}');
    return buf.toString();
  }

  // ── Preâmbulo ──────────────────────────────────────────────────────────────

  void _writePreamble(StringBuffer buf, ExportConfig config) {
    buf.writeln(r'\documentclass[aspectratio=169]{beamer}');
    buf.writeln(r'\usepackage[utf8]{inputenc}');
    buf.writeln(r'\usepackage[T1]{fontenc}');
    buf.writeln(r'\usepackage[brazil]{babel}');
    buf.writeln(r'\usepackage{graphicx}');
    buf.writeln(r'\usepackage{amsmath,amssymb}');
    buf.writeln(r'\usepackage{xcolor}');
    buf.writeln(r'\usetheme{Madrid}');
    buf.writeln(r'\usecolortheme{whale}');
    buf.writeln();
    buf.writeln('\\title{${_tex(config.title)}}');
    buf.writeln(r'\author{LearnForge}');
    buf.writeln(r'\date{\today}');
    buf.writeln();
    final fszQ = config.fontSizeQuestion;
    final fszA = config.fontSizeAnswer;
    buf.writeln(
        '\\newcommand{\\QuestionSize}{\\fontsize{$fszQ}{${fszQ + 2}}\\selectfont}');
    buf.writeln(
        '\\newcommand{\\AnswerSize}{\\fontsize{$fszA}{${fszA + 2}}\\selectfont}');
    buf.writeln();
    buf.writeln(r'\begin{document}');
    buf.writeln(r'\maketitle');
    buf.writeln();
  }

  // ── Frames por questão ─────────────────────────────────────────────────────

  void _writeQuestionFrames(
    StringBuffer buf,
    Question q,
    int index,
    ExportConfig config,
  ) {
    final title = '$index) ${_tex(q.enunciado)}';

    // Frame 1: questão sem gabarito
    _writeFrame(buf, title, q, showAnswer: false, config: config);

    // Frame 2 (opcional): observações/feedback
    if (q.obs.isNotEmpty) {
      _writeObsFrame(buf, title, q.obs, config);
    }

    // Frame 3: questão com gabarito destacado
    _writeFrame(buf, title, q, showAnswer: true, config: config);
  }

  void _writeFrame(
    StringBuffer buf,
    String title,
    Question q, {
    required bool showAnswer,
    required ExportConfig config,
  }) {
    buf.writeln(r'\begin{frame}');
    buf.writeln('  \\frametitle{$title}');
    buf.writeln(r'  {\QuestionSize');
    buf.writeln();

    // Imagens
    if (q.imagens.isNotEmpty) {
      buf.writeln(r'  \begin{center}');
      for (final img in q.imagens) {
        final path = _imgPath(img);
        final dims = _imgDims(img);
        buf.writeln(
            '    \\includegraphics[$dims]{${_tex(path)}}');
      }
      buf.writeln(r'  \end{center}');
    }

    // Subenunciado
    if (q.subenunciado != null && q.subenunciado!.isNotEmpty) {
      buf.writeln('  ${_tex(q.subenunciado!)}\\\\');
      buf.writeln();
    }

    // Alternativas ou afirmações
    if (q.tipo == 4 && q.afirmacoes.isNotEmpty) {
      _writeAfirmacoes(buf, q, showAnswer, config);
    } else {
      _writeAlternativas(buf, q, showAnswer, config);
    }

    buf.writeln(r'  }');
    buf.writeln(r'\end{frame}');
    buf.writeln();
  }

  void _writeAlternativas(
    StringBuffer buf,
    Question q,
    bool showAnswer,
    ExportConfig config,
  ) {
    // Insere a correta no índice determinístico
    final alts = _mergeCorrect(q);

    buf.writeln(r'  {\AnswerSize');
    buf.writeln(r'  \begin{enumerate}[a)]');

    for (final alt in alts) {
      final isCorrect = alt == q.correta;
      if (showAnswer && isCorrect) {
        buf.writeln(
            '    \\item \\textcolor{${config.alertColor}}{\\textbf{${_tex(alt)}}}');
      } else {
        buf.writeln('    \\item ${_tex(alt)}');
      }
    }

    buf.writeln(r'  \end{enumerate}');
    buf.writeln(r'  }');
  }

  void _writeAfirmacoes(
    StringBuffer buf,
    Question q,
    bool showAnswer,
    ExportConfig config,
  ) {
    buf.writeln(r'  \begin{itemize}');
    for (final entry in q.afirmacoes.entries) {
      buf.writeln('    \\item \\textbf{${entry.key}.} ${_tex(entry.value)}');
    }
    buf.writeln(r'  \end{itemize}');

    if (q.subenunciado != null) {
      buf.writeln('  ${_tex(q.subenunciado!)}\\\\');
    }

    if (q.alternativas.isNotEmpty) {
      _writeAlternativas(buf, q, showAnswer, config);
    } else if (showAnswer && q.correta.isNotEmpty) {
      buf.writeln();
      buf.writeln(
          '  \\textbf{Gabarito:} \\textcolor{${config.alertColor}}{${_tex(q.correta)}}');
    }
  }

  void _writeObsFrame(
    StringBuffer buf,
    String title,
    List<String> obs,
    ExportConfig config,
  ) {
    buf.writeln(r'\begin{frame}');
    buf.writeln('  \\frametitle{$title}');
    buf.writeln(r'  {\QuestionSize');
    buf.writeln('  \\textbf{OBS.:}');
    buf.writeln(r'  \begin{itemize}');
    for (final item in obs) {
      buf.writeln('    \\item ${_tex(item)}');
    }
    buf.writeln(r'  \end{itemize}');
    buf.writeln(r'  }');
    buf.writeln(r'\end{frame}');
    buf.writeln();
  }

  // ── helpers ────────────────────────────────────────────────────────────────

  /// Insere a correta em posição determinística (baseada no enunciado).
  List<String> _mergeCorrect(Question q) {
    final alts = List<String>.from(q.alternativas);
    if (q.correta.isEmpty) return alts;
    if (alts.contains(q.correta)) return alts;

    final seed = q.enunciado.codeUnits.fold<int>(0, (a, b) => a + b);
    final rng = Random(seed + alts.length);
    final pos = rng.nextInt(alts.length + 1);
    alts.insert(pos, q.correta);
    return alts;
  }

  String _imgPath(String raw) {
    if (raw.contains('|')) return raw.split('|').first;
    return raw;
  }

  String _imgDims(String raw) {
    if (raw.contains('|')) {
      final dims = raw.split('|')[1];
      final parts = dims.split('x');
      if (parts.length == 2) {
        return 'width=${parts[0]}mm,height=${parts[1]}mm,keepaspectratio';
      }
    }
    return 'width=0.8\\textwidth';
  }

  /// Escapa caracteres especiais do LaTeX e converte Unicode.
  String _tex(String s) {
    final replacements = <String, String>{
      '\\': r'\textbackslash{}',
      '{': r'\{',
      '}': r'\}',
      '\$': r'\$',
      '&': r'\&',
      '#': r'\#',
      '%': r'\%',
      '^': r'\textasciicircum{}',
      '_': r'\_',
      '~': r'\textasciitilde{}',
      'α': r'\(\alpha\)',
      'β': r'\(\beta\)',
      'γ': r'\(\gamma\)',
      'δ': r'\(\delta\)',
      'Δ': r'\(\Delta\)',
      'θ': r'\(\theta\)',
      'λ': r'\(\lambda\)',
      'μ': r'\(\mu\)',
      'π': r'\(\pi\)',
      'σ': r'\(\sigma\)',
      'φ': r'\(\varphi\)',
      'ω': r'\(\omega\)',
      'Ω': r'\(\Omega\)',
      '°': r'\({}^\circ\)',
      '²': r'\({}^2\)',
      '³': r'\({}^3\)',
      '±': r'\(\pm\)',
      '×': r'\(\times\)',
      '÷': r'\(\div\)',
      '≤': r'\(\leq\)',
      '≥': r'\(\geq\)',
      '≠': r'\(\neq\)',
      '√': r'\(\sqrt{}\)',
      '∞': r'\(\infty\)',
    };

    var result = s;
    // Backslash primeiro para não double-processar
    for (final entry in replacements.entries) {
      result = result.replaceAll(entry.key, entry.value);
    }
    return result;
  }
}

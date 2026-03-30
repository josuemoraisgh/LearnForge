import '../domain/entities/question.dart';
import 'exporter_interface.dart';

/// Exporta questões no formato XML padrão do Moodle (Gift-XML / Moodle XML).
/// O campo `obs` é mapeado para `generalfeedback` — texto exibido ao aluno
/// após ele responder a questão, funcionando como comentário/explicação.
class MoodleXmlExporter implements IExporter {
  const MoodleXmlExporter();

  @override
  String get label => 'Moodle XML';

  @override
  String get fileExtension => '.xml';

  @override
  String get iconAsset => 'quiz';

  @override
  String export(List<Question> questions, ExportConfig config) {
    final buf = StringBuffer();
    buf.writeln('<?xml version="1.0" encoding="UTF-8"?>');
    buf.writeln('<quiz>');

    for (int i = 0; i < questions.length; i++) {
      _writeQuestion(buf, questions[i], i + 1, config);
    }

    buf.writeln('</quiz>');
    return buf.toString();
  }

  void _writeQuestion(
    StringBuffer buf,
    Question q,
    int index,
    ExportConfig config,
  ) {
    final tipo = q.tipo;

    // Questões de afirmações (tipo 4) exportadas como essay por ora
    if (tipo == 4 && q.afirmacoes.isNotEmpty) {
      _writeEssayQuestion(buf, q, index);
      return;
    }

    // Questão de múltipla escolha (tipos 1, 2, 3)
    _writeMultichoiceQuestion(buf, q, index, config);
  }

  void _writeMultichoiceQuestion(
    StringBuffer buf,
    Question q,
    int index,
    ExportConfig config,
  ) {
    final name = _esc('Q$index - ${_truncate(q.enunciado, 60)}');
    final questionHtml = _toHtml(q.enunciado, q.imagens, q.subenunciado);
    final feedbackHtml = _obsToHtml(q.obs);

    buf.writeln('  <question type="multichoice">');
    buf.writeln('    <name><text>$name</text></name>');
    buf.writeln('    <questiontext format="html">');
    buf.writeln('      <text><![CDATA[$questionHtml]]></text>');
    buf.writeln('    </questiontext>');
    buf.writeln('    <generalfeedback format="html">');
    buf.writeln('      <text><![CDATA[$feedbackHtml]]></text>');
    buf.writeln('    </generalfeedback>');
    buf.writeln('    <defaultgrade>1.0</defaultgrade>');
    buf.writeln('    <penalty>0.25</penalty>');
    buf.writeln('    <hidden>0</hidden>');
    buf.writeln('    <idnumber/>');
    buf.writeln('    <single>true</single>');
    buf.writeln('    <shuffleanswers>true</shuffleanswers>');
    buf.writeln('    <answernumbering>abc</answernumbering>');
    buf.writeln('    <showstandardinstruction>0</showstandardinstruction>');
    buf.writeln('    <correctfeedback format="html">');
    buf.writeln('      <text>Resposta correta!</text>');
    buf.writeln('    </correctfeedback>');
    buf.writeln('    <partiallycorrectfeedback format="html">');
    buf.writeln('      <text>Parcialmente correto.</text>');
    buf.writeln('    </partiallycorrectfeedback>');
    buf.writeln('    <incorrectfeedback format="html">');
    buf.writeln('      <text>Resposta incorreta.</text>');
    buf.writeln('    </incorrectfeedback>');

    // Resposta correta (fraction=100)
    final correctText = _esc(q.correta.isNotEmpty ? q.correta : 'N/A');
    buf.writeln('    <answer fraction="100" format="html">');
    buf.writeln('      <text><![CDATA[<p>$correctText</p>]]></text>');
    buf.writeln('      <feedback format="html">');
    buf.writeln('        <text>Correto!</text>');
    buf.writeln('      </feedback>');
    buf.writeln('    </answer>');

    // Alternativas incorretas
    for (final alt in q.alternativas) {
      if (alt == q.correta) continue;
      final altText = _esc(alt);
      buf.writeln('    <answer fraction="0" format="html">');
      buf.writeln('      <text><![CDATA[<p>$altText</p>]]></text>');
      buf.writeln('      <feedback format="html">');
      buf.writeln('        <text>Incorreto.</text>');
      buf.writeln('      </feedback>');
      buf.writeln('    </answer>');
    }

    buf.writeln('  </question>');
    buf.writeln();
  }

  void _writeEssayQuestion(StringBuffer buf, Question q, int index) {
    final name = _esc('Q$index - ${_truncate(q.enunciado, 60)}');
    final questionHtml = _buildAfirmacoesHtml(q);
    final feedbackHtml = _obsToHtml(q.obs);

    buf.writeln('  <question type="essay">');
    buf.writeln('    <name><text>$name</text></name>');
    buf.writeln('    <questiontext format="html">');
    buf.writeln('      <text><![CDATA[$questionHtml]]></text>');
    buf.writeln('    </questiontext>');
    buf.writeln('    <generalfeedback format="html">');
    buf.writeln('      <text><![CDATA[$feedbackHtml]]></text>');
    buf.writeln('    </generalfeedback>');
    buf.writeln('    <defaultgrade>1.0</defaultgrade>');
    buf.writeln('    <hidden>0</hidden>');
    buf.writeln('    <responseformat>editor</responseformat>');
    buf.writeln('    <responserequired>1</responserequired>');
    buf.writeln('    <responsefieldlines>5</responsefieldlines>');
    buf.writeln('    <attachments>0</attachments>');
    buf.writeln('    <graderinfo format="html">');
    buf.writeln('      <text><![CDATA[<p>${_esc(q.correta)}</p>]]></text>');
    buf.writeln('    </graderinfo>');
    buf.writeln('  </question>');
    buf.writeln();
  }

  // ── helpers ────────────────────────────────────────────────────────────────

  String _toHtml(String enunciado, List<String> imagens, String? subenunciado) {
    final buf = StringBuffer();
    buf.write('<p>${_esc(enunciado)}</p>');
    if (subenunciado != null && subenunciado.isNotEmpty) {
      buf.write('<p><em>${_esc(subenunciado)}</em></p>');
    }
    for (final img in imagens) {
      final path = _extractImagePath(img);
      if (path.isNotEmpty) {
        buf.write('<p><img src="@@PLUGINFILE@@/${_esc(path)}" /></p>');
      }
    }
    return buf.toString();
  }

  /// Transforma o campo `obs` em HTML de feedback.
  /// Cada item da lista vira um parágrafo — exibido ao aluno após a resposta.
  String _obsToHtml(List<String> obs) {
    if (obs.isEmpty) return '';
    final buf = StringBuffer('<p><strong>Comentários / Explicação:</strong></p>');
    buf.write('<ul>');
    for (final item in obs) {
      buf.write('<li>${_esc(item)}</li>');
    }
    buf.write('</ul>');
    return buf.toString();
  }

  String _buildAfirmacoesHtml(Question q) {
    final buf = StringBuffer('<p>${_esc(q.enunciado)}</p><ul>');
    for (final entry in q.afirmacoes.entries) {
      buf.write('<li><strong>${_esc(entry.key)}.</strong> ${_esc(entry.value)}</li>');
    }
    buf.write('</ul>');
    if (q.subenunciado != null && q.subenunciado!.isNotEmpty) {
      buf.write('<p>${_esc(q.subenunciado!)}</p>');
    }
    return buf.toString();
  }

  String _extractImagePath(String raw) {
    if (raw.contains('|')) return raw.split('|').first;
    return raw;
  }

  String _truncate(String s, int max) =>
      s.length > max ? '${s.substring(0, max)}…' : s;

  String _esc(String s) => s
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&apos;');
}

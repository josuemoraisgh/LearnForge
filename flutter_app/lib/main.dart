import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    // ProviderScope é o container de DI do Riverpod — raiz da árvore
    const ProviderScope(
      child: LearnForgeApp(),
    ),
  );
}

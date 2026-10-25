import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'features/start/presentation/start_screen.dart';

void main() {
  runApp(const ProviderScope(child: BoliggaetApp()));
}

class BoliggaetApp extends StatelessWidget {
  const BoliggaetApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Boliggaet',
      theme: AppTheme.light,
      home: const StartScreen(),
    );
  }
}

import 'package:boliggaetapp/features/start/presentation/start_screen.dart';
import 'package:boliggaetapp/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('app starts on the start page, without the old counter', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: BoliggaetApp()));

    expect(find.byType(StartScreen), findsOneWidget);
    expect(find.byType(FloatingActionButton), findsNothing);
    expect(find.byIcon(Icons.add), findsNothing);
  });
}

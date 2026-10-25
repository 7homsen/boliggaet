import 'package:boliggaetapp/features/start/presentation/start_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _phoneSize = Size(375, 812);
const _desktopSize = Size(1440, 900);

Future<void> _pumpStartScreen(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(const MaterialApp(home: StartScreen()));
}

Finder _button(String label) =>
    find.ancestor(of: find.text(label), matching: find.byType(FilledButton));

void main() {
  testWidgets(
    'shows exactly two buttons, "Nyt Spil" above "Jeg ser en bolig"',
    (tester) async {
      await _pumpStartScreen(tester, _phoneSize);

      expect(find.byType(FilledButton), findsNWidgets(2));
      expect(
        find.byWidgetPredicate((widget) => widget is ButtonStyleButton),
        findsNWidgets(2),
      );
      expect(
        tester.getRect(_button('Nyt Spil')).bottom,
        lessThan(tester.getRect(_button('Jeg ser en bolig')).top),
      );
    },
  );

  testWidgets('both buttons are enabled', (tester) async {
    await _pumpStartScreen(tester, _phoneSize);

    for (final label in ['Nyt Spil', 'Jeg ser en bolig']) {
      expect(tester.widget<FilledButton>(_button(label)).enabled, isTrue);
    }
  });

  for (final (name, size) in [
    ('phone', _phoneSize),
    ('desktop', _desktopSize),
  ]) {
    testWidgets('buttons are centred and equal width at $name width', (
      tester,
    ) async {
      await _pumpStartScreen(tester, size);

      final top = tester.getRect(_button('Nyt Spil'));
      final bottom = tester.getRect(_button('Jeg ser en bolig'));
      final group = top.expandToInclude(bottom);

      expect(top.width, bottom.width);
      expect(top.left, bottom.left);
      expect(top.width, lessThanOrEqualTo(StartScreen.buttonMaxWidth));
      expect(group.center.dx, moreOrLessEquals(size.width / 2));
      expect(group.center.dy, moreOrLessEquals(size.height / 2));
    });
  }

  testWidgets('tapping either button does not throw or navigate', (
    tester,
  ) async {
    await _pumpStartScreen(tester, _phoneSize);

    for (final label in ['Nyt Spil', 'Jeg ser en bolig']) {
      await tester.tap(_button(label));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.byType(StartScreen), findsOneWidget);
      expect(find.byType(Scaffold), findsOneWidget);
    }
  });
}

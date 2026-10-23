import 'package:boliggaet/features/home/presentation/home_view_model.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('HomeViewModel starts at 0 and increments', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Keep the autoDispose provider alive for the duration of the test.
    final subscription = container.listen(homeViewModelProvider, (_, _) {});

    expect(subscription.read(), 0);

    container.read(homeViewModelProvider.notifier).increment();

    expect(subscription.read(), 1);
  });
}

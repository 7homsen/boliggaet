import 'package:flutter_riverpod/flutter_riverpod.dart';

/// ViewModel for [HomeScreen].
///
/// Holds the screen's state (here: a simple counter) and the actions the
/// View can trigger. Replace with real state as the feature grows.
class HomeViewModel extends Notifier<int> {
  @override
  int build() => 0;

  void increment() => state = state + 1;
}

final homeViewModelProvider =
    NotifierProvider.autoDispose<HomeViewModel, int>(HomeViewModel.new);

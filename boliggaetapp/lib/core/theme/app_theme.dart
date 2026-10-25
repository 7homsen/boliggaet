import 'package:flutter/material.dart';

/// App-wide theme definitions.
abstract final class AppTheme {
  static final ThemeData light = ThemeData(
    colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
  );
}

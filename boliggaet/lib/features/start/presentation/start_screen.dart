import 'package:flutter/material.dart';

/// The page shown at app start, where the user picks what to do.
class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  static const double buttonMaxWidth = 320;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: buttonMaxWidth),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // The pages behind these buttons come in later specs.
                  FilledButton(onPressed: () {}, child: const Text('Nyt Spil')),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () {},
                    child: const Text('Jeg ser en bolig'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

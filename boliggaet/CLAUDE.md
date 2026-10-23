# Boliggaet – instructions for Claude

## Project
- Flutter app (Dart SDK ^3.13), targets Android and iOS
- Architecture: MVVM with Riverpod (`flutter_riverpod`)
- Lints: `flutter_lints` via `analysis_options.yaml`

## Commands
- Get packages: `flutter pub get`
- Run: `flutter run`
- Analyze: `flutter analyze` (must pass with no issues before a task is done)
- Test: `flutter test` (must pass before a task is done)
- Format: `dart format .`

## Architecture (MVVM with Riverpod)
- **Model**: data classes and repositories. Repositories handle all data access (API, local storage) and are exposed as plain `Provider`s.
- **ViewModel**: one per screen, a `Notifier` or `AsyncNotifier` (use `AsyncNotifier` when the screen loads data). Holds the screen's state and the methods the View calls. Gets repositories via `ref.read` / `ref.watch` — never constructs them directly.
- **View**: a `ConsumerWidget` (or `ConsumerStatefulWidget` only when it needs controllers/animations). Only reads ViewModel state and calls ViewModel methods. No business logic, no direct repository or API calls in widgets.
- Use `AsyncValue` (`.when(...)`) for loading/error/data states instead of manual `isLoading`/error flags.
- Use `autoDispose` providers for screen ViewModels so they are cleaned up when the screen closes.
- Write providers by hand; do not use Riverpod code generation (`@riverpod`) unless I ask for it.
- Do not use the `provider` package, `ChangeNotifier` for app state, Bloc, or GetX.

## Folder structure
Feature-first:
```
lib/
  main.dart                    # ProviderScope + app root
  core/                        # shared widgets, theme, utils, constants
  features/
    <feature>/
      data/                    # models, repositories (+ their providers)
      presentation/            # views (screens/widgets) and view models
test/
  features/<feature>/          # mirrors lib/
```
- File names in `snake_case`, e.g. `home_screen.dart`, `home_view_model.dart`, `bolig_repository.dart`.

## Code style
- Follow `analysis_options.yaml`; prefer `const` constructors and `final` fields.
- Immutable state classes; update state by assigning a new value (`state = ...`), never by mutating.
- Keep widgets small; extract sub-widgets into their own classes rather than helper methods returning widgets.
- Full null safety; avoid `!` unless it is clearly safe.
- Code, identifiers and comments in English. User-facing UI text in Danish.

## Testing
- Write unit tests for new ViewModel and repository logic.
- In tests, override repository providers with fakes via `ProviderContainer(overrides: [...])` or `ProviderScope(overrides: [...])`.

## How I want you to work
- For larger changes, briefly explain your plan before writing code.
- Ask before adding any new package to `pubspec.yaml`.
- Keep changes focused on the task; don't refactor unrelated code without asking.
- Run `flutter analyze` and `flutter test` after changes and fix what you broke.
- Don't commit or push unless I ask.

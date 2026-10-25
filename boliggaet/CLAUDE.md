# Boliggaet – instructions for Claude

## Project
- Flutter app (Dart SDK ^3.13), targets Android, iOS and web
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
- Code in `lib/` must run on Android, iOS and web: no `dart:io` or other platform-only APIs in shared code. Before proposing a new package, check that it supports all three platforms.
- Layouts must work from phone to desktop browser widths.

## Design principles
Apply SOLID, DRY, KISS and YAGNI pragmatically. When they pull in different directions, choose the simpler code.
- **Single responsibility**: views render, view models hold screen state and actions, repositories do data access. Put non-trivial validation or formatting logic in its own class or function (in the feature, or `core/` if shared), never in widgets.
- **Open/closed**: add behaviour by adding a new implementation or class rather than growing `if`/`switch` chains on type in existing code.
- **Liskov substitution**: every implementation must honour its interface's contract: accept the same inputs, return the same kind of result, throw no new kinds of exceptions. No `UnimplementedError` stubs.
- **Interface segregation**: keep repository interfaces small and feature-specific. Split one when callers only use part of it.
- **Dependency inversion**: depend on abstractions provided through Riverpod (`ref.watch` / `ref.read`), never construct dependencies inside view models or widgets. Repository interfaces are worth it even with one real implementation, because the test fake is the second.
- **DRY**: extract a shared widget, function or class when the same logic appears the third time, not before. Shared code goes in `core/`. Prefer composition (small widgets and classes) over mixins.
- **KISS**: use Flutter's built-in widgets and plain Dart before custom solutions. Clear names over explanatory comments. Small widgets and short methods.
- **YAGNI**: build only what the current task needs. No speculative parameters, configuration options, base classes or "just in case" abstractions, and no optimisation without a measured problem.

## Implementation spec
- `docs/implementation-spec.md` is the overview of the whole app as it is currently built. Keep it up to date: update it in the same change whenever you add, remove or change a page, a page's purpose, or the navigation between pages.
- Keep it high-level: the app's purpose, each page (how it's reached, what it's for, its main actions), and a navigation map. No class names, state details or code.
- Describe what is built, not what is planned. Planned work lives in `docs/specs/<slug>/`.

## Testing
- Write unit tests for new ViewModel and repository logic.
- In tests, override repository providers with fakes via `ProviderContainer(overrides: [...])` or `ProviderScope(overrides: [...])`.

## How I want you to work
- For larger changes, briefly explain your plan before writing code.
- Ask before adding any new package to `pubspec.yaml`.
- Keep changes focused on the task; don't refactor unrelated code without asking.
- Run `flutter analyze` and `flutter test` after changes and fix what you broke.
- Don't commit or push unless I ask.
  - Exception: when I run the `implement-spec` skill, feature implementers may commit on their own git worktree branches so their work can be merged. Never commit on `main` and never push without asking.

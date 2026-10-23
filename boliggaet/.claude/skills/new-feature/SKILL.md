---
name: new-feature
description: Scaffold a new feature in the Boliggaet Flutter app - data/ and presentation/ folders with a model, repository + provider, AsyncNotifier view model, ConsumerWidget screen, and unit tests - following CLAUDE.md. Use when the user asks to add/create/scaffold a new feature, screen or page.
argument-hint: <feature_name> [ModelName]
---

# New feature scaffold

Arguments: $ARGUMENTS

Creates a feature that follows the MVVM + Riverpod rules and the feature-first layout in `CLAUDE.md`. The code to generate is in [templates.md](templates.md), written for an example feature `listings` with model `Listing`.

## 1. Settle the names

Work out these from the arguments or the user's request. If something can't be inferred, ask once with all the open questions together.

| Placeholder in templates | Meaning | Example |
|---|---|---|
| `listings` | feature folder and file prefix, `snake_case` | `saved_searches` |
| `Listings` | feature in PascalCase (screen, view model) | `SavedSearches` |
| `listings` (in identifiers) | feature in lowerCamelCase (`listingsViewModelProvider`) | `savedSearchesViewModelProvider` |
| `listing` | model file name, `snake_case`, singular | `saved_search` |
| `Listing` | model class, PascalCase, singular | `SavedSearch` |
| `listing` (in identifiers) | model in lowerCamelCase (`listingRepositoryProvider`) | `savedSearchRepositoryProvider` |
| `fetchListings` | repository method | `fetchSavedSearches` |
| Danish UI strings | screen title, empty/error/retry texts | `Gemte søgninger`, `Ingen gemte søgninger endnu.` |

Model fields: use the fields the user names. Otherwise keep `id` + `title` and tell the user they are placeholders.

## 2. Check before writing

- If `lib/features/<feature>/` already exists, stop and ask. Never overwrite an existing feature.
- Briefly tell the user which files you are about to create (see list below), then create them.

## 3. Create the files

```
lib/features/<feature>/
  data/
    <model>.dart                      # immutable model
    <model>_repository.dart           # interface + in-memory impl + Provider
  presentation/
    <feature>_screen.dart             # ConsumerWidget, AsyncValue.when, Danish UI text
    <feature>_view_model.dart         # AsyncNotifier + autoDispose provider
test/features/<feature>/
  data/<model>_repository_test.dart
  presentation/<feature>_view_model_test.dart
```

Copy each template from [templates.md](templates.md) and apply the renames consistently: file names, class names, provider names, imports (`package:boliggaet/features/<feature>/...` in tests), doc comments and test descriptions.

Rules (from `CLAUDE.md`, don't break them while adapting):
- Providers are written by hand: no `@riverpod` code generation.
- The view model gets the repository via `ref.watch` / `ref.read`, never constructs it.
- The screen only reads view model state and calls view model methods. Sub-widgets are private classes, not helper methods.
- State is immutable. Update by assigning `state = ...`.
- Code and comments in English, user-facing text in Danish.
- Don't add packages to `pubspec.yaml`. If the feature seems to need one, ask first.

## 4. Don't wire it up unasked

Don't change `main.dart`, navigation or other features unless the user asked for that. In your summary, say how to show the screen, e.g. `home: const ListingsScreen()` or `Navigator.push(context, MaterialPageRoute(builder: (_) => const ListingsScreen()))`.

## 5. Verify

Run from the project root and fix anything you broke:

```
dart format lib/features/<feature> test/features/<feature>
flutter analyze
flutter test
```

Both `flutter analyze` and `flutter test` must pass before you report the feature as done.

## 6. Report

List the files created, which names and fields are placeholders (the in-memory repository's sample data, the `id`/`title` fields), and how to show the screen. Don't commit unless the user asks.

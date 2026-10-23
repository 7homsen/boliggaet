# Templates for the new-feature skill

Example feature `listings` with model `Listing`. Rename as described in SKILL.md.

## lib/features/listings/data/listing.dart

```dart
/// A single listing.
class Listing {
  const Listing({required this.id, required this.title});

  final String id;
  final String title;
}
```

## lib/features/listings/data/listing_repository.dart

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'listing.dart';

/// Data access for [Listing]s.
abstract interface class ListingRepository {
  Future<List<Listing>> fetchListings();
}

/// In-memory implementation used until a real data source exists.
class InMemoryListingRepository implements ListingRepository {
  const InMemoryListingRepository();

  @override
  Future<List<Listing>> fetchListings() async => const [
    Listing(id: '1', title: 'Eksempel 1'),
    Listing(id: '2', title: 'Eksempel 2'),
  ];
}

final listingRepositoryProvider = Provider<ListingRepository>(
  (ref) => const InMemoryListingRepository(),
);
```

## lib/features/listings/presentation/listings_view_model.dart

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/listing.dart';
import '../data/listing_repository.dart';

/// ViewModel for [ListingsScreen].
///
/// Loads the listings from [ListingRepository] and exposes them as an
/// [AsyncValue] so the View can show loading, error and data states.
class ListingsViewModel extends AsyncNotifier<List<Listing>> {
  @override
  Future<List<Listing>> build() =>
      ref.watch(listingRepositoryProvider).fetchListings();

  /// Reloads the listings, showing the loading state meanwhile.
  Future<void> refresh() async {
    state = const AsyncLoading();
    final result = await AsyncValue.guard(
      () => ref.read(listingRepositoryProvider).fetchListings(),
    );
    if (ref.mounted) state = result;
  }
}

final listingsViewModelProvider =
    AsyncNotifierProvider.autoDispose<ListingsViewModel, List<Listing>>(
      ListingsViewModel.new,
    );
```

## lib/features/listings/presentation/listings_screen.dart

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/listing.dart';
import 'listings_view_model.dart';

class ListingsScreen extends ConsumerWidget {
  const ListingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listings = ref.watch(listingsViewModelProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Annoncer')),
      body: listings.when(
        data: (items) =>
            items.isEmpty ? const _EmptyView() : _ListingList(listings: items),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, _) => _ErrorView(
          onRetry: () => ref.read(listingsViewModelProvider.notifier).refresh(),
        ),
      ),
    );
  }
}

class _ListingList extends StatelessWidget {
  const _ListingList({required this.listings});

  final List<Listing> listings;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: listings.length,
      itemBuilder: (context, index) => _ListingTile(listing: listings[index]),
    );
  }
}

class _ListingTile extends StatelessWidget {
  const _ListingTile({required this.listing});

  final Listing listing;

  @override
  Widget build(BuildContext context) {
    return ListTile(title: Text(listing.title));
  }
}

class _EmptyView extends StatelessWidget {
  const _EmptyView();

  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('Ingen annoncer endnu.'));
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Noget gik galt.'),
          const SizedBox(height: 8),
          FilledButton(onPressed: onRetry, child: const Text('Prøv igen')),
        ],
      ),
    );
  }
}
```

## test/features/listings/data/listing_repository_test.dart

```dart
import 'package:boliggaet/features/listings/data/listing_repository.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('InMemoryListingRepository returns sample listings', () async {
    const repository = InMemoryListingRepository();

    final listings = await repository.fetchListings();

    expect(listings, isNotEmpty);
  });
}
```

## test/features/listings/presentation/listings_view_model_test.dart

```dart
import 'package:boliggaet/features/listings/data/listing.dart';
import 'package:boliggaet/features/listings/data/listing_repository.dart';
import 'package:boliggaet/features/listings/presentation/listings_view_model.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeListingRepository implements ListingRepository {
  FakeListingRepository({this.listings = const [], this.error});

  List<Listing> listings;
  Object? error;

  @override
  Future<List<Listing>> fetchListings() async {
    final error = this.error;
    if (error != null) throw error;
    return listings;
  }
}

ProviderContainer createContainer(ListingRepository repository) {
  final container = ProviderContainer(
    overrides: [listingRepositoryProvider.overrideWithValue(repository)],
    // Disable Riverpod's automatic retry so errors surface immediately.
    retry: (_, _) => null,
  );
  addTearDown(container.dispose);
  // Keep the autoDispose view model alive for the duration of the test.
  container.listen(listingsViewModelProvider, (_, _) {});
  return container;
}

void main() {
  test('loads listings from the repository', () async {
    final container = createContainer(
      FakeListingRepository(
        listings: const [Listing(id: '1', title: 'A')],
      ),
    );

    final listings = await container.read(listingsViewModelProvider.future);

    expect(listings.map((l) => l.id).toList(), ['1']);
  });

  test('exposes repository errors as AsyncError', () async {
    final container = createContainer(
      FakeListingRepository(error: Exception('boom')),
    );

    await expectLater(
      container.read(listingsViewModelProvider.future),
      throwsException,
    );
    expect(container.read(listingsViewModelProvider), isA<AsyncError>());
  });

  test('refresh reloads from the repository', () async {
    final repository = FakeListingRepository(
      listings: const [Listing(id: '1', title: 'A')],
    );
    final container = createContainer(repository);
    await container.read(listingsViewModelProvider.future);

    repository.listings = const [Listing(id: '2', title: 'B')];
    await container.read(listingsViewModelProvider.notifier).refresh();

    final listings = container.read(listingsViewModelProvider).value;
    expect(listings?.map((l) => l.id).toList(), ['2']);
  });
}
```

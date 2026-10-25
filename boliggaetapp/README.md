# Boliggaet

A price-guessing game about real estate in Denmark, for Android, iOS and web.

The app is fed data about current property listings in Denmark. Each round shows a listing's images, floor plans, statistics and location, but never its price. The player guesses the price, and the real price is revealed before the next round. Each guess earns up to 1000 points depending on how close it was, but the points stay hidden until the end.

## Game modes

- **Nyt Spil (five rounds):** guess the price of five listings in a row, then see your points per round and your final score, out of 5000.
- **Jeg ser en bolig (nearby listing):** when you're physically close to a listing, play the game with that specific listing.

## Status

Early development. The start page with the two mode buttons exists; the game modes themselves are not built yet. See [docs/implementation-spec.md](docs/implementation-spec.md) for what is currently built.

## Development

Flutter app using MVVM with Riverpod. Project conventions are in [CLAUDE.md](CLAUDE.md).

```
flutter pub get      # get packages
flutter run          # run the app
flutter analyze      # static analysis
flutter test         # run tests
dart format .        # format code
```

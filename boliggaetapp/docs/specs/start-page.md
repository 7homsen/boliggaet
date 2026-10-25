# Spec: Start page

## Goal
When the app opens, the user lands on a start page where they choose between two options: starting a new game or registering a home they are looking at.

## What to build
- A new **start page** that is shown when the app starts.
- It replaces the template counter page (Home) as the app's first page. The counter page and its + button are removed.
- The page shows two buttons, with this exact Danish text:
  1. **Nyt Spil**
  2. **Jeg ser en bolig**
- The two buttons are stacked vertically, "Nyt Spil" on top and "Jeg ser en bolig" below it.
- The pair of buttons is centred on the page, both horizontally and vertically.
- Both buttons have the same width, so they line up as a neat column.

## Behaviour
- Tapping a button does nothing yet. The pages behind "Nyt Spil" and "Jeg ser en bolig" will come in later specs. The buttons must still look and behave as normal, enabled buttons (not greyed out).

## Layout and styling
- Works from phone to desktop browser widths: on wide screens the buttons keep a sensible fixed or maximum width and stay centred instead of stretching across the screen.
- Uses the app's existing Material 3 theme (deep purple seed colour). No new colours, fonts or branding.
- No other content on the page is required.

## Out of scope
- The pages or flows behind either button.
- Navigation/routing setup beyond what is needed to show the start page at app start.
- App logo, title artwork, dark mode or other styling changes.

## Acceptance (for reference)
- On app start the start page is shown, and the old counter page is no longer reachable.
- The page shows exactly two buttons, "Nyt Spil" above "Jeg ser en bolig".
- The buttons are centred horizontally and vertically, at phone width and at desktop width.
- Both buttons have the same width and are enabled.
- Tapping either button does not throw and does not navigate anywhere.

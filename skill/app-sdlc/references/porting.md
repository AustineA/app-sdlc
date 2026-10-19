# Porting to the missing platform

The goal is 1:1 feature parity, proven feature by feature, not a rewrite that "should" match.

## Contents
- Parity matrix
- Order of work
- iOS → Android (SwiftUI → Kotlin/Compose) mapping
- Android → iOS notes
- QA loop
- Gotchas we hit

## Parity matrix
Before writing code, walk the source app and write `.release/parity.md`, one row per feature:

| Area | Feature | Source files | Target files | Tested how | Status |
|---|---|---|---|---|---|

Include things that are easy to forget:
- Onboarding branches, and the empty, error and lapsed-subscription states.
- Deep links and URL schemes, widgets, local notification schedules, push handling.
- Haptics, review prompt, settings pages, account deletion, sign-out.
- Theme variants and dark mode, every localized string, demo or debug data switches (used later for screenshots).

## Order of work
1. Project skeleton, build config, theme tokens, fonts, string generation.
2. Models and storage. Decode tolerantly: every field defaulted, unknown fields ignored, so old saves and server changes don't crash.
3. API client and sync. Point it at the same backend, with a debug base URL for a local server.
4. Core screens, then secondary screens, then settings.
5. Notifications, then widgets, then polish (haptics, animation, review prompt).

Mirror the source app's file layout and type names, so a later diff between the platforms is easy to read.

## iOS → Android mapping (what worked)
- **Stack:** Kotlin + Jetpack Compose (BOM), kotlinx.serialization, OkHttp, coroutines. Navigation is plain state, a per-tab back stack in an `AppNavigation` class, rather than navigation-compose when the iOS app uses its own `AppNavigation`.
- **Observable store:** one store class holding Compose `mutableStateOf`. Its state setter mirrors Swift `didSet`: persist, re-time, update widgets, push settings.
- **Theme:** tokens in a `Theme` data class, resolved through a `CompositionLocal`. Set `android:forceDarkAllowed=false` in values-v29 and values-v31 themes, so OEM "force dark" doesn't invert hand-tuned light surfaces (paper cards turned dark on a Samsung).
- **Fonts:** Apple-only fonts (Noteworthy, SF Rounded) need an OFL lookalike bundled in `res/font`. Use synthetic bold and scale if the weight is missing.
- **Strings:** generate `values-*/strings.xml` from the iOS `Localizable.xcstrings` with a script. Use a TSV mapping resource name → iOS key (`~` for plurals, `!` for Android-only English) and a JSON file of Android-only translations. Never hand-edit the generated XML. Convert `%@` to `%1$s` and escape apostrophes.
- **Sheets:** use `ModalBottomSheet` with `rememberModalBottomSheetState`. Any `confirmValueChange` lambda must be stable (`remember` + `rememberUpdatedState`). Otherwise the sheet state is recreated on recomposition, and the sheet closes and reopens on the first keystroke.
- **Notifications:** for local reminders, use `AlarmManager.setWindow` (a 10-minute window, no exact-alarm permission) plus a receiver for reboot and time changes. Use separate notification channels per kind, translated. Ask for POST_NOTIFICATIONS on API 33+.
- **Widgets:** a Glance app widget. **A live Glance session does not re-run `provideGlance` on update**, so feed the composition from a `MutableStateFlow` snapshot that every update refreshes (state + `now`). Otherwise the widget keeps the board it was first drawn with. Tick on minute/hour boundaries with an inexact `AlarmManager.set`; exact alarms need a restricted permission. Pass `previewImage`, `targetCellWidth`/`Height` and `minResize*`. Lock-screen widgets have no Android phone equivalent.
- **Haptics:** `HapticFeedbackConstants` on the view, with a `Vibrator` fallback.
- **Review prompt:** Play In-App Review (`review-ktx`), at the same moments as the iOS prompt.
- **Deep links:** an intent filter for the custom scheme. Handle `onNewIntent` too, not just `onCreate`.

## Android → iOS notes
SwiftUI + Observation, a `Localizable.xcstrings` catalog, WidgetKit with timeline entries on minute/hour boundaries, local notifications via `UNCalendarNotificationTrigger`, StoreKit through RevenueCat. Mark anything SwiftUI calls off the main thread as `nonisolated` when the target uses MainActor default isolation.

## QA loop (per feature)
1. Build: `./gradlew :app:assembleDebug`, or `xcodebuildmcp` for iOS.
2. Install on a running emulator or simulator. Pick devices with the argent `list-devices` tool, or `adb devices`.
3. Exercise the feature as a user would: tap, type, background and foreground, rotate if relevant. Compare against the source app on its own simulator.
4. Multi-user features: two emulators signed in as two people on one board or pair, then an iOS + Android pair. Check that each side sees the other's change.
5. Fix, rebuild, and re-check before marking the row done.

Use a local backend (for example Rails on `:3000`). The emulator reaches the host at `10.0.2.2`, so add a **debug-only** network security config allowing cleartext to `10.0.2.2` and `localhost`.

## Gotchas we hit
- **Emulator IME drops characters** from automated typing. Use `adb shell input text "Hello%sworld"` and turn off `stylus_handwriting_enabled`.
- **adb UI dumps beat stale screen streams.** Use `uiautomator dump` + `screencap` when a tool's screen stream freezes.
- **OkHttp throws on body-less POST/PUT/PATCH.** Send `{}`.
- **Debug demo boards** that are never persisted can't be shown by widgets, which read saved state. Test widgets with real data.
- **Emulators have no Play billing** unless signed in to Play. In debug builds, offer a "skip paywall" when offerings fail to load, and grant Pro on the local backend to test paid paths.
- **An ANR blaming a background job** while the main thread waits in `RenderProxy::setStopped` is the emulator's GPU stalling on a starved host, not app code.
- **iOS simulator:** an old build with the same URL scheme hijacks deep links. Uninstall it.
- **Notification-type FCM messages** aren't delivered to `onMessageReceived` while the app is backgrounded. The system shows them itself, so a widget won't refresh from them. That matches iOS alert pushes; use data messages only if it matters.

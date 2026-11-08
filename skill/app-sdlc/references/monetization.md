# Monetization: App Store, Google Play, RevenueCat

## Contents
- Product shape
- App Store Connect (API)
- Google Play (API)
- RevenueCat
- RevenueCat Test Store (debug and simulator builds)
- Account identity, restore and sign-in
- App integration and policy
- Backend
- Verification
- Gotchas

## Product shape
Ask for prices only if no sibling app sets the pattern. The default that worked is a yearly plan (no trial) and a weekly plan with a 3-day free trial, one entitlement (`pro`), and one offering (`default`) with `$rc_annual` and `$rc_weekly`. Use the same product ids on both stores (`<slug>_yearly`, `<slug>_weekly`).

## App Store Connect (API)
- Create the subscription group, then each subscription (`productId`, `subscriptionPeriod`, `groupLevel`), then localizations.
- Prices: read the equalized price points for the base territory and apply them to every territory (175).
- Introductory offer: a free trial on the weekly plan.
- Each subscription needs a **review screenshot** (the paywall) before the first submission. Status should reach READY_TO_SUBMIT.
- READY_TO_SUBMIT is not submitted. The first subscriptions must go into the **same review submission as the app version**, through the web UI only. Otherwise review rejects the app under 2.1(b). See "First submission with subscriptions" in `store-forms.md`.

## Google Play (API)
- `monetization.subscriptions.create` with a base plan (`yearly` P1Y, or `weekly` P1W, auto-renewing). Get regional prices from `monetization.convertRegionPrices` with the USD price, then activate the base plan.
- Free trial: an offer (`free-trial`) on the weekly base plan with a P3D free phase, eligibility "new customer acquisition", then activate it.
- RevenueCat ids for Play products are `<productId>:<basePlanId>` (for example `app_weekly:weekly`).

## RevenueCat
- **Project:** reuse the app's existing project if it has one. Each store gets its own app inside it, with the bundle id or package. Each store app needs credentials:
  - **iOS:** the in-app purchase key and an ASC API key. Choose existing keys in the picker; uploading `.p8` files through the browser gets blocked.
  - **Play:** a service-account JSON with financial-data access, either uploaded or picked.
- **Products:** "Import" from the store, then attach them to entitlement `pro`. Create packages in the default offering and attach a product per store to each.
- **Webhook:** point it at the backend `/…/revenuecat-webhook` with a bearer secret kept in server credentials. Send a test event and expect 200.
- **Driving it without the dashboard UI:** RevenueCat's internal API works from a logged-in dashboard page (`/internal/v1/developers/me/projects/<id>/...` with header `X-Requested-With: XMLHttpRequest`). The useful calls are `entitlements/<id>/attach_products {products_ids}`, `POST packages {offering_id, identifier}` and `packages/<id>/attach_products`.
- **Check that the SDK keys belong to this project.** Grep sibling repos for the `goog_`/`appl_` value; a key copied from another app is a common mistake and silently points purchases at the wrong project. If the RC project has no Play app, create it (Apps → New app → Google Play Store, package name) and copy its key with the copy button + `pbpaste`.
- The service-account JSON upload in RC is a native file picker that Argent can't drive reliably. Set it through RC API v2 instead: create a v2 secret key (API keys → New secret API key → V2, Project configuration: Read & write), copy it with the copy button, then `POST /v2/projects/<proj>/apps/<app>` with `{"play_store":{"package_name":…,"play_service_account_credentials_json":"<file contents>"}}` using **curl** (Python urllib timed out). Expect `play_service_account_credentials_configured: true`. The account's existing `*-revenuecat.json` key usually already has access; prove it with a package-scoped Play read.
- Public SDK keys (`appl_…`, `goog_…`) go in gitignored config: an xcconfig on iOS, `local.properties` → `BuildConfig` on Android.

## RevenueCat Test Store (debug and simulator builds)
**Always set this up.** Debug and simulator builds buy through RevenueCat's Test Store, so the paywall, purchase, unlock and sign-in flow can be run end to end on a simulator or emulator with no StoreKit config, sandbox account or Play licence tester. Purchases show a "Test Store Purchase" sheet with *Test valid purchase* / *Test failed purchase* / *Cancel*. Release builds keep the real `appl_`/`goog_` keys. This is how Grain and Last Summer are tested, and how the "paid but can't get back in" bug was reproduced and fixed.

**Set it up in RevenueCat** (internal API from the logged-in dashboard; see `browser-automation.md` for running `fetch` in the page with Argent `debugger-evaluate`). Base path `/internal/v1/developers/me/projects/<proj>/`, header `X-Requested-With: XMLHttpRequest`, plus `Content-Type: application/json` on writes:
1. **Find the Test Store app.** `GET apps` → the entry with `type: "test_store"`. Projects created since 2026 come with one (often holding unused `weekly`/`yearly` placeholder products); create it in the dashboard if it's missing.
2. **Create products with the real store ids**, so code that branches on product id (`last_summer_weekly`, `<slug>_yearly`) behaves the same: `POST apps/<testApp>/products` with `{identifier, display_name, title, duration: "P1W"|"P1Y", product_type: "subscription"}`.
   - Don't send `is_subscription` ("Illegal parameters").
   - `display_name` must be unique within the app, so the placeholder "Weekly" blocks a second "Weekly". Use "<App> Weekly".
   - Only `subscription` worked. `non_consumable` returned "Invalid product type" even with prices, so lifetime/one-time products can't be tested in the Test Store. Say so in the report.
3. **Price every product:** `POST products/<id>/prices` with `{prices: [{currency: "USD", price: 6.99}]}`. **Without a price the SDK can't fetch any Test Store product** and offerings come back empty: "None of the Test Store products registered in the RevenueCat dashboard could be fetched". Use the real USD prices when they're known.
4. **Attach them:** `POST entitlements/<id>/attach_products {products_ids}`, and `POST packages/<id>/attach_products {products_ids}` for the matching package (`$rc_weekly`, `$rc_annual`) in **every offering the app reads**. Grep the code for `offerings.current` and `offerings.all["…"]`; an in-app paywall often uses a second offering.
5. **Read the public key:** `GET apps/<testApp>` → `api_key.key` (`test_…`). It's a public SDK key, like `appl_`.

**Wire it into the app** (the key is used only in debug builds):
- **Expo / React Native:** `EXPO_PUBLIC_RC_TEST_API=test_…` in `.env.development`, and pick it in the configure call:
  ```ts
  const testKey = process.env.EXPO_PUBLIC_RC_TEST_API;
  const apiKey = __DEV__ && testKey ? testKey
    : Platform.OS === "ios" ? process.env.EXPO_PUBLIC_RC_IOS_API : process.env.EXPO_PUBLIC_RC_ANDROID_API;
  Purchases.configure({ apiKey });
  ```
  `EXPO_PUBLIC_*` values are inlined at bundle time, so restart Metro with `--clear` after changing them. Check that `.env*` actually defines the real keys too; they may only exist in `eas.json`. A local build with no key crashes in `configure`.
- **Native iOS:** in the gitignored `Secrets.xcconfig`, `REVENUECAT_API_KEY = appl_…` followed by `REVENUECAT_API_KEY[config=Debug] = test_…`. The conditional line must come **after** the plain one. Read it from Info.plist.
- **Native Android:** `buildConfigField` with the `test_` key in `debug {}` and the `goog_` key in `release {}`, both read from `local.properties`.
- **Flutter:** choose the key with `kDebugMode`.

**Test with it:**
- Run the app's own onboarding → paywall → purchase on the simulator, and tap *Test valid purchase*. The app must unlock, sign in and leave the paywall. *Test failed purchase* and *Cancel* must leave the user on the paywall with a usable button.
- **To test against the production backend** (webhook races and real sign-in), temporarily point the dev API URL at production and restart Metro with `--clear`. Use a **second booted simulator** for a brand-new user: iOS keeps Keychain items across uninstall, so a reinstall on the same simulator is not a new user. Put the URL back afterwards. Each run creates one test user in production; say so in the report.
- **Limit: the Test Store can't restore across accounts.** `restorePurchases` logs "Restoring purchases not available in Test Store" and returns the current customer. Same-account flows (sign out → Restore, relaunch) are testable. Reinstall/new-phone restore needs a sandbox purchase on a device before release; list that as unverified.
- Record the Test Store app id, product ids and the env var in project memory.

## Account identity, restore and sign-in
Most "I paid but can't log in" reports come from the app user id drifting between RevenueCat, the device and the backend. Hold these invariants, and audit any existing app against them:
- **One account id everywhere.** Generate a uuid once and store it in the Keychain/secure storage (on iOS it survives reinstall). Use it as the RevenueCat `appUserID` (`logIn(id)` before every purchase and restore) **and** as the backend user id. Every sign-in path (login, post-purchase, restore) goes through **one shared helper**; three hand-copied versions drift.
- **Never sign in with `customerInfo.originalAppUserId`.** For a customer who started anonymous it's `$RCAnonymousID:…`. Signing in with it creates a new, unpaid backend user and moves RevenueCat onto an empty customer: the user is let in but shown as free. If such an id was ever saved as the account id, treat it as missing (make a fresh uuid) and let restore move the purchases over.
- **Restore must call `Purchases.restorePurchases()`**, not just `getCustomerInfo()`. Reading the current customer finds nothing on a reinstall or a new phone. The order is: `logIn(accountId)` → `restorePurchases()` → if an entitlement is active, sign in to the backend → apply RevenueCat's subscription on top of the backend's copy (the webhook may not have landed) → open the app. When nothing is active, say so ("No Active Subscription"); don't fail silently.
- **After a purchase, keep the button loading through backend sign-in, retry sign-in briefly, and show an error if it still fails.** A user who just paid must never be left idle on the paywall with no feedback. Restore must then be able to finish the sign-in.
- **Hard paywalls need a visible way back in.** If onboarding ends on a paywall with no close or login button, Restore is the only path back for a returning payer, so it must work from a signed-out state.
- Sign-out clears the session token but keeps the account id, so Restore or sign-in lands on the same paid account.

## App integration and policy
- Configure the SDK with the backend user id as `appUserID`, so webhooks map to users. Log in again after account linking.
- **Play policy: no paywall inside Android onboarding.** Create the account or board first, and show the paywall when the user tries the paid action. A user who never subscribed must be able to close it immediately.
- Keep a once-per-launch prompt only for owners whose subscription has ended. Detect that as a RevenueCat entitlement that exists but is inactive.
- Lapsed state: lock nothing; existing content stays readable and the paid action prompts. If one person pays for a pair, the partner sees "paused" with the owner's name.
- Debug builds use the RevenueCat Test Store (above), so simulators and emulators without Play billing or a sandbox account can still buy. Don't add a "skip the paywall" path for debug builds.

## Backend
- The webhook updates `pro_expires_at` (or similar).
- The paid-action guard falls back to asking RevenueCat (`GET /v1/subscribers/<id>` with the secret or public key) before refusing, because a fresh purchase can beat the webhook.

## Verification
- **Test Store, on a simulator and an emulator, driven with Argent:** a debug build loads the Test Store offerings with prices. Onboarding → paywall → *Test valid purchase* unlocks the app and leaves the paywall. Relaunch keeps the user in and Pro. Settings → Sign out → paywall → Restore comes back **Pro** (check the Settings subscription row, not just "the app opened"). Run the purchase once more against the production backend from a fresh simulator.
- Offerings load with real prices on each platform. On iOS that needs a sandbox account; on Android, an internal-track install from Play or a licence tester.
- A real or sandbox purchase unlocks the paid action; restore works on a reinstall (this one can't be done in the Test Store); cancelling leads to the lapsed state.
- The webhook test returns 200, and a purchase event updates the user's row.

## Gotchas
- Play's subscription APIs need the app to have a billing-enabled AAB uploaded (the `com.android.vending.BILLING` permission comes with the RevenueCat SDK).
- "Billing service unavailable" on an emulator is the device, not the code.
- Keep the iOS and Android prices in step; `convertRegionPrices` keeps Play's local prices sensible.
- When reading offerings, note packages that have a product for only one store: that plan is hidden on the other platform. It can be deliberate (a secondary offering may sell weekly + lifetime on iOS but yearly on Play), so ask before "fixing" it, and mirror the same per-platform plans when attaching Test Store products.
- **Xcode 27 simulator builds** of apps with `.metal` files fail with "missing Metal Toolchain" until `xcodebuild -downloadComponent MetalToolchain` (~840 MB) has run. Check `df -h` before building: a full disk shows up as unrelated build errors and then blocks the shell entirely.

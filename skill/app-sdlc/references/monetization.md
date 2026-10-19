# Monetization: App Store, Google Play, RevenueCat

## Contents
- Product shape
- App Store Connect (API)
- Google Play (API)
- RevenueCat
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
- Public SDK keys (`appl_…`, `goog_…`) go in gitignored config: an xcconfig on iOS, `local.properties` → `BuildConfig` on Android.

## App integration and policy
- Configure the SDK with the backend user id as `appUserID`, so webhooks map to users. Log in again after account linking.
- **Play policy: no paywall inside Android onboarding.** Create the account or board first, and show the paywall when the user tries the paid action. A user who never subscribed must be able to close it immediately.
- Keep a once-per-launch prompt only for owners whose subscription has ended. Detect that as a RevenueCat entitlement that exists but is inactive.
- Lapsed state: lock nothing; existing content stays readable and the paid action prompts. If one person pays for a pair, the partner sees "paused" with the owner's name.
- Debug builds: a "skip" path when offerings can't load (emulators without Play billing, simulators without a sandbox account).

## Backend
- The webhook updates `pro_expires_at` (or similar).
- The paid-action guard falls back to asking RevenueCat (`GET /v1/subscribers/<id>` with the secret or public key) before refusing, because a fresh purchase can beat the webhook.

## Verification
- Offerings load with real prices on each platform. On iOS that needs a sandbox account; on Android, an internal-track install from Play or a licence tester.
- A real or sandbox purchase unlocks the paid action; restore works on a reinstall; cancelling leads to the lapsed state.
- The webhook test returns 200, and a purchase event updates the user's row.

## Gotchas
- Play's subscription APIs need the app to have a billing-enabled AAB uploaded (the `com.android.vending.BILLING` permission comes with the RevenueCat SDK).
- "Billing service unavailable" on an emulator is the device, not the code.
- Keep the iOS and Android prices in step; `convertRegionPrices` keeps Play's local prices sensible.

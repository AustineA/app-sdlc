# Store listings and policy forms

## Contents
- App Store Connect listing
- App Store review readiness
- Google Play listing (API)
- Google Play app content forms
- Verification

## App Store Connect listing
- Use the `asc-locale` or `appstore-metadata` skill. Fill name, subtitle, description, keywords, promo text, and support, marketing and privacy URLs (localized site pages) for every locale. A new locale's first POST may return 409; the retry succeeds.
- Primary and secondary category, copyright (for example "© 2026"), age rating questionnaire (messaging = yes for user-to-user apps).
- App Privacy: data types collected (contact info: email and name; identifiers: user id; user content: notes; purchases; device id for push), linked to the user, no tracking.
- Review notes: how to test multi-user flows (the owner creates, the partner joins with a code), where account deletion is, and a demo account if sign-in gates everything.

## App Store review readiness
- Each subscription needs a review screenshot and a localized display name. The subscriptions get submitted together with the first version.
- Test the iPad compatibility window even for an iPhone-only app.
- Attach the build and submit only when the user asks.

### First submission with subscriptions
Submitting the version alone gets rejected under **2.1(b) App Completeness** ("the app includes references to subscriptions but the associated In-App Purchase products have not been submitted"), and Apple then wants a new binary too. The first subscriptions can only be submitted inside the same review submission as an app version, and only from the web UI:
- The API can't do it. `POST /v1/subscriptionSubmissions` returns `FIRST_SUBSCRIPTION_MUST_BE_SUBMITTED_ON_VERSION`, and `reviewSubmissionItems` has no `subscription` relationship. Use the browser (Argent on CDP 9222).
- The version page no longer has an "In-App Purchases and Subscriptions" section. Items are collected in the **Draft Submissions** panel (bottom right) instead:
  1. Version page → **Add for Review** → pick the existing draft.
  2. Subscriptions → the group → **Add for Review** into the same draft.
  3. Open **each** subscription and **Add for Review** into the same draft. With only the group added, the panel says "New subscription groups must be submitted with an auto-renewable subscription from within that group".
  4. When the panel lists version + group + subscriptions and shows no warning, **Submit for Review**.
- Verify through the API: the version and every subscription read `WAITING_FOR_REVIEW`.

### Recovering from that rejection
1. Bump the build number, build and upload (`testflight-upload`), wait for VALID, then attach it to the version (`PATCH /v1/appStoreVersions/<id>/relationships/build`).
2. The rejected submission (`UNRESOLVED_ISSUES`) holds the version and can't take subscriptions. "Update Review" only swaps the build. Resubmitting it as it is would be rejected again.
3. Open that submission and click **Cancel Submission** → Confirm. Wait until it reads `COMPLETE` and the version reads `DEVELOPER_REJECTED`.
4. Then follow the steps above, adding everything into one draft. A draft holding only the group says "add an app version for the selected platform" until the version is in it.

## Google Play listing (API)
- Generate per-locale `title` (30 characters), `short_description` (80) and `full_description` (4000) from the ASC listing. Replace Apple-specific paragraphs (billing, Apple ID) with Google Play equivalents, and write your own 80-character short descriptions.
- Upload through the Publishing API: one edit, `PATCH details` (default language, contact email and website), then `PUT listings/<locale>` for each, then commit. `fastlane supply` metadata upload fails with "Could not find release for version code" while production has no release.
- Play locale codes: `ar, de-DE, en-GB, en-US, es-419, es-ES, fr-FR, hi-IN, id, it-IT, ja-JP, ko-KR, nl-NL, pt-BR, ru-RU, tr-TR, zh-CN, zh-TW`.
- Store the text under `android/fastlane/metadata/android/<locale>/`. Force-add it to git if a root `.gitignore` ignores `fastlane/`.

## Google Play app content forms (browser)
These have no API. Drive them in the user's browser (see browser-automation.md), in this order:
1. **Privacy policy URL.**
2. **Ads:** no. **Advertising ID:** no. That needs no `AD_ID` permission in the merged manifest; check it.
3. **Government apps, financial features, health:** none.
4. **Content rating** (IARC): "All other app types", user-generated content shared between users, digital purchases. **Save first, then Next.** Next stays disabled until it's saved.
5. **App access:**
   - "All or some functionality is restricted", plus sign-in instructions.
   - Google reviewers need a working login; for paid apps, an account that already has Pro.
   - Only the user can create this account, so it goes on the user list.
6. **Target audience:** 18+ (or the real audience). It's blocked until App access is done.
7. **Data safety:**
   - Export the template as CSV (capture it by hooking `window.Blob`), fill it in, then re-import it by setting the file input with CDP `DOM.setFileInputFiles`.
   - Clear any answer the importer rejects (for example `PSL_HAS_OUTSIDE_APP_ACCOUNTS`), then save it as a draft.
   - Submit it once App access and Target audience are complete.
8. **Store settings:** category (for example Lifestyle), contact email, and the website.

## Verification
- ASC: an API read of each version localization shows its text.
- Play: an API read of the listings returns every locale. Play Console "App content" shows each declaration as completed. Record in the state file anything blocked on the user, and why.

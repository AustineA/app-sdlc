---
name: app-sdlc
description: End-to-end orchestrator that takes a mobile app (native iOS, native Android, Expo/React Native or Flutter) from "code exists" to "builds on TestFlight and the Play internal track", including porting it to the missing platform. It audits the project first, skips every phase that's already done, and only moves on after each phase passes a verification gate. Phases are platform port with feature-by-feature e2e QA; Sign in with Apple/Google with cross-platform account linking; subscriptions (App Store Connect, Google Play, RevenueCat); push (APNs, FCM); localization; store screenshots for every locale; landing site and legal pages on Cloudflare; App Store and Play listings and policy forms; then the release. Use this whenever the user wants to "ship", "launch", "get the app to the stores", "port to Android/iOS", "do everything needed to publish", "finish the release setup", or asks what's missing before a store launch, even if they name only one or two of these pieces.
---

# App SDLC orchestrator

This skill runs the whole path from an app in a repo to builds that testers can install from TestFlight and the Play internal track. It's the workflow that shipped Couples Retro: a SwiftUI iOS app was ported to Kotlin/Compose with each feature QA'd before the next. That covered RevenueCat on both stores, Google and Apple sign-in, APNs and FCM push, FrameCraft screenshots in 18 locales, a localized landing site on Cloudflare and every store form.

You are the orchestrator. Most phases have a specialist skill; your job is to sequence them, detect what already exists, hold each phase to its verification gate, and keep a written record so a later session can resume.

**Specialist skills come from `setup.sh`, and they're optional.** This skill names helpers by role, among them `testflight-upload`, `play-store-publisher`, `framecraft-layer-design`, `aso-appstore-screenshots`, `asc-locale` / `appstore-metadata`, `app-landing-seo`, and an emulator or simulator driver such as Argent or XcodeBuildMCP. Use whichever of them is installed. When one is missing, do the step directly by following the phase's reference file and the scripts in `scripts/`. Every phase can be done without them.

## Operating principles

0. **Run end to end without asking.** Once the plan is shown, carry out every phase yourself. Don't stop to offer option lists, ask "should I proceed?", or write blocker reports for things you can do in the browser. When a key gets a 403, try the other keys. When a console step has no API, do it in the user's browser. Stop only for the items in "Things only the user can do". If the browser needs a re-login, send the user the URL and keep going with other work.
1. **Audit before acting.** Run `scripts/audit.py <project>` first. Phases it reports `done` are skipped (spot-check one piece of evidence; don't redo them). `partial` means finish only the missing pieces. This is what makes the skill safe to call on a half-shipped app: "app exists, no screenshots" should go straight to screenshots and whatever else is missing.
2. **Gate every phase.** A phase is finished only when its "Verify" evidence exists: a real sign-in, a push that arrived, an API read showing the build on the track. Logs that say "uploaded" don't count. Record the evidence in the state file. If a gate fails, fix it before starting the next phase. Later phases build on earlier ones (screenshots need a working app, store forms need the legal URLs).
3. **Prefer APIs and CLIs over clicking**, and the browser over asking the user. Use the order App Store Connect API → Google Play Developer API → RevenueCat API (or its internal API from a logged-in page) → driving the user's browser with **Argent on CDP port 9222**. Bash Playwright and raw-CDP scripts get blocked; see `references/browser-automation.md`. Hand a step to the user only when a console truly has no other way (see "Things only the user can do").
4. **Look for existing credentials before asking.** Check `~/.config/google-play/`, `~/.config/<app>/`, macOS Keychain, `~/.gradle/gradle.properties`, gitignored `*.local.*`/`local.properties`/`.asc-config.json`/`.play-config.json`, the project's memory, and past sessions (`~/.claude/projects/*/`, `~/.codex/sessions/`) for commands that worked. Reuse an app-scoped key from a sibling app on the same developer account before creating a new one.
5. **Secrets stay out of output and git.** Read them into shell variables inline (`PW=$(security find-generic-password -s '<App> Android Upload' -a upload_password -w)`), never echo them, and keep key files outside the repo, git-ignored.
6. **Store mutations default to the safest state.** iOS goes to TestFlight only. Never submit for review or attach a build to a version unless asked. Android goes to the internal track as a `draft`. Never touch production or rollouts unless the user explicitly asks. Respect any project memory that says "don't upload unless asked" or "I deploy the backend myself". When a backend change is needed, finish and test it locally, then tell the user it's ready to deploy, if that's their rule.
7. **Generic, not Couples-shaped.** Derive names, slugs, bundle ids, price points, locales and copy from the project. The references show what worked; adapt them to the project.

## State file

Keep `.release/sdlc-state.json` in the project root and add it to `.gitignore`. Update it after every gate:

```json
{
  "app": {"name": "", "slug": "", "ios_bundle_id": "", "android_package": "", "platforms": ["ios", "android"]},
  "phases": {
    "port": {"status": "done|partial|missing|skipped|blocked", "evidence": ["..."], "notes": ""}
  },
  "user_actions": ["things only the user can do, with exact console paths"]
}
```

On resume, read the state file and re-run the audit. The file can be stale; the audit can't.

## Phase 0 — Audit and plan

0. **Tooling.** Run `bash ~/.agents/skills/app-sdlc/scripts/setup.sh`, or use the path to this skill's `scripts/`. It reports which tools and companion skills are present: Argent, framecraft, XcodeBuildMCP, app-landing-seo, asc-locale, testflight-upload, play-store-publisher, fastlane and the rest. Once the plan below is known, install what's missing for the phases you'll actually run with `setup.sh --install <groups>`. See `references/tooling.md` for what each tool is for. If an MCP server such as Argent was just installed, tell the user to restart the agent before the QA phases.
1. `python3 ~/.claude/skills/app-sdlc/scripts/audit.py <project-root> [--landing <dir>] [--json]`. It detects the stack, ids, versions, and evidence per phase without reading secret contents. It also reports two things that come before any phase:
   - **Hygiene problems:**
     - secrets tracked in git (rotate them, then untrack them);
     - key files sitting in the repo;
     - release builds signed with the debug key;
     - EAS-managed credentials;
     - sensitive Android permissions with no real use.
   - **Data processors found in the code.** The legal pages and privacy labels must name them.
2. Fill in what static analysis can't see with read-only API calls when credentials exist:
   - Does the App Store Connect app exist? What's the live version, and which builds are VALID?
   - Does the Play app exist, and which version codes are on which tracks? An edits.insert → tracks.get → edits.delete with no commit counts as a read, and is fine even in a dry run. Use `scripts/play_api.py tracks`.
   - Does a RevenueCat project exist?
   - Is the landing site live, and do `/privacy`, `/terms`, `/support` and `/delete-account` return 200?
   - Does the version in the repo trail the store's? If so, bump it from the store's numbers, not the repo's.
3. Check the backend as well as the app, since store compliance lives there too:
   - The account-deletion endpoint deletes the right model.
   - The webhook handles both stores' product ids.
   - Sign-in verifiers check the token audience.
   - Note processors called only from the server (AI APIs, email). The legal pages must name those too.
4. Show the user a short plan as a table (phase → done / to do / blocked, plus why). List the hygiene problems first, then start. Ask only about decisions that are truly theirs: the store app name if none exists, prices if none are set, and any platform they don't want. Everything else has a default in the references.

## Phases

Run them in this order. Each section lists what it **detects** (to skip it), what it **does**, and what it must **verify** before moving on. Read the linked reference when you start the phase, not before.

### 1. Identity and store records → `references/identity-and-signing.md`
- **Detect:** bundle id and package set; App ID registered; App Group or capabilities registered; upload keystore present; App Store Connect app record and Play app record exist.
- **Do:**
  - Register the App ID and its capabilities through the ASC API.
  - Create the ASC app record.
  - Create the Android upload keystore, with its password in the Keychain.
  - Create the Play app in the user's browser, grant the existing publisher service account access to it (Users and permissions → Add app), then upload the first AAB with `fastlane supply` as an internal draft. Play App Signing gets enrolled on that upload.
- **Verify:**
  - An ASC API read returns the app.
  - A package-scoped Play API read succeeds (an edit insert followed by a track read).
  - `keytool -printcert -jarfile` on a signed AAB shows the upload certificate.
  - Record the upload SHA-1 and Play's app-signing SHA-1. Both are needed later, for Google sign-in.

### 2. Platform port (only when a platform is missing) → `references/porting.md`
- **Detect:** only one of iOS or Android exists, or the user asked for a port.
- **Do:**
  - Write a parity matrix from the source app (`.release/parity.md`): every screen, flow, notification, widget, deep link, setting and string.
  - Port one feature at a time, in dependency order: model and storage → sync and API → core screens → secondary screens → notifications → widget → store polish.
  - After each feature, build it, run it on an emulator or simulator, and exercise it end to end before starting the next.
  - Generate strings from the source app's catalog rather than hand-translating.
- **Verify:**
  - Every matrix row is ticked, with how it was tested.
  - Two-device tests pass: two emulators as a couple or pair for multi-user apps, plus one cross-platform pair (Android + iOS on the same backend). Use a local backend for these tests when one exists.

### 3. Authentication → `references/auth.md`
- **Detect:** Sign in with Apple and Google sign-in code; OAuth clients; backend verifiers; account linking.
- **Do:**
  - Sign in with Apple must request the `email` scope, or there's nothing to link on.
  - For Google sign-in, set up the OAuth consent screen and publish it to production. Branding needs the URLs and authorized domains first. Create a web client (its id is the server's audience) and Android clients for the **Play app-signing** SHA-1, plus the upload and debug SHA-1s if local builds must sign in. Check that any client id already in the code belongs to this package.
  - Expo apps on `expo-auth-session` Google need migrating to `@react-native-google-signin/google-signin`, because new Android clients reject custom-scheme redirects. See `references/auth.md`.
  - Add backend token verification.
  - Link accounts by provider-verified email, so the same person gets the same data on both platforms.
  - A returning account skips onboarding and the paywall.
- **Verify:**
  - A real sign-in on a device against the production backend, on each platform.
  - The same email gives the same account on iOS and Android.
  - Sign-out followed by sign-in restores the data.

### 4. Monetization → `references/monetization.md`
- **Detect:** subscription products in ASC and Play; a RevenueCat project, apps, entitlement and offering; the SDK wired in; a webhook; a server-side Pro check.
- **Do:**
  - Create the subscription group and products in ASC through the API.
  - Create the Play subscriptions with base plans and the trial offer through the API (`convertRegionPrices`).
  - In RevenueCat: create the project, an app per store, import the products, attach them to the entitlement, add packages to the default offering, and set up the webhook to the backend.
  - Add a server Pro check that asks RevenueCat when the webhook hasn't arrived yet.
  - No paywall in Android onboarding (Play policy). Gate the paid action instead.
- **Verify:**
  - Offerings load in a sandbox build on each platform.
  - A real or sandbox purchase works, and so does restore.
  - A webhook test returns 200.
  - A lapsed state is handled softly: content stays readable and the paid action prompts.

### 5. Push notifications → `references/push.md`
- **Detect:** `aps-environment` entitlement; APNs key on the server; Firebase app with `google-services.json`; FCM service account on the server; device registration that records the platform.
- **Do:**
  - Get an APNs key (team-scoped, so one key is reusable across apps) and enable the push capability, then regenerate the profiles.
  - Set up the Firebase project and Android app, and get the FCM v1 service account.
  - Add a backend dispatcher that sends to iOS through APNs and to Android through FCM, pruning dead tokens.
  - Create notification channels on Android.
  - Local reminders get scheduled on the device.
- **Verify:** a real push from the backend arrives on an iOS device or simulator and on an Android emulator. Check both foreground and background.

### 6. Localization → `references/localization.md`
- **Detect:** how many locales the app's string catalog or resources have, versus the target set.
- **Do:**
  - Use one source catalog. On Android, generate the string resources from it, plus a small file of Android-only translations.
  - Localize dates and plurals. Choose regional casts for photos if the brand calls for it.
- **Verify:**
  - Spot-check two locales on a device, one RTL and one CJK, using the per-app language setting.
  - The generator reports no missing keys.

### 7. Store screenshots → `references/screenshots.md`
- **Detect:** FrameCraft project and exports per locale; screenshots already in ASC and Play (read through the APIs).
- **Do:**
  - Capture from demo data.
  - Build the layered set with the `framecraft-layer-design` skill (`aso-appstore-screenshots` for headlines).
  - Export every store locale.
  - For Play, reuse the iOS set cropped to at most 2:1 (Play rejects a long side more than twice the short side).
- **Verify:** API reads show 6–10 screenshots per locale on both stores, and the images are the new ones.

### 8. Landing site and legal pages → `references/landing-and-legal.md`
- **Detect:** landing repo or Worker; live URL; privacy, terms, support and delete-account pages; whether those pages name every platform and data processor; locale coverage.
- **Do:**
  - Build or extend the site with the `app-landing-seo` skill.
  - Legal pages must cover each platform's sign-in, billing, push provider and cancellation path, account deletion, and every processor. That means every processor the audit found in the app, plus the ones the backend calls. A privacy page that says "we collect no data" while the app ships analytics gets the app rejected.
  - Translate the legal pages into every locale.
  - Deploy with `npx wrangler deploy` (Cloudflare).
- **Verify:**
  - `curl` the live privacy, terms and delete-account pages, plus one translated locale, and check for the new wording.
  - The build's SEO checks pass.

### 9. Store listings and policy forms → `references/store-forms.md`
- **Detect:** ASC version localizations, age rating, App Privacy, review notes; Play listing locales, category, contact details, the app content declarations (privacy URL, ads, ad ID, data safety, content rating, target audience, app access/sign-in details, government/financial/health).
- **Do:**
  - **ASC:** write the listing text per locale with the `asc-locale` or `appstore-metadata` skill, and fill in age rating, review notes, URLs and copyright.
  - **Play:** upload the listing through the Publishing API rather than `fastlane supply` metadata, which fails while production has no release.
  - **Play forms:** fill the app content forms in the browser. Data safety can be done by CSV import.
- **Verify:**
  - API reads show every locale's text.
  - Play Console's "App content" page shows each declaration as complete. Some depend on others (target audience needs sign-in details first), so record what's blocked on the user.
  - In the final report, warn that the first App Store submission must include the subscriptions in the same submission as the version. The API can't do this; use the Draft Submissions panel. Otherwise review rejects the app under 2.1(b). When the user asks you to submit, or to fix that rejection, follow "First submission with subscriptions" in `store-forms.md`.

### 10. Release builds
- **iOS:** use the `testflight-upload` skill. Bump the build number, archive, export and upload, then poll until the build is VALID.
- **Android:** check `df -h /` first (about 7 GB needed), bump `versionCode` above Play's latest, build a signed AAB (the IPv4 Gradle flag is in `identity-and-signing.md`), check the signer, then upload with the `play-store-publisher` skill (or `fastlane supply --track internal --release_status draft --skip_upload_metadata ...`). Then read the track through the API. Fastlane's update banner can hide its own result.
- **Expo:** `eas build --platform all --profile production`, then `eas submit` (or download the artifacts and use the paths above). Its credentials may live in EAS (`eas credentials`) rather than on the machine, which is not an error.
- **Verify:** the build is VALID in TestFlight, and the version code is on the internal track as a draft.

## Things only the user can do

Collect these in `user_actions` and in the final report. Give the exact console path for each.

- Accepting agreements: Paid Apps in App Store Connect, payments profile in Play Console.
- Reviewer sign-in credentials, using a real account that has Pro.
- Rolling out a draft, and submitting for review.
- Deploying the backend, if their rule says so.
- Anything that requires 2FA or a password in the browser. Send them the exact URL.

Creating the Play app, granting the service account access, creating OAuth clients and publishing the consent screen are **not** on this list. Do them in the browser.

## Final report

Write it for the user, briefly:

1. A table of phases with skipped / done / blocked.
2. What's live: the build numbers and tracks, the URLs, and where to try it.
3. What was verified and how.
4. The user's remaining actions, with console paths.
5. Anything risky or not verified.

Update the project's memory with the setup that worked (ids, key names, commands), never the secrets.

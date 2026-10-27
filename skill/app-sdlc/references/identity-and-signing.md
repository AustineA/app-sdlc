# Identity, signing and store records

## Contents
- Ids and naming
- iOS: App ID, capabilities, App Store Connect record
- Android: package, upload keystore, Play app, API access
- Gotchas

## Ids and naming
- Use the same identifier on both platforms when possible: iOS bundle id = Android `applicationId` (for example `app.<studio>.<slug>`). It keeps RevenueCat, deep links and server config simple.
- Keep internal codenames out of anything user-facing (store name, notification channel names, legal pages). Ask the user for the public name if the code only has a codename.
- Pick a stable kebab-case `slug`. Key files follow it: `~/.config/google-play/<slug>-upload.jks`, `<slug>-publisher.json`, Keychain service `"<App Name> Android Upload"`.

## iOS
- Use the App Store Connect API with the account's existing key: a gitignored `.asc-config.json` holding `keyId`, `issuerId`, `keyPath` and `teamId`. Look for a sibling project's config before asking for one.
- Register the bundle id (`POST /v1/bundleIds`) and enable its capabilities (`POST /v1/bundleIdCapabilities`): PUSH_NOTIFICATIONS, APP_GROUPS (widgets), SIGN_IN_WITH_APPLE, ASSOCIATED_DOMAINS when needed. Regenerate the App Store profiles after any capability change. **An ASC API key cannot create App Groups.** That needs the developer portal or a signed-in Xcode, so put it on the user list if it's missing.
- Create the app record with `POST /v1/apps` (name, primary locale, SKU, bundle id). It fails if the name is taken, so offer alternatives.
- XcodeGen projects: set `TARGETED_DEVICE_FAMILY: "1"` at **target** level for iPhone-only apps (and their extensions). Otherwise Apple demands iPad orientations at upload.
- Treat an iPhone-only app as reviewed on iPad anyway: run it once in the iPad compatibility window (an iPad Air sim) and fix overlaps and truncation before the first submission.

## Android
- `applicationId`, `minSdk 26`, target and compile SDK at the current level. Release builds minified, and `localeFilters` set to the shipped locales.
- Upload keystore: `keytool -genkeypair -v -keystore ~/.config/google-play/<slug>-upload.jks -alias <slug>-upload -keyalg RSA -keysize 4096 -validity 10000`. Store the password with `security add-generic-password -s '<App Name> Android Upload' -a upload_password -w '<pw>'`, generating it into a variable rather than printing it.
- Build signed without saving secrets in Gradle:
  ```
  PW=$(security find-generic-password -s '<App Name> Android Upload' -a upload_password -w)
  ./gradlew :app:bundleRelease \
    -Pandroid.injected.signing.store.file=$HOME/.config/google-play/<slug>-upload.jks \
    -Pandroid.injected.signing.store.password="$PW" \
    -Pandroid.injected.signing.key.alias=<slug>-upload \
    -Pandroid.injected.signing.key.password="$PW"
  keytool -printcert -jarfile app/build/outputs/bundle/release/app-release.aab | grep SHA1
  ```
- Play app: the API can't create it, so create it yourself in the user's browser (see `browser-automation.md` → "Play create app"). If every publisher key returns **"Package not found"**, the app doesn't exist yet. That isn't a permissions problem.
- API access: then grant an existing publisher service account access to the new app yourself, through Users and permissions → Add app (see `browser-automation.md`). Reuse the account's existing publisher key. When one key returns 403, try the account's other keys. Once the grant is in, **the first AAB can go up through `fastlane supply` to the internal track as a draft**, so no manual upload is needed. Play App Signing is enrolled by default on that first upload; check it on the App signing page.
- Record both SHA-1s, the **upload** certificate (from `keytool`) and Play's **app signing** certificate (Test and release → App integrity → App signing, read with the copy button and `pbpaste`). Google sign-in needs an Android OAuth client for the Play app-signing key at least. Add the upload key and the debug keystore when local builds must sign in too.

## Build machine
- **Check `df -h /` before building.** An Expo/RN release build needs about 7 GB free (Gradle caches, CMake, the AAB). If space is short, clear regenerable caches first (Xcode DerivedData, `~/.gradle/caches`, npm and pnpm caches) with the `reclaim-disk-space` skill. Don't run `uv cache clean`, which can hang.
- If Gradle fails with **"Can't assign requested address"**, add `-Dorg.gradle.jvmargs="-Xmx4g -Djava.net.preferIPv4Stack=true"`.
- Expo CNG: run `npx expo prebuild --clean -p android --no-install`, then `NODE_ENV=production ./gradlew :app:bundleRelease` from `android/` with the injected signing flags above. The AAB is at `android/app/build/outputs/bundle/release/app-release.aab`. Copy it to `.release/<slug>-<versionCode>.aab`. Set `expo.android.versionCode` in `app.json`; with no value, every build is versionCode 1.

## Gotchas
- A Play `versionCode` can never be reused, even from a deleted draft. Always read the track's latest first, then bump above it.
- Fastlane's "update available" banner can hide the upload result. Confirm with an API track read (edits.insert → tracks.get → edits.delete).
- Keep `local.properties`, `google-services.json` (if the project treats it as private), `.asc-config.json`, `.play-config.json` and every `*.jks` / `*.p8` / service-account JSON out of git.

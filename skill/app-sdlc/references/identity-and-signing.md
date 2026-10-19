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
- Play app: create it in Play Console (the API can't). Enrol Play App Signing. Upload the first AAB (the internal track is fine). After that everything goes through the API.
- Record both SHA-1s, the **upload** certificate and Play's **app signing** certificate (Play Console → Test and release → App integrity). Google sign-in needs an Android OAuth client for each, plus one for the debug keystore.
- API access: a service-account JSON with Play permissions for this app. Reuse one from a sibling app on the same developer account if a package-scoped read proves it has access. When one key returns 403, try the account's other publisher keys before asking the user to grant access (Users and permissions → the service account → App permissions: view app information, release to testing tracks, manage store presence).

## Gotchas
- A Play `versionCode` can never be reused, even from a deleted draft. Always read the track's latest first, then bump above it.
- Fastlane's "update available" banner can hide the upload result. Confirm with an API track read (edits.insert → tracks.get → edits.delete).
- Keep `local.properties`, `google-services.json` (if the project treats it as private), `.asc-config.json`, `.play-config.json` and every `*.jks` / `*.p8` / service-account JSON out of git.

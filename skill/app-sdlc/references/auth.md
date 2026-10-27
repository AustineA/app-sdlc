# Authentication: Sign in with Apple, Google, cross-platform accounts

## Contents
- Target behaviour
- Sign in with Apple
- Google sign-in (Android)
- Backend
- Verification
- Gotchas

## Target behaviour
- iOS signs in with Apple; Android signs in with Google, unless the user wants both on both.
- **The same person gets the same account and data on every platform.** Link identities by the provider-verified email.
- A returning account with data skips onboarding and the paywall, whatever its subscription status.
- Signing out keeps the data. Deleting the account removes it, as the legal pages describe.

## Sign in with Apple
- Request `[.fullName, .email]`. Without `.email`, Apple's ID token carries no email and there is nothing to link on. Accounts created before the scope was added have no stored email until they sign in on a build that requests it, or until it's backfilled by hand.
- The capability must be on the App ID, and the profiles regenerated afterwards.

## Google sign-in (Android)
Use Credential Manager with the `googleid` library (`GetSignInWithGoogleOption` or `GetGoogleIdOption` with `serverClientId` = **web** client id). Send the ID token to the backend.

Set up OAuth in the Google Cloud project. Reuse the Firebase project's GCP project, so push and auth share it:
1. OAuth consent screen: External, app name, support email, privacy and terms URLs from the landing site. **Publish it to Production**, because in Testing only listed test users can sign in.
2. A **Web application** client. Its id is the backend's expected audience and the app's `serverClientId`.
3. **Android** clients for each signing certificate: the debug keystore, the upload key, and Play's app-signing key. Each one is the package name plus that SHA-1. A release installed from Play is signed with Play's key, so leaving that client out breaks sign-in only in production.

Keep the web client id in gitignored config (for example `local.properties` → `BuildConfig`).

**Check that client ids already in the code belong to this app.** Open each id in the Clients list and compare its package name and SHA-1. A client copied from a sibling app (same GCP project, different package) fails silently on device. Create the right client instead of trusting the code.

The consent screen can only be published once Branding has a home page URL, privacy and terms URLs, and every domain those URLs use under Authorized domains (Notion legal pages need their `*.notion.site` subdomain too). Fill these first; otherwise "Publish app" stays greyed out.

### Expo / React Native
- **`expo-auth-session`'s Google provider on Android relies on a custom-scheme redirect.** New Android OAuth clients have no "custom URI scheme" toggle under Advanced settings, and Google blocks those redirects, so the browser flow fails on a fresh client. Use `@react-native-google-signin/google-signin`, which goes through Credential Manager, with `webClientId` set to the **web** client id. Send the ID token to the backend. An existing app on `expo-auth-session` needs this migration before Google sign-in on Android counts as verified. Flag it in the report, and don't claim the auth gate passed.

## Backend
- Verify Google ID tokens against Google's certs with `aud` = web client id (in Rails: `Google::Auth::IDTokens.verify_oidc`). Verify Apple tokens against Apple's JWKS with `aud` = bundle id.
- Store provider subject ids in separate columns (`apple_user_id`, `google_user_id`, both nullable and unique) plus an index on `lower(email)`.
- One identity sign-in service, `IdentitySignIn.call(provider:, subject:, email:, email_verified:, first_name:)`:
  1. If an account already has this provider subject, and it has data or no other account matches the email, use it.
  2. Otherwise, find an account with the same **verified** email and link this identity to it. Prefer the account that has data. Retire an empty, non-paying account this identity made earlier.
  3. Otherwise, create an account.
  4. Fill in a missing email or first name.
- Cover these cases with integration tests: new user, returning user, link by email, an unverified email must not link, and an empty duplicate retired.

## Verification
- Sign in on a real device against production, on each platform.
- Sign in with the same email on iOS and on Android, and check that the same data appears on both.
- Sign out, sign in again, and check that you go straight to your data with no paywall.

## Gotchas
- **"Couldn't sign in" on device while it works locally** usually means the backend endpoint isn't deployed (production returned 404).
- **Two accounts already holding data** for the same person (made before linking existed) need a one-off merge script. Run it as a dry run first, then apply it. Run production Rails commands from a script file copied into the container (`docker cp` + `dokku enter <app> web bin/rails runner /tmp/x.rb`), because `dokku run` re-evaluates the command string and parentheses break it.
- Users who hid their Apple email get a relay address. It links to a Google account only if the user signs in with the same address, which is expected; explain it if asked.

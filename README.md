# App SDLC

An AI coding-agent skill that takes a mobile app from "the code exists" to "testers can install it from TestFlight and the Google Play internal track". It works with native iOS, native Android, Expo/React Native, Flutter and Capacitor. It can also port an app to the platform it's missing.

It starts with an audit of the project and skips every phase that's already done. Each phase must pass a verification check (a real sign-in, a push that arrived, a build visible on the track) before the next one starts. That makes it safe to point at a half-shipped app: "the app is live but has no localized screenshots" goes straight to screenshots and whatever else is missing.

## Phases

1. Identity and signing: bundle id, App ID and capabilities, upload keystore, store app records, API access
2. Platform port: a parity matrix, then one feature at a time with end-to-end QA on emulators and simulators, including two-device and cross-platform tests
3. Authentication: Sign in with Apple and Google, plus account linking by email so one person has one account across platforms
4. Monetization: App Store and Play subscriptions, RevenueCat (products, entitlement, offering, webhook), and Play's rule against a paywall during onboarding
5. Push: APNs and FCM, with a backend dispatcher for each platform
6. Localization: one string catalog, with Android strings generated from it
7. Store screenshots for every locale (FrameCraft), reused for Play with a 2:1 crop
8. Landing site and legal pages that name every platform and data processor, deployed to Cloudflare
9. Store listings and policy forms: App Store Connect, the Play listing through the API, and the Play app-content declarations
10. Release: a TestFlight build, and a Play internal-track draft

The audit also flags hygiene problems before any phase starts: secrets committed to git, debug-signed release builds, unused sensitive permissions, and SDKs the privacy policy doesn't mention.

## Installation

```bash
npx github:AustineA/app-sdlc
```

This copies the skill to `~/.agents/skills/app-sdlc/` and symlinks it into any Claude Code, Codex, Cursor, Windsurf, Antigravity, Trae or Amp installation it finds.

```bash
npx github:AustineA/app-sdlc status
npx github:AustineA/app-sdlc uninstall
```

## Usage

Ask your agent, for example:

```text
Ship ~/Code/my-app to the App Store and Google Play. Do whatever is still missing.
Port this iOS app to Android and get it on the Play internal track.
What's left before we can launch this app?
```

To see the phase table on its own (read-only):

```bash
python3 ~/.agents/skills/app-sdlc/scripts/audit.py <project-root> [--landing <site-dir>] [--json]
```

## Requirements

- Node.js 18+ (installer) and Python 3 (scripts). The Play helpers need `pip install google-auth requests pillow`.
- Your own accounts and keys: an App Store Connect API key, a Google Play service account, RevenueCat, Firebase/GCP and Cloudflare. The skill reuses keys it finds locally, never prints secrets, and lists anything only you can do (agreements, reviewer accounts, rollouts).
- Optional specialist skills it hands work to when they're installed: `testflight-upload`, `play-store-publisher`, `framecraft-layer-design`, `asc-locale`, `app-landing-seo`, and an emulator/simulator driver such as Argent or XcodeBuildMCP.

Store changes default to the safest state: iOS goes to TestFlight only, and Android to an internal draft. Nothing is submitted for review or sent to production unless you ask.

## License

MIT

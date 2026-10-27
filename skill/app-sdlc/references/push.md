# Push notifications: APNs + FCM

## Contents
- Design
- iOS (APNs)
- Android (Firebase Cloud Messaging)
- Backend
- Verification
- Gotchas

## First: does the app need remote push?
Grep for push-token registration (`getDevicePushTokenAsync`, `getExpoPushTokenAsync`, `FirebaseMessaging`, `onNewToken`) and for server-side sending. If the app only schedules local notifications, mark the phase skipped: FCM and `google-services.json` are not needed.

## Design
- Anything that can be scheduled on the device should be a **local** notification: daily reminders, "opens tomorrow", "it's time". Both partners' phones fire at the same moment without a server.
- Server pushes are only for things other people do ("Jonah added a note"). Never put private content in the push text, and rate-limit per recipient (for example 1 per hour).
- Register devices on the server with `{token, platform: ios|android, environment}` and dispatch by platform.

## iOS (APNs)
- Add the `aps-environment` entitlement (an AppDelegate for registration). Enable PUSH_NOTIFICATIONS on the App ID and **regenerate the App Store profile**; the old one lacks the entitlement.
- Use a token-based **APNs key** (`.p8`, team-scoped, sandbox + production). One key serves every app on the team, so look for an existing one before making another. Store `key_id`, `team_id` and the p8 contents in server credentials.
- Debug builds register as sandbox, Release builds as production. Send `environment` with the token so the server picks the right APNs host.
- A `.p8` in Dropbox may be an online-only placeholder. Open it once to download it before reading.

## Android (FCM)
- Firebase project: reuse the app's GCP project. Add the Android app with the package name and the SHA-1s, then get `google-services.json`.
  - If the browser can't download the file (download manager extensions intercept it), assemble it from the console values: project number, project id, mobilesdk app id, API key, package. Apply the google-services Gradle plugin only when the file exists, so the build works without it.
- FCM HTTP v1 needs a **service account** JSON (Project settings → Service accounts → Generate key). Keep it outside the repo, for example `~/.config/<slug>/fcm-service-account.json`, and in server credentials.
- App:
  - `FirebaseMessagingService.onNewToken` → register with the backend.
  - `onMessageReceived` shows the notification only when the app is in the foreground; otherwise the system shows notification messages itself. Use `NotificationChannel`s with translated names.
  - Request POST_NOTIFICATIONS on API 33+, after the user has done something that makes the permission make sense (for example finishing the schedule step).

## Backend
- An `FcmPush` service (for example the `fcm` gem `send_v1`) with `android.priority: high` and `notification.channel_id`. Delete tokens that return UNREGISTERED or 404.
- An `ApnsPush` service (for example `apnotic`) sending only to iOS devices.
- A dispatcher job calls both. Without credentials it skips with a log line, so dev and tests don't crash.

## Verification
- From the backend console, send to a real iOS device or the simulator (sandbox) and to an Android emulator, and see them arrive. Do it once with the app in the foreground and once in the background.
- Trigger a real event (the partner adds a note) and see the push on the other device.
- Delete the app and check the dead token gets pruned on the next send.

## Gotchas
- Pushes stop once the device token rotates, unless the app re-registers on launch.
- Notification-type FCM messages don't wake the app in the background, so a widget refreshes the next time the app opens.

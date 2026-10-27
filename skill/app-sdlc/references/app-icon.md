# App icon: launcher vs store listing

Google Play rejects an update under the **Misleading Claims policy → "App store listing mismatch: your app's installed icon or name differs from its store listing"** when the icon a reviewer sees on the phone doesn't look like the 512×512 hi-res icon on the listing. Bee Habit was rejected twice for this in one day (2026-10-26). Check it before every production submission.

## Contents
- Why it happens
- Building a matching pair
- Verify before submitting
- Reading a rejection

## Why it happens
1. **The launcher icon is still a template.** Expo projects ship placeholder adaptive-icon files, and they survive until someone replaces them on purpose. Setting `expo.icon` (or the iOS `.icon` file) does **not** change the Android launcher icon. Templates `scripts/audit.py` flags by hash:
   - SDK 54+: `assets/images/android-icon-foreground.png` (a blue "A"), plus its background and monochrome files.
   - Older SDKs: `assets/images/adaptive-icon.png` (a grey grid with concentric circles).
   - `android.adaptiveIcon.monochromeImage` is the themed icon (Android 13+). A leftover template there shows the "A" to anyone with themed icons on, so replace it or delete the key.
   - Flutter's default `ic_launcher` and Android Studio's green robot aren't hashed. Look at the launcher yourself.
2. **The artwork is full-bleed.** An adaptive icon is a 108dp canvas: launchers show only the middle 72dp and then mask it to a circle, squircle or rounded square. Every launcher keeps the **66dp safe circle**. Artwork that runs to the edges (a mascot or tile cut off by the border, as iOS icons often are) gets cropped differently on each launcher. On a Pixel, the circle cut away the bee and the check tile, so the installed icon no longer looked like the square store icon, even though both came from the same PNG. The second rejection's only evidence was "App icon (en-US)", the store icon.

## Building a matching pair
- **One composition, two outputs.** Generate the launcher foreground and background **and** the Play hi-res icon from the same layers with one script, so they can't drift. Bee Habit's version is `scripts/android-icon.py` in that repo:
  - **Background:** the pattern or colour layer, filling the whole 108dp canvas, with no white frame.
  - **Foreground:** the important artwork, kept inside the 66dp safe circle (about 61% of the 108dp canvas width), on a transparent canvas.
  - **Play icon:** the 72dp viewport of background + foreground, at 512×512. Play applies its own rounded mask, so don't round the corners yourself.
- **Start from layers, not a flattened icon.** iOS Icon Composer files keep them in `<name>.icon/Assets` (for example `bg.jpg`, a character, a glyph). A flattened 1024 PNG with artwork cut off at its edges can't be fixed by scaling it: it gets a white frame or a sliced-off subject.
- Any feature graphic or promo image that shows the icon gets regenerated from the new Play icon.
- The iOS icon can stay as it is. Apple doesn't compare like this, but keep the same characters and colours so the two stores still look like one app.
- **Name:** the launcher label (`expo.name` / `android:label`) should be the listing title or a clear prefix of it ("Bee Habit" for "Bee Habit Tracker: Year Pixels"). If a rejection persists after the icon matches, look at the name next.

## Verify before submitting
Do this gate for any build bound for production, and on the **internal track first**:
1. `python3 scripts/icon_check.py --aab <app-release.aab> --store-icon <512px icon> --out icon-check.png` pulls the launcher layers out of the bundle and renders them under circle, squircle and rounded-square masks, with the safe circle drawn on, next to the store icon. Everything that matters has to sit inside the red circle, and all panels should read as the same icon.
2. Install the exact AAB on an emulator: `bundletool build-apks --connected-device` with the upload key, then `install-apks`. Open the app drawer and compare the real launcher icon with the listing icon. Download the live listing icon through the Publishing API (`edits.listings.images.list` for `icon`); don't trust the local file.
3. If the listing icon changed, upload it in the same Play submission as the build. A listing change without the build, or the build without the listing change, gets judged against the old half.

## Reading a rejection
- **Play Console → Policy status → View details** names the location and attaches the evidence image. **Publishing overview → Submission activity → the submission** shows which release, and so which build, was reviewed. Check both before changing anything. A rejected change returns to "Changes not yet submitted for review", so it can look as if it was never sent.
- Fix the build and the listing, roll the build out on internal testing, verify it on a device, then replace the production release and send it for review. An appeal won't help when the mismatch is real.

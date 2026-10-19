# Store screenshots (every locale)

## Contents
- Captures
- Building the set (FrameCraft)
- App Store upload
- Google Play upload
- Verification

## Captures
- Capture from **demo data**: launch arguments or intent extras that load a full board with no backend (`-demoBoard`, `-demoOpen`, `-demoTheme`, `-demoScreen viewer|compose|past` on iOS; `--ez demoBoard true` and similar on Android, debug builds only).
- Show a 9:41 status bar on iOS. A `simctl` capture lacks the Dynamic Island, so stamp it on.
- Capture every locale with the per-locale keyboard set (`simctl spawn <udid> defaults write -g AppleKeyboards`) and the regional cast if the app has one.

## Building the set (FrameCraft)
- Use the `framecraft-layer-design` skill for layered shots (device frame, pulled-out cards, headline), and `aso-appstore-screenshots` to find 6–8 benefit-led headlines.
- Lay it out per locale as `design/appstore/framecraft/l10n/<lang>/caps` → an export script → `export/<asc-locale>/NN-iphone-6-9-inch.png` (1320×2868).
- Scripts need their own fonts: the display serif has no Cyrillic or CJK, so pick per script (Georgia for ru, Hiragino Mincho for ja, Songti for zh, Apple SD Gothic Neo for ko, Geeza Pro for ar, Kohinoor for hi). Mirror crops for ar. With Pillow, Arabic and Devanagari shaping needs libraqm (`DYLD_LIBRARY_PATH=/opt/homebrew/lib`).

## App Store upload
- Use the `appstore-screenshots` or `asc-locale` skill: APP_IPHONE_67 screenshot sets per version localization (delete the old set first, then upload, then commit through the reservation flow).
- Optional iOS 27 product page header and search-result assets: `POST /v1/appAssetLibraryImages` (category CREATIVE_ASSETS), then placements on the version localization.

## Google Play upload
- **Reuse the iOS set.** Play rejects images whose long side is more than 2× the short side, and 1320×2868 is 2.17. Crop to 1320×2640 from the top when the phone runs off the bottom of the frame (check one first). Otherwise pad.
- Play → FrameCraft locale map: `ar`→ar-SA, `es-419`→es-MX, `id`→id-ID, `zh-CN`→zh-Hans, `zh-TW`→zh-Hant; the rest are the same.
- Upload through the Publishing API in **one edit**: for each locale, `DELETE …/listings/<loc>/phoneScreenshots`, then POST each PNG to the upload endpoint (`/upload/androidpublisher/v3/…/phoneScreenshots?uploadType=media`), then `:commit`. That's over 120 uploads, and the run hit intermittent 401s and broken pipes. **Fetch a fresh access token for each image and retry with backoff.** A failed run never commits, so retrying is safe. `scripts/play_screenshots.py` does all of this.
- Also needed: a feature graphic (1024×500) and a 512×512 icon (en-US at least).

## Verification
- API reads list 6–10 images per locale on both stores.
- Look at one locale per script family (Latin, RTL, CJK, Devanagari) in a contact sheet before uploading.

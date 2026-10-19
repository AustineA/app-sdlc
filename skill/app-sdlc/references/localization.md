# Localization

## Locale set
The proven store set is en-US, en-GB, de, fr, es (es-ES, es-419/es-MX), it, pt-BR, nl, tr, ru, ar, hi, id, ja, ko, zh-Hans, zh-Hant. Match the app's catalog to the store listings. Add a locale to the app before adding its store listing.

## App
- **iOS:**
  - One `Localizable.xcstrings`, shared with extensions.
  - Use `String(localized:)` for plain strings. Use inflection markup (`^[\(n) note](inflect: true)`) only where it works (de, fr, es, it, pt), and number-safe wording elsewhere.
  - Xcode doesn't write the catalog back on command-line builds. Run `xcrun xcstringstool sync <catalog> --stringsdata <DerivedData *.stringsdata>`.
- **Android:**
  - Generate `values-<q>` from the iOS catalog (see porting.md). Qualifiers: `id`→`in`, `pt-BR`→`pt-rBR`, `zh-Hans`→`zh-rCN`, `zh-Hant`→`zh-rTW`.
  - Android-only strings (notification channels, "Continue with Google", Play wording) go in a JSON file of translations keyed by iOS locale. Swap Apple ID → Google account, App Store → Google Play, iPhone → phone.
  - Don't half-translate phrases that sit beside fixed English text, such as "Made with ♥ by X".
- Store data stays language-neutral. Default column or category titles stay stored in English and are shown localized, because they sync to a partner who may use another language.
- Dates, times and lists come from the locale (12/24-hour, ICU list format). Use `ar_AE` on the iOS simulator; `ar_SA` defaults to the Hijri calendar.
- Optional: regional photo casts (East Asia, LatAm, India, Indonesia, Middle East) chosen from the device's language or region for onboarding photos, store hero images and the website.

## Verify
- Run the generator: no missing keys, no "no translation" warnings.
- On Android, set a per-app language without changing the device: `adb shell cmd locale set-app-locales <pkg> --user 0 --locales de-DE` (`""` resets it). On iOS, use `-AppleLanguages (de) -AppleLocale de_DE` launch arguments.
- Check one RTL locale (ar) and one CJK locale (ja or zh). Look at the settings page, a dialog, the notification channel names (`dumpsys notification`) and the widget.

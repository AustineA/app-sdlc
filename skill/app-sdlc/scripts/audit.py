#!/usr/bin/env python3
"""Audit a mobile app project for store readiness, phase by phase.

Usage: audit.py <project-root> [--landing <dir>] [--json]

Static, read-only and offline. It reports what exists per phase (done / partial / missing),
with the evidence it found, so the orchestrator can skip finished work. It never prints
secret values: for keys it only reports that a pattern or file is present.
"""
import json, os, re, sys, glob
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "build", ".gradle", "Pods", "DerivedData", ".build", "dist", ".ssr",
             ".next", ".expo", "vendor", "__pycache__", ".idea", "build-production", "export", "raw"}
CODE_EXT = {".swift", ".kt", ".kts", ".java", ".ts", ".tsx", ".js", ".jsx", ".dart", ".m", ".mm", ".gradle",
            ".plist", ".xml", ".json", ".yml", ".yaml", ".entitlements", ".xcconfig", ".properties", ".rb", ".toml"}
MAX_FILE = 1_500_000


def walk(root, max_depth=16):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d in (".github",)]
        if depth >= max_depth:
            dirnames[:] = []
        for f in filenames:
            yield Path(dirpath) / f


class Index:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.files = list(walk(self.root))
        self._text = {}

    def rel(self, p):
        return str(Path(p).resolve().relative_to(self.root)) if str(Path(p).resolve()).startswith(str(self.root)) else str(p)

    def text(self, p):
        if p not in self._text:
            try:
                self._text[p] = p.read_text(errors="ignore") if p.stat().st_size < MAX_FILE else ""
            except OSError:
                self._text[p] = ""
        return self._text[p]

    def named(self, *patterns):
        return [f for f in self.files if any(f.match(pat) for pat in patterns)]

    def grep(self, regex, exts=CODE_EXT, limit=5):
        rx = re.compile(regex)
        hits = []
        for f in self.files:
            if f.suffix in exts and rx.search(self.text(f)):
                hits.append(self.rel(f))
                if len(hits) >= limit:
                    break
        return hits

    def first_match(self, regex, files):
        rx = re.compile(regex)
        for f in files:
            m = rx.search(self.text(f))
            if m:
                return m.group(1)
        return None


def status(found, total):
    return "done" if found == total else ("missing" if found == 0 else "partial")


def phase(name, checks, notes=None):
    """checks: list of (label, evidence-or-None)."""
    have = [(l, e) for l, e in checks if e]
    return {"phase": name, "status": status(len(have), len(checks)),
            "have": {l: e for l, e in have}, "missing": [l for l, e in checks if not e], "notes": notes or []}


def audit(root, landing=None):
    ix = Index(root)
    home = Path.home()
    r = {"root": str(ix.root), "stack": {}, "app": {}, "phases": []}

    # ---- Stack ---------------------------------------------------------------------------
    pkg = ix.named("package.json")
    pkg_text = " ".join(ix.text(p) for p in pkg if "node_modules" not in str(p))
    is_expo = '"expo"' in pkg_text
    is_rn = '"react-native"' in pkg_text
    is_flutter = bool(ix.named("pubspec.yaml"))
    is_capacitor = '"@capacitor/core"' in pkg_text
    xcodeprojs = [d for d in ix.root.rglob("*.xcodeproj") if not any(s in d.parts for s in SKIP_DIRS)]
    xcodegen = ix.named("project.yml")
    gradle_settings = ix.named("settings.gradle", "settings.gradle.kts")
    app_gradle = [f for f in ix.named("build.gradle", "build.gradle.kts") if "com.android.application" in ix.text(f)
                  or "applicationId" in ix.text(f)]
    has_ios = bool(xcodeprojs or xcodegen or ix.named("Podfile")) or (is_expo and '"ios"' in ix.text(ix.root / "app.json") if (ix.root / "app.json").exists() else False)
    has_android = bool(app_gradle) or (is_expo and (ix.root / "app.json").exists() and '"android"' in ix.text(ix.root / "app.json"))
    kind = ("flutter" if is_flutter else "expo" if is_expo else "react-native" if is_rn
            else "capacitor" if is_capacitor else "native")
    r["stack"] = {"kind": kind, "ios": has_ios, "android": has_android,
                  "xcodegen": [ix.rel(p) for p in xcodegen], "xcodeproj": [ix.rel(p) for p in xcodeprojs][:3],
                  "android_app_gradle": [ix.rel(p) for p in app_gradle][:3]}

    # ---- App identity --------------------------------------------------------------------
    ios_files = xcodegen + [p / "project.pbxproj" for p in xcodeprojs] + ix.named("app.json", "app.config.*")
    bundle = ix.first_match(r'PRODUCT_BUNDLE_IDENTIFIER["\s:=]+"?([A-Za-z0-9.\-]+)"?', ios_files) \
        or ix.first_match(r'"bundleIdentifier"\s*:\s*"([^"]+)"', ios_files)
    package = ix.first_match(r'applicationId\s*=?\s*"([^"]+)"', app_gradle) \
        or ix.first_match(r'"package"\s*:\s*"([^"]+)"', ix.named("app.json"))
    ios_build = ix.first_match(r'CURRENT_PROJECT_VERSION["\s:=]+"?([0-9.]+)', ios_files)
    ios_version = ix.first_match(r'MARKETING_VERSION["\s:=]+"?([0-9.]+)', ios_files)
    vcode = ix.first_match(r'versionCode\s*=?\s*(\d+)', app_gradle)
    slug = (package or bundle or ix.root.name).split(".")[-1].lower()
    r["app"] = {"ios_bundle_id": bundle, "ios_version": ios_version, "ios_build": ios_build,
                "android_package": package, "android_version_code": vcode, "slug_guess": slug}

    def exists(*paths):
        for p in paths:
            for g in glob.glob(os.path.expanduser(p), recursive=True):
                return g.replace(str(home), "~")
        return None

    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    slug_keys = {norm(slug), norm(ix.root.name)}

    def slug_file(dirs, exts):
        """A file in dirs whose name (ignoring case/punctuation) contains the app slug."""
        for d in dirs:
            for g in sorted(glob.glob(os.path.expanduser(d) + "/*")):
                name = norm(Path(g).stem)
                if Path(g).suffix in exts and any(k and k in name for k in slug_keys):
                    return g.replace(str(home), "~")
        return None

    # ---- 1 Identity & signing ------------------------------------------------------------
    asc_cfg = exists(str(ix.root / ".asc-config.json"), str(ix.root / "*/.asc-config.json"))
    play_cfg = exists(str(ix.root / ".play-config.json"), str(ix.root / "*/.play-config.json"))
    keystore = slug_file(["~/.config/google-play", "~/.android-keystores"], {".jks", ".keystore"}) \
        or exists(str(ix.root / "**/*.jks"))
    play_keys = slug_file(["~/.config/google-play"], {".json"})
    checks = []
    if has_ios:
        checks += [("ios bundle id", bundle), ("ASC API config (.asc-config.json)", asc_cfg)]
    if has_android:
        checks += [("android applicationId", package), ("upload keystore", keystore),
                   ("Play API config or key", play_cfg or play_keys)]
    r["phases"].append(phase("1 identity-and-signing", checks,
                             ["Store app records can only be confirmed with an API read (ASC GET /v1/apps; Play edits.insert)."]))

    # ---- 2 Port ---------------------------------------------------------------------------
    port_note = []
    if kind in ("expo", "react-native", "flutter"):
        port_note.append(f"{kind}: one codebase; 'port' means making sure both platform builds work.")
    r["phases"].append(phase("2 platform-port", [("ios app", has_ios or None), ("android app", has_android or None)],
                             port_note + ["Parity matrix: .release/parity.md" + (" (present)" if (ix.root / ".release/parity.md").exists() else " (absent)")]))

    # ---- 3 Auth ---------------------------------------------------------------------------
    apple = ix.grep(r"ASAuthorizationAppleIDProvider|SignInWithAppleButton|expo-apple-authentication|AppleAuthentication\.|"
                    r"sign_in_with_apple|@invertase/react-native-apple-authentication|SignInWithApple\.authorize|providerId:\s*['\"]apple")
    apple_email = ix.grep(r"requestedScopes\s*=\s*\[[^\]]*\.email|AppleAuthenticationScope\.EMAIL|AppleIDAuthorizationScopes\.email")
    google = ix.grep(r"GetSignInWithGoogleOption|GetGoogleIdOption|GoogleSignIn|@react-native-google-signin|google_sign_in|"
                     r"Google\.useAuthRequest|Google\.useIdTokenAuthRequest|expo-auth-session/providers/google|"
                     r"@codetrix-studio/capacitor-google-auth|GoogleAuth\.signIn|signInWithGoogle")
    google_client = ix.grep(r"googleWebClientId|GOOGLE_WEB_CLIENT_ID|webClientId|serverClientId", limit=3)
    checks = []
    if has_ios:
        checks += [("Sign in with Apple", apple), ("Apple email scope (account linking)", apple_email)]
    if has_android:
        checks += [("Google sign-in", google), ("Google web client id wired", google_client)]
    r["phases"].append(phase("3 auth", checks, ["Backend verification + email linking live in the server repo; check it there."]))

    # ---- 4 Monetization ------------------------------------------------------------------
    rc = ix.grep(r"Purchases\.configure|import RevenueCat|com\.revenuecat|react-native-purchases|purchases_flutter")
    rc_ios_key = ix.grep(r"appl_[A-Za-z0-9]{10,}", limit=1)
    rc_android_key = ix.grep(r"goog_[A-Za-z0-9]{10,}", limit=1) or ix.grep(r"revenuecatKey|REVENUECAT_KEY", limit=1)
    paywall = [f for f in ix.grep(r"[Pp]aywall", exts={".swift", ".kt", ".tsx", ".ts", ".dart"}, limit=12)
               if not re.search(r"[Tt]est", f)][:3]
    checks = [("RevenueCat SDK", rc), ("paywall UI", paywall)]
    if has_ios:
        checks.append(("RevenueCat iOS key (appl_) in config", rc_ios_key))
    if has_android:
        checks.append(("RevenueCat Play key (goog_) in config", rc_android_key))
    notes = ["Store products, RC entitlement/offering and webhook need API reads to confirm."]
    if has_android and ix.grep(r"Step\.Paywall|PaywallStep\(|OnboardingPaywall", exts={".kt", ".tsx", ".ts", ".dart"}, limit=1):
        notes.append("WARNING: paywall appears to be an onboarding step; Play policy wants it removed from Android onboarding.")
    r["phases"].append(phase("4 monetization", checks, notes))

    # ---- 5 Push --------------------------------------------------------------------------
    aps = ix.grep(r"aps-environment", exts={".entitlements", ".plist", ".json", ".yml"}, limit=2)
    gsj = [ix.rel(p) for p in ix.named("google-services.json")]
    fcm = ix.grep(r"FirebaseMessagingService|firebase-messaging|@react-native-firebase/messaging|expo-notifications|firebase_messaging", limit=3)
    local_notifs = ix.grep(r"UNCalendarNotificationTrigger|UNUserNotificationCenter|AlarmManager|NotificationChannel|scheduleNotificationAsync", limit=3)
    checks = [("local notifications", local_notifs)]
    if has_ios:
        checks.append(("aps-environment entitlement", aps))
    if has_android:
        checks += [("google-services.json", gsj or None), ("FCM service in app", fcm)]
    r["phases"].append(phase("5 push", checks, ["Server-side APNs key / FCM service account: check server credentials."]))

    # ---- 6 Localization ------------------------------------------------------------------
    xcstrings = ix.named("*.xcstrings")
    ios_langs = set()
    for f in xcstrings:
        ios_langs |= set(re.findall(r'"([a-z]{2}(?:-[A-Za-z]{2,4})?)"\s*:\s*\{\s*"(?:stringUnit|variations)"', ix.text(f)))
    ios_langs |= {p.parent.name[:-6] for p in ix.named("*.lproj/Localizable.strings")}
    android_langs = {p.parent.name[7:] for p in ix.named("values-*/strings.xml")}
    i18n = {p.stem for p in ix.named("locales/*.json", "i18n/*.json", "l10n/*.arb", "translations/*.json")}
    checks = []
    if has_ios and kind == "native":
        checks.append(("iOS locales > 1", sorted(ios_langs) if len(ios_langs) > 1 else None))
    if has_android and kind == "native":
        checks.append(("Android locales > 0", sorted(android_langs) if android_langs else None))
    if kind != "native":
        i18n |= {p.stem for p in ix.named("*/locales/*.json", "*/i18n/*.json", "*/lang/*.json", "*/translations/*.json")}
        checks.append(("JS/Dart locale catalogs", sorted(i18n) if len(i18n) > 1 else None))
    r["phases"].append(phase("6 localization", checks))

    # ---- 7 Screenshots -------------------------------------------------------------------
    framecraft = [ix.rel(p) for p in ix.root.rglob("framecraft.json") if "node_modules" not in p.parts][:2]
    fc_exports = sorted({p.parent.name for p in ix.root.rglob("*-iphone-6-9-inch.png") if "node_modules" not in p.parts})
    fastlane_ios_shots = [ix.rel(p) for p in list(ix.root.glob("fastlane/screenshots/*")) + list(ix.root.glob("screenshots/*"))][:3]
    play_shots = sorted({p.parent.parent.parent.name for p in ix.root.rglob("phoneScreenshots/*.png")})
    checks = []
    if has_ios:
        checks.append(("iOS screenshot set (FrameCraft or fastlane)", fc_exports or fastlane_ios_shots or framecraft or None))
    if has_android:
        checks.append(("Play screenshots (local)", play_shots or (fc_exports and ["reuse FrameCraft exports cropped to 2:1"]) or None))
    r["phases"].append(phase("7 screenshots", checks,
                             [f"FrameCraft locales exported: {len(fc_exports)}"] + (["What's live in the stores needs an API read."])))

    # ---- 8 Landing & legal ---------------------------------------------------------------
    cands = [Path(landing)] if landing else [p for p in ix.root.parent.iterdir()
                                              if p.is_dir() and slug.split("-")[0][:5] in p.name.lower()
                                              and any(k in p.name.lower() for k in ("landing", "site", "web", "www"))]
    lp = next((p for p in cands if p.exists()), None)
    land = {}
    if lp:
        li = Index(lp)
        land["dir"] = str(lp).replace(str(home), "~")
        land["cloudflare"] = [li.rel(p) for p in li.named("wrangler.toml", "wrangler.json", "wrangler.jsonc")] or None
        legal_text = " ".join(li.text(p) for p in li.files if p.suffix in {".ts", ".tsx", ".md", ".mdx", ".html", ".json"}
                              and re.search(r"privacy|terms|delete", str(p), re.I) or (p.suffix == ".ts" and "dictionar" in str(p)))
        land["privacy"] = bool(re.search(r"[Pp]rivacy", legal_text))
        land["terms"] = bool(re.search(r"[Tt]erms", legal_text))
        land["delete_account"] = bool(re.search(r"[Dd]elete (my |your )?account|deleteAccount", legal_text))
        land["mentions_google_play"] = "Google Play" in legal_text
        land["mentions_app_store"] = "App Store" in legal_text
        land["locales"] = sorted({p.stem for p in li.named("dictionaries/*.ts", "locales/*.json", "i18n/*.json")})
    checks = [("landing project", land.get("dir")), ("Cloudflare deploy config", land.get("cloudflare")),
              ("privacy + terms + delete-account", (land.get("privacy") and land.get("terms") and land.get("delete_account")) or None)]
    if has_android:
        checks.append(("legal covers Android / Google Play", land.get("mentions_google_play") or None))
    if has_ios:
        checks.append(("legal covers iOS / App Store", land.get("mentions_app_store") or None))
    r["phases"].append(phase("8 landing-and-legal", checks,
                             [f"landing: {land}" if land else "No landing dir found; pass --landing <dir> if it lives elsewhere."]))

    # ---- 9 Store listings ----------------------------------------------------------------
    ios_meta = sorted({p.parent.name for p in ix.root.glob("fastlane/metadata/*/description.txt")}) \
        or sorted({p.stem for p in ix.root.rglob("listing/*.json") if "asc" in str(p)})
    play_meta = sorted({p.parent.name for p in ix.root.rglob("metadata/android/*/full_description.txt")})
    checks = []
    if has_ios:
        checks.append(("ASC listing text (local)", ios_meta or None))
    if has_android:
        checks.append(("Play listing text (local)", play_meta or None))
        # A placeholder launcher icon under a real store icon gets the update rejected (references/app-icon.md).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from icon_check import template_hits
        templates = template_hits(ix.root)
        checks.append(("Android launcher icon is not a template", None if templates else "no known template files"))
        if templates:
            r["icon_templates"] = [f"{path}: {name}" for path, name in templates]
    r["phases"].append(phase("9 store-forms", checks,
                             ["Play app-content declarations (data safety, content rating, target audience, app access) are console-only; check Play Console > App content."]))

    # ---- 10 Release ----------------------------------------------------------------------
    fastfile = [ix.rel(p) for p in ix.named("Fastfile", "Testflight.rb")]
    checks = []
    if has_ios:
        checks.append(("iOS release lane / script", [f for f in fastfile] or ix.grep(r"exportArchive|upload_to_testflight|pilot", limit=2) or None))
    if has_android:
        checks.append(("signed AAB tooling (keystore found)", keystore))
    r["phases"].append(phase("10 release", checks, ["Confirm with API: TestFlight build VALID; Play internal track version code."]))

    # ---- Hygiene (always reported; fix before shipping) --------------------------------------
    import subprocess
    hyg = []
    try:
        tracked = subprocess.run(["git", "-C", str(ix.root), "ls-files"], capture_output=True, text=True, timeout=30).stdout.split()
    except Exception:
        tracked = []
    secret_like = []
    for t in tracked:
        tp = ix.root / t
        if t.endswith("debug.keystore"):  # the shared Android debug key isn't a secret
            continue
        if re.search(r"\.(p8|p12|jks|keystore|mobileprovision)$|AuthKey_|service[_-]?(account|key).*\.json$", t, re.I):
            secret_like.append(t)
        elif t.endswith(".json") and tp.exists() and tp.stat().st_size < 20000 and '"private_key"' in ix.text(tp):
            secret_like.append(t)
    if secret_like:
        hyg.append(f"SECRETS TRACKED IN GIT (rotate + untrack): {secret_like[:6]}")
    untracked_keys = [ix.rel(p) for p in ix.named("*.p8", "AuthKey_*") if ix.rel(p) not in tracked][:3]
    if untracked_keys:
        hyg.append(f"key files inside the repo (make sure they're gitignored): {untracked_keys}")
    if has_android:
        gt = " ".join(ix.text(f) for f in app_gradle)
        if re.search(r"release\s*\{[^}]*signingConfig\s*=?\s*signingConfigs\.debug", gt, re.S):
            hyg.append("Android release buildType is signed with the DEBUG key")
        if kind == "expo" and ix.named("eas.json"):
            hyg.append("Expo/EAS: the Android upload key and iOS certs may be EAS-managed (check `eas credentials`) rather than local")
        manifests = " ".join(ix.text(f) for f in ix.named("AndroidManifest.xml") if "/build/" not in str(f))
        perms = set(re.findall(r'android\.permission\.([A-Z_]+)', manifests + ix.text(ix.root / "app.json") if (ix.root / "app.json").exists() else manifests))
        sensitive = perms & {"RECORD_AUDIO", "CAMERA", "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "READ_CONTACTS",
                             "READ_MEDIA_IMAGES", "READ_EXTERNAL_STORAGE", "SCHEDULE_EXACT_ALARM", "USE_EXACT_ALARM", "AD_ID"}
        if sensitive:
            hyg.append(f"sensitive Android permissions declared (each needs a real use + Play declaration): {sorted(sensitive)}")
    # Package/endpoint names only: bare words like "amplitude" also match ordinary code (vibration amplitude).
    sdk_patterns = {"Firebase Analytics": r"firebase[-_/]analytics|FirebaseAnalytics|@react-native-firebase/analytics|@capacitor-firebase/analytics",
                    "Crashlytics": r"firebase[-_/]crashlytics|FirebaseCrashlytics", "Sentry": r"@sentry/|sentry-cocoa|io\.sentry",
                    "Mixpanel": r"com\.mixpanel|mixpanel-react-native|mixpanel-browser|import Mixpanel",
                    "Amplitude": r"com\.amplitude|@amplitude/|AmplitudeSwift|import Amplitude",
                    "PostHog": r"posthog-react-native|com\.posthog|PostHogSDK|posthog-js", "AppsFlyer": r"appsflyer",
                    "Adjust": r"com\.adjust\.sdk|react-native-adjust", "Meta SDK": r"FBSDKCoreKit|facebook-android-sdk|react-native-fbsdk",
                    "AdMob/Ads": r"google-mobile-ads|GADMobileAds|play-services-ads",
                    "OpenAI": r"api\.openai\.com|from ['\"]openai['\"]|com\.openai", "Replicate": r"api\.replicate\.com|from ['\"]replicate['\"]",
                    "Anthropic": r"api\.anthropic\.com|@anthropic-ai/sdk", "RevenueCat": r"com\.revenuecat|react-native-purchases|import RevenueCat|purchases_flutter"}
    sdks = [name for name, rx in sdk_patterns.items()
            if ix.grep(rx, exts={".swift", ".kt", ".kts", ".ts", ".tsx", ".js", ".dart", ".gradle", ".json", ".rb"}, limit=1)]
    r["data_processors_in_code"] = sdks
    r["hygiene"] = hyg

    state = ix.root / ".release/sdlc-state.json"
    r["state_file"] = str(state) if state.exists() else None
    return r


def print_table(r):
    s, a = r["stack"], r["app"]
    print(f"Project: {r['root']}")
    print(f"Stack:   {s['kind']}  ios={s['ios']}  android={s['android']}")
    print(f"App:     ios={a['ios_bundle_id']} v{a['ios_version']} ({a['ios_build']})   android={a['android_package']} vc={a['android_version_code']}")
    if r["state_file"]:
        print(f"State:   {r['state_file']}")
    print(f"Data processors found in code (legal pages + privacy labels must name them): {r['data_processors_in_code'] or 'none'}")
    for h in r["hygiene"]:
        print(f"!  {h}")
    print()
    for p in r["phases"]:
        mark = {"done": "✓", "partial": "◐", "missing": "✗"}[p["status"]]
        print(f"{mark} {p['phase']:<26} {p['status']}")
        for label, ev in p["have"].items():
            ev_s = ", ".join(map(str, ev[:3])) if isinstance(ev, list) else str(ev)
            print(f"    + {label}: {ev_s[:110]}")
        for label in p["missing"]:
            print(f"    - {label}")
        for n in p["notes"]:
            print(f"    · {n[:160]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        sys.exit(__doc__)
    landing = args[args.index("--landing") + 1] if "--landing" in args else None
    result = audit(args[0], landing)
    if "--json" in args:
        print(json.dumps(result, indent=1, default=str))
    else:
        print_table(result)

# Driving consoles in the user's browser

Use the browser for consoles that have no API: Play Console app creation and app content, Users and permissions, App signing, Google Cloud OAuth (Google Auth Platform), the Firebase console, the RevenueCat dashboard, and occasionally App Store Connect. **Do these steps yourself.** Don't list them as "user actions" when a signed-in browser is available.

## Which tool
1. **Argent against the user's Chromium browser (Brave, Chrome or Edge) on CDP port 9222.** This is the method that works. `mcp__argent__list-devices` lists the browser as `chromium-cdp-9222`. Drive it with `open-url`, `gesture-tap`, `keyboard`, `gesture-scroll`, `await-ui-element`, `screenshot` and `run-sequence`. The user prefers it.
2. An attached browser tool (Claude in Chrome, computer use), if the session has one.
3. **Don't** write Bash scripts with Playwright or raw CDP (`connectOverCDP`, `Runtime.evaluate`, `Input.insertText`) to fill consoles. Auto mode's classifier blocks them even after the user grants permission, and `connectOverCDP` times out on a browser with many tabs and extensions. A read-only `curl http://127.0.0.1:9222/json/list` is fine.

If nothing is listening on 9222, ask the user to restart the browser with `--remote-debugging-port=9222`. Never copy their profile or cookies.

## Argent on Google consoles
- **Google Cloud and Play Console pages blow the describe budget.** Each interaction tool returns a DOM tree that gets truncated, often to 25k+ tokens of sidebar. Don't call `describe` on these pages. Use:
  - `await-ui-element` with a text selector to wait for a page or a state ("Publishing status", "In production").
  - `screenshot` to see the page. Tap at the element's centre in normalized coordinates (pixel ÷ displayed width/height). This is the one place where reading coordinates from a screenshot is acceptable, because the tree is truncated. Take a fresh screenshot after anything that can shift the layout.
  - Keyboard navigation: tap the first field, then `keyboard {text}` and `keyboard {key:"tab"}` in one `run-sequence`. For Material dropdowns, focus the field, press `arrow-down` to open it, `arrow-down` to the option, then `enter`.
- **Reading generated values** (client ids, SHA-1s): click the console's copy button, then read the value with `pbpaste` in Bash. Never transcribe long ids from a screenshot.
- Client detail pages: deep links to `/auth/clients/<id>` can hang on a spinner. Open the Clients list and click the name instead.
- Pages load slowly. Wait with `await-ui-element` (timeouts of 20–30s), not repeated screenshots.

## Known layouts
- **Play create app**: `https://play.google.com/console/u/0/developers/<devId>/create-new-app`. Fill the app name, choose App, then Free. Choosing **Free inserts a banner that pushes the declaration checkboxes down**, so take a new screenshot before ticking them. The page also asks for the package name when it's shown.
- **Play Users and permissions**: Users and permissions → the service account → **Add app** → choose the app → grant view app information, release to testing tracks, and manage store presence → Apply → Save. After that a package-scoped API read works.
- **Play app signing SHA-1**: Test and release → App integrity → App signing. Use the copy button next to "SHA-1 certificate fingerprint" under the app signing key.
- **GCP Android OAuth client**: `https://console.cloud.google.com/auth/clients/create?project=<projectNumber>`. Choose Android as the application type (arrow-down and enter), then Tab-fill the name, package name and SHA-1. Click Create, then copy the client id from the dialog.
- **GCP consent screen**: Branding needs a home page URL, privacy and terms URLs, **and every domain those URLs use listed under Authorized domains**, each added with its own "Add domain" click. Until then, "Publish app" on the Audience page stays disabled. Then go to Audience → Publish app → Confirm and wait for "In production".

## Safety
- Never type passwords or 2FA codes. If a page asks to re-authenticate, send the user the exact URL to sign in at, then continue.
- Don't accept legal agreements, change billing, or invite human users unless the user asks.
- Uploading private keys through a file input may be blocked. Prefer "select existing key" options.

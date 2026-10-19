# Driving consoles in the user's browser

Use the browser only for consoles with no API: Play Console app content, the Firebase console, Google Cloud OAuth, the RevenueCat dashboard, and occasionally App Store Connect. Prefer an attached browser tool (Claude in Chrome, computer use) if the session has one. Otherwise use plain Chrome DevTools Protocol against the user's running Chromium browser (Chrome, Brave or Edge), where they're already signed in.

## Setup
- The browser must be running with `--remote-debugging-port=9222`. If it isn't, ask the user to restart it with that flag. Never copy their profile or cookies elsewhere.
- Keep a small Node helper (`cdp.mjs`) that talks to `http://127.0.0.1:9222/json` and the tab websocket. It needs these commands:
  - `tabs` and `open <url>`
  - `nav <tabId> <url>`
  - `eval <tabId> <js>`, which returns JSON
  - `click <tabId> <selector|text>` and `type <tabId> <selector> <text>`, sent as real `Input.dispatch*` events, because Angular and Material forms ignore `.value=`
  - `key`
  - `file <tabId> <selector> <path>` (`DOM.setFileInputFiles`)
  - `shot <tabId> <out.png>`
- Always open a new tab for your work and leave the user's tabs alone. Re-find your tab by id after navigation, because titles change.

## Techniques
- **Read generated values,** such as a client id from a "copy" button: hook `navigator.clipboard.writeText` before clicking.
- **Capture downloads** (CSV templates, service-account keys) when a download manager extension swallows them: hook `window.Blob` / `URL.createObjectURL` and read the content from the page. Write it to a file outside the repo straight away; never print key material.
- **Find form controls by visible text,** then click them by coordinates, using `getBoundingClientRect`. Consoles re-render often, so query again after each step.
- Use internal JSON APIs when the console calls them from the page (RevenueCat's `/internal/v1/...` with `X-Requested-With: XMLHttpRequest`). That's faster and steadier than clicking.

## Safety
- Never type passwords or 2FA codes. If a console asks to re-authenticate, hand the step to the user.
- Uploading private keys (`.p8`, service-account JSON) through a file input may be blocked. Prefer the console's "select existing key" option, or have the user do that step.
- Don't accept legal agreements, change billing, or invite users without the user's explicit request.

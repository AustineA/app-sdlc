# Tools and companion skills

`scripts/setup.sh` checks all of these and installs what can be scripted (`--install [groups]`). This table is the reference for what each one is for and where it comes from.

| Group | Tool / skill | Used in phase | Install |
|---|---|---|---|
| core | Node.js 18+, Python 3, git | all | system packages |
| core | `gh` (GitHub CLI) | landing repo, releases | `brew install gh` |
| core | Python libs: google-auth, requests, pillow, pyyaml | Play API scripts, screenshot crops | `python3 -m pip install --user google-auth requests pillow pyyaml` |
| ios | Xcode | port, release | App Store (manual) |
| ios | XcodeGen | iOS projects defined in `project.yml` | `brew install xcodegen` |
| ios | fastlane | TestFlight, `supply` | `brew install fastlane` |
| ios | XcodeBuildMCP CLI + `xcodebuildmcp-cli` skill | build/run/test on simulators and devices | `brew tap getsentry/xcodebuildmcp && brew install xcodebuildmcp`, then `xcodebuildmcp init` |
| android | JDK 17+, Android SDK, emulator + AVD | port, QA, release | Android Studio (manual); create a Pixel AVD with a Play Store image |
| android | bundletool | install the exact release AAB on an emulator to check the launcher icon before production | `brew install bundletool` |
| device | **Argent** (MCP server + argent-* skills) | e2e QA: tap, type, describe and screenshot on iOS sims and Android emulators | `npx -y @swmansion/argent@latest init -y`, then restart the agent so the MCP tools load |
| screenshots | **framecraft** CLI + `framecraft-layer-design` skill | layered App Store screenshots for every locale | `npx -y github:AustineA/framecraft install` (installs both) |
| screenshots | `aso-appstore-screenshots` skill | benefit-led headlines | cloned from github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots |
| screenshots | libraqm | Arabic/Devanagari shaping in Pillow | `brew install libraqm` |
| landing | `app-landing-seo` skill (+ `gpt-image`) | landing site, guides, SEO | `npx -y github:AustineA/app-landing-seo` |
| landing | wrangler | Cloudflare deploy | via `npx wrangler` (no install); `npx wrangler login` once |
| store | `asc-locale` skill | App Store metadata, localization, screenshots upload | `npx -y github:AustineA/asc-locale` |
| store | `testflight-upload` skill | archive, export, upload, poll VALID | `npx -y github:AustineA/testflight-upload` |
| store | `play-store-publisher` skill | Play listings, AAB upload, tracks | `npx -y github:AustineA/play-store-publisher` |

The AustineA installers put each skill in `~/.agents/skills/<name>` and symlink it into Claude Code, Codex, Cursor, Windsurf, Antigravity, Trae and Amp. A skill that an agent already has as a real folder is left alone.

## Rules
- Install only the groups the plan needs. An iOS-only app doesn't need the android group, and an app with a live site doesn't need landing.
- Global installs are fine when the user asked to ship, but say what you're installing in one line first. Never use `sudo`. Xcode and Android Studio are manual, so put them on the user list with the exact step.
- After installing Argent or any MCP server, the agent has to restart before its tools appear. Say so, and record in the state file where to resume.

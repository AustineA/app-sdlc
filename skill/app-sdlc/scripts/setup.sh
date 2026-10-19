#!/usr/bin/env bash
# Checks (default) or installs (--install) the tools and companion skills app-sdlc uses.
#
#   setup.sh                       report what's present and what's missing
#   setup.sh --install             install whatever is missing (all groups)
#   setup.sh --install ios android screenshots landing   only these groups
#
# Groups: core, ios, android, device, screenshots, landing, store
# Everything comes from its official source. Global installs go through brew, npx, pip --user
# or a git clone into ~/.agents/skills. Xcode and Android Studio can't be scripted; they're reported.
set -u
INSTALL=0
SELECTED=()
for arg in "$@"; do
  case "$arg" in
    --install) INSTALL=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) SELECTED+=("$arg") ;;
  esac
done
[ ${#SELECTED[@]} -eq 0 ] && SELECTED=(core ios android device screenshots landing store)
want() { local g; for g in "${SELECTED[@]}"; do [ "$g" = "$1" ] && return 0; done; return 1; }

MISSING=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
miss() { printf "  \033[31m✗\033[0m %s\n" "$1"; MISSING=$((MISSING + 1)); }
info() { printf "    %s\n" "$1"; }
has()  { command -v "$1" >/dev/null 2>&1; }
skill_installed() { [ -f "$HOME/.agents/skills/$1/SKILL.md" ] || [ -f "$HOME/.claude/skills/$1/SKILL.md" ] || [ -f "$HOME/.codex/skills/$1/SKILL.md" ]; }

# tool <label> <check-command> <install-command|""> [manual hint]
tool() {
  local label="$1" check="$2" cmd="$3" hint="${4:-}"
  if eval "$check" >/dev/null 2>&1; then ok "$label"; return; fi
  if [ "$INSTALL" = 1 ] && [ -n "$cmd" ]; then
    echo "  → installing $label: $cmd"
    if eval "$cmd" && eval "$check" >/dev/null 2>&1; then ok "$label (installed)"; return; fi
  fi
  miss "$label"
  [ -n "$cmd" ] && info "install: $cmd"
  [ -n "$hint" ] && info "$hint"
}

# Clone a third-party skill repo into ~/.agents/skills and link it into the agents present.
link_skill() {
  local name="$1" repo="$2" sub="${3:-}" dest="$HOME/.agents/skills/$1" tmp
  mkdir -p "$HOME/.agents/skills"
  tmp=$(mktemp -d) && git clone -q --depth 1 "$repo" "$tmp/repo" || return 1
  rm -rf "$dest" && cp -R "$tmp/repo/$sub" "$dest" && rm -rf "$tmp"
  for root in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.cursor/skills"; do
    [ -d "$(dirname "$root")" ] || continue
    mkdir -p "$root"; [ -e "$root/$name" ] || ln -s "$dest" "$root/$name"
  done
}

if want core; then
  echo "core"
  tool "node 18+"   "node -e 'process.exit(+process.versions.node.split(\".\")[0] >= 18 ? 0 : 1)'" "" "install Node.js 18+ (https://nodejs.org or brew install node)"
  tool "python3"    "python3 --version" "" "install Python 3"
  tool "git"        "git --version" ""
  tool "gh (GitHub CLI)" "gh --version" "brew install gh"
  tool "python: google-auth, requests, pillow, pyyaml" \
       "python3 -c 'import google.auth, requests, PIL, yaml'" \
       "python3 -m pip install --user --quiet google-auth requests pillow pyyaml"
fi

if want ios; then
  echo "ios"
  if [ "$(uname)" != "Darwin" ]; then info "skipped: iOS builds need macOS"; else
    tool "Xcode (xcodebuild)" "xcodebuild -version" "" "install Xcode from the App Store, then: sudo xcode-select -s /Applications/Xcode.app"
    tool "XcodeGen"           "xcodegen --version" "brew install xcodegen"
    tool "fastlane"           "fastlane --version" "brew install fastlane"
    tool "XcodeBuildMCP CLI"  "xcodebuildmcp --help" "brew tap getsentry/xcodebuildmcp && brew install xcodebuildmcp"
    tool "xcodebuildmcp-cli skill" "skill_installed xcodebuildmcp-cli" "xcodebuildmcp init"
  fi
fi

if want android; then
  echo "android"
  tool "JDK 17+" "java -version" "" "install a JDK 17+ (Android Studio bundles one: export JAVA_HOME=\"/Applications/Android Studio.app/Contents/jbr/Contents/Home\")"
  tool "adb"     "adb version" "" "install Android Studio (SDK Platform Tools), then add \$ANDROID_HOME/platform-tools to PATH"
  tool "Android emulator + an AVD" "emulator -list-avds | grep -q ." "" "Android Studio > Device Manager > create a Pixel AVD with a Play Store image"
  tool "keytool" "keytool -help" "" "comes with the JDK"
fi

if want device; then
  echo "device (simulator/emulator driving for e2e QA)"
  tool "Argent (MCP + skills)" "has argent && skill_installed argent-device-interact" "npx -y @swmansion/argent@latest init -y" \
       "Argent drives iOS simulators and Android emulators; restart the agent after install so its MCP tools load"
fi

if want screenshots; then
  echo "screenshots"
  # One install gives the framecraft CLI and its framecraft-layer-design skill.
  tool "framecraft CLI + framecraft-layer-design skill" "framecraft --help && skill_installed framecraft-layer-design" "npx -y github:AustineA/framecraft install" "make sure ~/.local/bin is on PATH"
  tool "aso-appstore-screenshots skill" "skill_installed aso-appstore-screenshots" \
       "link_skill aso-appstore-screenshots https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots.git"
  tool "libraqm (Arabic/Devanagari text shaping in Pillow)" "ls /opt/homebrew/lib/libraqm* /usr/local/lib/libraqm* 2>/dev/null | grep -q ." "brew install libraqm"
fi

if want landing; then
  echo "landing"
  tool "app-landing-seo skill" "skill_installed app-landing-seo" "npx -y github:AustineA/app-landing-seo"
  tool "wrangler (Cloudflare)" "npx -y wrangler --version" "" "runs through npx; log in once with: npx wrangler login"
fi

if want store; then
  echo "store"
  tool "asc-locale skill (App Store metadata/screenshots)" "skill_installed asc-locale" "npx -y github:AustineA/asc-locale"
  tool "testflight-upload skill" "skill_installed testflight-upload" "npx -y github:AustineA/testflight-upload"
  tool "play-store-publisher skill" "skill_installed play-store-publisher" "npx -y github:AustineA/play-store-publisher"
fi

echo
if [ "$MISSING" = 0 ]; then echo "All set."; else
  echo "$MISSING missing."
  [ "$INSTALL" = 0 ] && echo "Run again with --install to install what can be scripted."
fi
exit 0

#!/usr/bin/env node

import {
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readdirSync,
  readlinkSync,
  rmSync,
  symlinkSync,
  unlinkSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PACKAGE_TITLE = "App Sdlc";
const SKILLS = ["app-sdlc"];
const NEXT_STEP = "Ship <path-to-your-app> to the App Store and Google Play: do whatever is still missing";
const INSTALL_HOME = process.env.SKILL_INSTALL_HOME
  ? resolve(process.env.SKILL_INSTALL_HOME)
  : homedir();
const SOURCE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "skill");
const CANONICAL_ROOT = join(INSTALL_HOME, ".agents", "skills");

const AGENTS = [
  { name: "Claude Code", dir: join(INSTALL_HOME, ".claude", "skills") },
  { name: "Codex", dir: join(INSTALL_HOME, ".codex", "skills") },
  { name: "Cursor", dir: join(INSTALL_HOME, ".cursor", "skills") },
  { name: "Windsurf", dir: join(INSTALL_HOME, ".windsurf", "skills") },
  { name: "Antigravity", dir: join(INSTALL_HOME, ".antigravity", "skills") },
  { name: "Trae", dir: join(INSTALL_HOME, ".trae", "skills") },
  { name: "Amp", dir: join(INSTALL_HOME, ".amp", "skills") },
];

const command = process.argv[2] || "install";
const success = (message) => console.log(`  ✅ ${message}`);
const skip = (message) => console.log(`  ⏭️  ${message}`);
const warn = (message) => console.log(`  ⚠️  ${message}`);

function pathExists(path) {
  try {
    lstatSync(path);
    return true;
  } catch {
    return false;
  }
}

function installSkill(skillName) {
  const source = join(SOURCE_ROOT, skillName);
  const destination = join(CANONICAL_ROOT, skillName);
  if (!existsSync(join(source, "SKILL.md"))) {
    throw new Error(`Packaged skill is missing SKILL.md: ${source}`);
  }
  mkdirSync(destination, { recursive: true });
  cpSync(source, destination, { recursive: true, force: true });
  success(`${skillName} installed to ~/.agents/skills/${skillName}`);
}

function linkSkill(agent, skillName) {
  const target = join(CANONICAL_ROOT, skillName);
  const linkPath = join(agent.dir, skillName);
  if (pathExists(linkPath)) {
    try {
      const currentTarget = readlinkSync(linkPath);
      if (resolve(dirname(linkPath), currentTarget) === target) {
        skip(`${agent.name}: ${skillName} already linked`);
        return true;
      }
      unlinkSync(linkPath);
    } catch {
      warn(`${agent.name}: ${linkPath} exists and is not a symlink; skipping`);
      return false;
    }
  }
  symlinkSync(target, linkPath);
  success(`${agent.name}: ${skillName} → ~/.agents/skills/${skillName}`);
  return true;
}

function install() {
  console.log(`\n📦 Installing ${PACKAGE_TITLE}...\n`);
  mkdirSync(CANONICAL_ROOT, { recursive: true });
  for (const skillName of SKILLS) installSkill(skillName);

  console.log("\n🔗 Linking to agents...\n");
  let linked = 0;
  for (const agent of AGENTS) {
    const agentRoot = resolve(agent.dir, "..");
    if (!existsSync(agentRoot)) {
      skip(`${agent.name} not found`);
      continue;
    }
    mkdirSync(agent.dir, { recursive: true });
    for (const skillName of SKILLS) {
      if (linkSkill(agent, skillName)) linked += 1;
    }
  }

  console.log(`\n🎉 Done! Installed ${SKILLS.length} skill(s) and created ${linked} link(s).\n`);
  if (NEXT_STEP) console.log(`Next, ${NEXT_STEP}\n`);
}

function uninstall() {
  console.log(`\n🗑️  Uninstalling ${PACKAGE_TITLE}...\n`);
  for (const agent of AGENTS) {
    for (const skillName of SKILLS) {
      const linkPath = join(agent.dir, skillName);
      if (!pathExists(linkPath)) continue;
      try {
        readlinkSync(linkPath);
        unlinkSync(linkPath);
        success(`Removed ${agent.name}: ${skillName}`);
      } catch {
        skip(`${agent.name}: ${skillName} is not a symlink; leaving it`);
      }
    }
  }

  for (const skillName of SKILLS) {
    const destination = join(CANONICAL_ROOT, skillName);
    if (existsSync(destination)) {
      rmSync(destination, { recursive: true, force: true });
      success(`Removed ~/.agents/skills/${skillName}`);
    }
  }
  console.log("\n✅ Uninstalled.\n");
}

function status() {
  console.log(`\n📊 ${PACKAGE_TITLE} status\n`);
  for (const skillName of SKILLS) {
    const destination = join(CANONICAL_ROOT, skillName);
    if (existsSync(destination)) {
      success(`${skillName} installed at ~/.agents/skills/${skillName}`);
      console.log(`  Files: ${readdirSync(destination).join(", ")}`);
    } else {
      warn(`${skillName} not installed`);
    }
  }

  console.log();
  for (const agent of AGENTS) {
    const installed = SKILLS.filter((skillName) => pathExists(join(agent.dir, skillName)));
    if (installed.length > 0) success(`${agent.name}: ${installed.join(", ")}`);
    else if (existsSync(resolve(agent.dir, ".."))) skip(`${agent.name}: not linked`);
  }
  console.log();
}

function help() {
  console.log(`
${PACKAGE_TITLE} installer

Commands:
  install      Install all packaged skills and link detected agents (default)
  uninstall    Remove managed skills and their links
  status       Show installation and link status
  help         Show this help
`);
}

const commands = { install, uninstall, status, help };
if (!commands[command]) {
  warn(`Unknown command: ${command}`);
  help();
  process.exitCode = 1;
} else {
  commands[command]();
}

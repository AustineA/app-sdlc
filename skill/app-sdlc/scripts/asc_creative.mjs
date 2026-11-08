#!/usr/bin/env node
// iOS 27 creative assets → App Store Connect Asset Library, placed on a version localization.
// Generalized from Grain's appstore/asc/creative.mjs (shipped 18 locales, 2026-11-06).
//
//   node asc_creative.mjs --project <root> --version <versionString|id> --dir <export dir> [--dry-run] [locale ...]
//
// <export dir>/<ASC locale>/{header.png, search.png, search.mp4}; each file that exists is uploaded.
// header.png → PRODUCT_PAGE_HEADER_ASSET; search.mp4 → APP_STORE_SEARCH_RESULTS_ASSET; search.png stays in
// the library as the fallback (the slot takes one asset), unless there is no video, then it takes the slot.
// Ids are kept in <export dir>/creative.json so reruns skip finished work. Reads <root>/.asc-config.json
// (keyId, issuerId, keyPath, bundleId). Only touches an editable version; never submits.
import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { createSign } from "node:crypto";
import { join, resolve } from "node:path";

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : undefined; };
const flag = (k) => { const i = args.indexOf(k); if (i >= 0) { args.splice(i, 1); return true; } return false; };
const ROOT = resolve(opt("--project") ?? ".");
const VERSION = opt("--version");
const DIR = resolve(ROOT, opt("--dir") ?? "appstore/creative-export");
const DRY = flag("--dry-run");
if (!VERSION) { console.error("--version <versionString|id> is required"); process.exit(2); }

const cfg = JSON.parse(readFileSync(join(ROOT, ".asc-config.json"), "utf8"));
const key = readFileSync(cfg.keyPath.replace(/^~/, process.env.HOME), "utf8");
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
function jwt() {
  const h = b64({ alg: "ES256", kid: cfg.keyId, typ: "JWT" }), now = Math.floor(Date.now() / 1000);
  const p = b64({ iss: cfg.issuerId, iat: now, exp: now + 1100, aud: "appstoreconnect-v1" });
  const s = createSign("SHA256"); s.update(`${h}.${p}`);
  return `${h}.${p}.${s.sign({ key, dsaEncoding: "ieee-p1363" }).toString("base64url")}`;
}
async function api(method, path, body) {
  const r = await fetch(`https://api.appstoreconnect.apple.com${path}`, { method,
    headers: { Authorization: `Bearer ${jwt()}`, "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  const t = await r.text(); let j; try { j = JSON.parse(t); } catch { j = t; }
  if (!r.ok) throw new Error(`${method} ${path} ${r.status} ${JSON.stringify(j?.errors?.map((e) => e.detail || e.title) ?? j)}`);
  return j;
}

const TYPE = { image: "appAssetLibraryImages", video: "appAssetLibraryVideos" };
const EDITABLE = /PREPARE_FOR_SUBMISSION|DEVELOPER_REJECTED|REJECTED|METADATA_REJECTED|INVALID_BINARY/;
const STATE_FILE = join(DIR, "creative.json");
const STATE = existsSync(STATE_FILE) ? JSON.parse(readFileSync(STATE_FILE, "utf8")) : {};
const save = () => { if (!DRY) writeFileSync(STATE_FILE, JSON.stringify(STATE, null, 1)); };

const app = (await api("GET", `/v1/apps?filter[bundleId]=${cfg.bundleId}`)).data[0];
if (!app) throw new Error(`no app for ${cfg.bundleId}`);
const versions = (await api("GET", `/v1/apps/${app.id}/appStoreVersions?limit=20&fields[appStoreVersions]=versionString,appStoreState,platform`)).data;
const ver = versions.find((v) => v.id === VERSION || (v.attributes.versionString === VERSION && v.attributes.platform === "IOS"));
if (!ver) throw new Error(`version ${VERSION} not found: ${versions.map((v) => v.attributes.versionString).join(", ")}`);
if (!EDITABLE.test(ver.attributes.appStoreState)) throw new Error(`version ${ver.attributes.versionString} is ${ver.attributes.appStoreState}, not editable`);
const locs = (await api("GET", `/v1/appStoreVersions/${ver.id}/appStoreVersionLocalizations?limit=50&fields[appStoreVersionLocalizations]=locale`)).data;
const available = existsSync(DIR) ? readdirSync(DIR).filter((d) => statSync(join(DIR, d)).isDirectory()) : [];
const LOCALES = args.length ? args : available.filter((d) => locs.some((l) => l.attributes.locale === d));
console.log(`${app.attributes?.name ?? app.id} ${ver.attributes.versionString} (${ver.attributes.appStoreState}); ${locs.length} localizations; folders: ${available.join(" ") || "none"}`);
const missing = locs.map((l) => l.attributes.locale).filter((l) => !available.includes(l));
if (missing.length) console.log("no assets for:", missing.join(" "));

function assetsFor(dir) {
  const has = (f) => existsSync(join(dir, f));
  return [
    { key: "header", file: "header.png", kind: "image", placement: "PRODUCT_PAGE_HEADER_ASSET" },
    { key: "search", file: "search.png", kind: "image", placement: has("search.mp4") ? null : "APP_STORE_SEARCH_RESULTS_ASSET" },
    { key: "search-video", file: "search.mp4", kind: "video", placement: "APP_STORE_SEARCH_RESULTS_ASSET" },
  ].filter((a) => has(a.file));
}

async function upload(a, dir, locale) {
  const bytes = readFileSync(join(dir, a.file));
  const res = (await api("POST", `/v1/${TYPE[a.kind]}`, { data: { type: TYPE[a.kind],
    attributes: { fileName: `${cfg.bundleId.split(".").pop()}-${a.key}-${locale}.${a.file.split(".").pop()}`, fileSize: bytes.length, category: "CREATIVE_ASSETS" },
    relationships: { assetLibrary: { data: { type: "appAssetLibraries", id: app.id } } } } })).data;
  for (const op of res.attributes.uploadOperations) {
    const r = await fetch(op.url, { method: op.method, headers: Object.fromEntries(op.requestHeaders.map((h) => [h.name, h.value])),
      body: bytes.subarray(op.offset, op.offset + op.length) });
    if (!r.ok) throw new Error(`upload ${a.key}: ${r.status} ${await r.text()}`);
  }
  await api("PATCH", `/v1/${TYPE[a.kind]}/${res.id}`, { data: { type: TYPE[a.kind], id: res.id, attributes: { uploaded: true } } });
  return res.id;
}

async function settle(a, id) {
  for (let i = 0; i < 60; i++) {
    const at = (await api("GET", `/v1/${TYPE[a.kind]}/${id}`)).data.attributes;
    const s = JSON.stringify(at.state ?? at.assetDeliveryState ?? at.previewFrameImage?.state ?? "");
    if (/FAILED|ERROR/.test(s) && !/"errors":null/.test(s)) throw new Error(`${a.key} processing failed: ${s.slice(0, 300)}`);
    if (/PREPARE_FOR_SUBMISSION|COMPLETE|READY/.test(s)) return s;
    await new Promise((r) => setTimeout(r, 10000));
  }
  throw new Error(`${a.key} still processing after 10 min`);
}

let failures = 0;
for (const locale of LOCALES) {
  const dir = join(DIR, locale), loc = locs.find((l) => l.attributes.locale === locale);
  if (!loc) { console.log(`--- ${locale}: no such localization on this version, skipped`); continue; }
  const ids = (STATE[locale] ??= {}), assets = assetsFor(dir);
  console.log(`--- ${locale}: ${assets.map((a) => `${a.file} ${(statSync(join(dir, a.file)).size / 1e6).toFixed(1)} MB`).join(", ") || "nothing"}`);
  if (DRY) continue;
  try {
    for (const a of assets) {
      if (!ids[a.key]) { ids[a.key] = await upload(a, dir, locale); save(); console.log("uploaded", a.key, ids[a.key]); }
      console.log(a.key, "state", (await settle(a, ids[a.key])).slice(0, 80));
    }
    for (const a of assets) {
      if (!a.placement || ids[`${a.key}-placement`]) continue;
      const rel = { [a.kind]: { data: { type: TYPE[a.kind], id: ids[a.key] } } };
      const p = (await api("POST", "/v1/appAssetLibraryPlacements", { data: { type: "appAssetLibraryPlacements",
        attributes: { placementType: a.placement },
        relationships: { ...rel, appStoreVersionLocalization: { data: { type: "appStoreVersionLocalizations", id: loc.id } } } } })).data;
      ids[`${a.key}-placement`] = p.id; save();
      console.log("placed", a.key, a.placement, p.id);
    }
    // verify: placements read back by id (the localization has no placements relationship to list)
    // A video placement stays PENDING until Apple finishes its preview frame (~10 min); wait up to 20.
    for (const k of Object.keys(ids).filter((k) => k.endsWith("-placement"))) {
      let at;
      for (let i = 0; i < 40; i++) {
        at = (await api("GET", `/v1/appAssetLibraryPlacements/${ids[k]}`)).data.attributes;
        if (at.state !== "PENDING" || process.env.NO_WAIT) break;
        await new Promise((r) => setTimeout(r, 30000));
      }
      console.log("verify", k, at.placementType, at.state);
      if (at.state !== "ACTIVE") failures++;
    }
  } catch (e) { failures++; console.log(`${locale} FAILED:`, e.message.slice(0, 400)); }
}
process.exit(failures ? 1 : 0);

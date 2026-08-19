// The manifest mechanism — what makes "update never touches your files"
// checkable instead of a promise. init/update record every framework-owned
// file (repo-relative path → sha256) in .vteam/manifest.json; update may
// overwrite a file ONLY when its on-disk hash matches the manifest (i.e. the
// user never modified it). Anything else gets `<file>.new` next to it plus a
// loud conflict list. Enforcement is structural: update's only write path is
// ManifestGuard.sync().
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export const MANIFEST_REL = ".vteam/manifest.json";

export function sha256(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

export function loadManifest(root) {
  const f = path.join(root, MANIFEST_REL);
  if (!fs.existsSync(f)) return null;
  try {
    const m = JSON.parse(fs.readFileSync(f, "utf8"));
    return m && typeof m.files === "object" ? m : null;
  } catch {
    return null;
  }
}

export class ManifestGuard {
  constructor(root) {
    this.root = root;
    this.old = loadManifest(root); // null on pre-manifest installs
    this.files = {};               // the manifest being built this run
    this.conflicts = [];           // rel paths preserved as <rel>.new
  }

  _abs(rel) { return path.join(this.root, ...rel.split("/")); }

  _put(rel, content, mode) {
    const abs = this._abs(rel);
    fs.mkdirSync(path.dirname(abs), { recursive: true });
    fs.writeFileSync(abs, content);
    if (mode !== undefined) fs.chmodSync(abs, mode);
  }

  /** init only: write unconditionally and record — a fresh install owns its tree. */
  force(rel, content, mode) {
    this._put(rel, content, mode);
    this.files[rel] = sha256(content);
  }

  /** Record a file the framework wrote through another path (writeIfAbsent). */
  record(rel, content) {
    this.files[rel] = sha256(content);
  }

  /** update's ONLY write path. Overwrites solely when the on-disk content is
   * the version the framework last wrote (hash matches the stored manifest);
   * anything else — user-edited, or never manifest-owned — gets <rel>.new. */
  sync(rel, content, mode) {
    const abs = this._abs(rel);
    const newHash = sha256(content);
    if (!fs.existsSync(abs)) {              // new framework file
      this._put(rel, content, mode);
      this.files[rel] = newHash;
      return "written";
    }
    const curHash = sha256(fs.readFileSync(abs));
    if (curHash === newHash) {              // already current
      this.files[rel] = newHash;
      return "current";
    }
    if (this.old?.files?.[rel] === curHash) { // user-unmodified → safe to refresh
      this._put(rel, content, mode);
      this.files[rel] = newHash;
      return "written";
    }
    // user-modified (or unowned): never clobber — park the new version beside it.
    this._put(`${rel}.new`, content, mode);
    this.conflicts.push(rel);
    if (this.old?.files?.[rel]) this.files[rel] = this.old.files[rel];
    return "conflict";
  }

  /** Sync a whole package directory into the repo (exec bits preserved). */
  syncDir(srcAbs, relDst) {
    for (const rel of walkFiles(srcAbs)) {
      const src = path.join(srcAbs, ...rel.split("/"));
      this.sync(`${relDst}/${rel}`, fs.readFileSync(src), fs.statSync(src).mode & 0o777);
    }
  }

  /** init's counterpart of syncDir: unconditional copy, recorded. */
  forceDir(srcAbs, relDst) {
    for (const rel of walkFiles(srcAbs)) {
      const src = path.join(srcAbs, ...rel.split("/"));
      this.force(`${relDst}/${rel}`, fs.readFileSync(src), fs.statSync(src).mode & 0o777);
    }
  }

  save(version) {
    const sorted = Object.fromEntries(Object.entries(this.files).sort(([a], [b]) => a.localeCompare(b)));
    this._put(MANIFEST_REL, JSON.stringify({ version, files: sorted }, null, 2) + "\n");
  }
}

/** Build junk that must never be copied into an install or recorded in the
 * manifest: python regenerates .pyc with a fresh source-mtime header, so a
 * copied one is guaranteed to read as "locally modified" on the next doctor —
 * exactly the false alarm that broke CI (a __pycache__ created in the package
 * tree by a prior test run rode forceDir into the manifest). */
const JUNK_DIRS = new Set(["__pycache__"]);
const JUNK_FILES = /\.(pyc|pyo)$|^\.DS_Store$/;

/** Repo-relative file listing, always forward-slash (manifest keys are portable). */
export function walkFiles(dir, prefix = "") {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = prefix ? `${prefix}/${e.name}` : e.name;
    if (e.isDirectory()) {
      if (!JUNK_DIRS.has(e.name)) out.push(...walkFiles(path.join(dir, e.name), rel));
    } else if (!JUNK_FILES.test(e.name)) {
      out.push(rel);
    }
  }
  return out;
}

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
    this.owned = [];               // rel paths this repo has DECLARED it owns
    // A repo may deliberately fork a framework file — a monorepo profile the stock
    // one will never match, a hook with local rules. Without a way to say so, every
    // update parks another `.new` on it forever: reviewed, deleted, and back within
    // the hour. Worse, the parked file is where upstream improvements land, so a fork
    // silently stops receiving them. `owned` in the manifest ends the chore and keeps
    // the signal: update reports, once, that upstream moved under a file you own.
    const decl = this.old?.owned;
    // Validated, because a reviewer got a bare string character-split into a bogus
    // array AND written back over the user's hand-edit. A malformed declaration is
    // reported and IGNORED; it is never silently rewritten.
    this.ownedInvalid = null;
    this.ownedPartial = null;
    if (decl === undefined || decl === null) {
      this.ownedDecl = new Set();
    } else if (Array.isArray(decl) && decl.every((x) => typeof x === "string")) {
      this.ownedDecl = new Set(decl.filter((x) => x && !x.includes("..")));
      const dropped = decl.filter((x) => !x || x.includes(".."));
      if (dropped.length) this.ownedPartial = `${dropped.length} owned entr${dropped.length === 1 ? "y" : "ies"} ignored (empty, or containing "..")`;
    } else {
      this.ownedDecl = new Set();
      this.ownedInvalid = `\`owned\` must be a list of path strings, got ${Array.isArray(decl) ? "a list with non-strings" : typeof decl}`;
    }
    this.ownedMatched = new Set();
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
    // Record the match FIRST. `ownedMatched` decides whether update warns "this owned
    // path matched no framework file", and it used to be set only inside the owned
    // branch — which sits below the two fast paths. So every owned path that was
    // currently in sync got told it matched nothing, in the most ordinary steady state
    // there is, and right after the hand-merge the feature exists for.
    if (this.ownedDecl.has(rel)) this.ownedMatched.add(rel);
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
    // Declared as owned by this repo: do not clobber AND do not park. Report that
    // upstream moved — the signal without the file to delete every time.
    //
    // This sits ABOVE the refresh branch on purpose. A reviewer found it below, where
    // the guarantee silently lapsed the moment a fork happened to be byte-identical to
    // the package — which is exactly what happens right after someone merges upstream
    // by hand. The declaration must hold whether or not the file has diverged yet.
    if (this.ownedDecl.has(rel)) {
      // Reached only when the file HAS diverged — the equality case returned above —
      // so this is unconditionally "upstream moved under a file you own".
      this.owned.push(rel);
      // The recorded hash is the FRAMEWORK's last-known one, never the user's bytes.
      // That is what keeps the guard from later mistaking a fork for framework content.
      this.files[rel] = this.old?.files?.[rel] ?? newHash;
      return "owned";
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
    // carry the ownership declaration forward — it is the repo's, not the run's
    const sorted = Object.fromEntries(Object.entries(this.files).sort(([a], [b]) => a.localeCompare(b)));
    this._put(MANIFEST_REL, JSON.stringify({ // BOTH flags. Splitting the message in round 2 moved the partial case off the
    // flag this guard reads, so a list with one bad entry got rewritten and the
    // user's hand-written lines vanished — silently, and only once, because the
    // warning cannot fire again after the entry is gone. A `..` is far more likely
    // to be a typo for a path they meant to own than junk to tidy away.
    owned: (this.ownedInvalid || this.ownedPartial) ? (this.old?.owned ?? []) : [...this.ownedDecl], version, files: sorted }, null, 2) + "\n");
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

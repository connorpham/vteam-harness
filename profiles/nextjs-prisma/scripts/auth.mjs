// Pluggable auth strategy for evidence capture (nextjs-prisma profile default:
// Auth.js v5 credentials flow — csrf → callback/credentials → session).
//
// Swap the strategy by setting EVD_AUTH_MODULE to another .mjs exporting
// signIn(context, base, username, password) — the deepest stack coupling of the
// evidence tools lives HERE and only here.
//
// The credential field name comes from EVD_USER_FIELD (default "username").
//
// Selftest:  node auth.mjs --selftest   (a FAKE context — no browser, no server)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

export async function signIn(context, base, username, password) {

  const field = process.env.EVD_USER_FIELD ?? "username";
  const { csrfToken } = await (await context.request.get(`${base}/api/auth/csrf`)).json();
  await context.request.post(`${base}/api/auth/callback/credentials`, {
    form: { csrfToken, [field]: username, password, redirect: "false" },
  });
  const session = await (await context.request.get(`${base}/api/auth/session`)).json();
  if (!session?.user) throw new Error(`sign-in failed for ${username}`);
  return session.user;
}

export async function loadAuth() {
  if (process.env.EVD_AUTH_MODULE) {
    const mod = await import(new URL(process.env.EVD_AUTH_MODULE, `file://${process.cwd()}/`).href);
    return mod.signIn;
  }
  return signIn;
}

// ── selftest: the flow on a fake context — csrf → callback/credentials → session ──
// (VT-25: this module had no test; the deepest stack coupling deserves one)
const isMain = process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain && process.argv.includes("--selftest")) {
  const fail = (m) => { console.error(`auth selftest: FAIL — ${m}`); process.exit(1); };
  const calls = [];
  const fakeContext = (sessionUser) => ({ request: {
    get: async (url) => { calls.push(["GET", url]); return { json: async () =>
      (url.endsWith("/api/auth/csrf") ? { csrfToken: "tok-1" } : { user: sessionUser }) }; },
    post: async (url, opts) => { calls.push(["POST", url, opts.form]); return { status: () => 200 }; },
  } });
  const user = await signIn(fakeContext({ role: "ADMIN" }), "http://x", "admin", "pw");
  if (user.role !== "ADMIN") fail("the session user was not returned");
  const [csrf, post, session] = calls;
  if (csrf[1] !== "http://x/api/auth/csrf" || post[1] !== "http://x/api/auth/callback/credentials" ||
      session[1] !== "http://x/api/auth/session") fail(`wrong URL order: ${JSON.stringify(calls)}`);
  if (post[2].csrfToken !== "tok-1" || post[2].username !== "admin" || post[2].password !== "pw" ||
      post[2].redirect !== "false") fail(`credentials form wrong: ${JSON.stringify(post[2])}`);
  // EVD_USER_FIELD renames the credential field (an app that signs in by email)
  calls.length = 0;
  process.env.EVD_USER_FIELD = "email";
  await signIn(fakeContext({ role: "STAFF" }), "http://x", "s@x", "pw");
  delete process.env.EVD_USER_FIELD;
  if (!("email" in calls[1][2]) || "username" in calls[1][2]) fail("EVD_USER_FIELD not honoured");
  // mutation: no session.user → throws naming the user, never a silent anonymous run
  let threw = false;
  try { await signIn(fakeContext(null), "http://x", "ghost", "pw"); }
  catch (e) { threw = /sign-in failed for ghost/.test(e.message); }
  if (!threw) fail("a failed sign-in must throw and name the user");
  // EVD_AUTH_MODULE swaps the strategy; without it the built-in is returned
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-auth-"));
  try {
    fs.writeFileSync(path.join(tmp, "alt.mjs"), "export async function signIn() { return { role: 'ALT' }; }\n");
    process.env.EVD_AUTH_MODULE = path.join(tmp, "alt.mjs");
    const alt = await loadAuth();
    delete process.env.EVD_AUTH_MODULE;
    if ((await alt()).role !== "ALT") fail("EVD_AUTH_MODULE strategy not loaded");
    if ((await loadAuth()) !== signIn) fail("the default strategy must be the built-in signIn");
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
  console.log("auth selftest: OK (csrf → callback → session on a fake context, EVD_USER_FIELD rename, "
    + "failed sign-in throws, EVD_AUTH_MODULE swap, default strategy)");
}

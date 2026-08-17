// Pluggable auth strategy for evidence capture (nextjs-prisma profile default:
// Auth.js v5 credentials flow — csrf → callback/credentials → session).
//
// Swap the strategy by setting EVD_AUTH_MODULE to another .mjs exporting
// signIn(context, base, username, password) — the deepest stack coupling of the
// evidence tools lives HERE and only here.
//
// The credential field name comes from EVD_USER_FIELD (default "username").

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

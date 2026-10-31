import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import { safeReturn } from '../src/web/src/lib/navigation.ts';
import { publicOrigin } from '../src/web/src/lib/api/proxy-config.ts';

const require = createRequire(new URL('../src/web/package.json', import.meta.url));
const ts = require('typescript');

test('workspace switching requires same-origin POST, membership and a role-appropriate return', async () => {
  const module = { exports: {} };
  const code = ts.transpileModule(readFileSync(new URL('../src/web/src/app/api/workspace/route.ts', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const { NextResponse } = require('next/server');
  let token: string | undefined = 'v2.synthetic.signature';
  let result = { ok: true, data: { workspaces: [{ kind: 'org', id: 'demo-org', role: 'member' }] }, status: 200 };
  let reads = 0;
  runInNewContext(code, { module, exports: module.exports, URL, URLSearchParams, process: { env: {} }, require: (id: string) => ({
    'next/server': { NextResponse },
    '@/lib/api/proxy-config': { publicOrigin: (r: Request) => publicOrigin(r, {}) },
    '@/lib/auth/session': { getSessionToken: async () => token },
    '@/lib/auth/workspace': { PERSONAL: 'personal', ORG_COOKIE: 'adept_org', isOrgId: (v: string) => /^[a-z0-9-]+$/.test(v) },
    '@/lib/navigation': { safeReturn },
    '@/lib/api/client': { createApiClient: () => ({ GET: () => { reads++; } }), call: async () => result },
  }[id]) });
  const { GET, POST } = module.exports;
  const request = (to = 'demo-org', origin = 'https://adept.example.test', next = '/work/plan?scenario=fast') => new Request('https://adept.example.test/api/workspace', {
    method: 'POST', headers: { origin }, body: new URLSearchParams({ to, next }),
  });
  assert.equal(GET().status, 405);
  assert.equal((await POST(request('demo-org', 'https://attacker.test'))).status, 403);
  assert.equal(reads, 0);
  token = undefined;
  assert.match((await POST(request())).headers.get('location'), /auth\/login\?next=/);
  token = 'v2.synthetic.signature';
  const member = await POST(request());
  assert.equal(member.headers.get('location'), 'https://adept.example.test/work/plan?scenario=fast');
  assert.match(member.headers.get('set-cookie'), /adept_org=demo-org/);
  const stranger = await POST(request('other-org'));
  assert.equal(stranger.status, 303);
  assert.equal(stranger.headers.get('location'), 'https://adept.example.test/app?workspace_error=1');
  assert.equal(stranger.headers.get('set-cookie'), null);
  const malformed = await POST(request('Not An Id!'));
  assert.equal(malformed.headers.get('location'), 'https://adept.example.test/app?workspace_error=1');
  assert.equal((await POST(request('demo-org', 'https://adept.example.test', '/org/settings'))).headers.get('location'), 'https://adept.example.test/work');
  result = { ok: false, data: { workspaces: [] }, status: 503 };
  const unavailable = await POST(request());
  assert.equal(unavailable.status, 303);
  assert.equal(unavailable.headers.get('location'), 'https://adept.example.test/app?workspace_error=1');
  assert.equal(unavailable.headers.get('set-cookie'), null);
  result = { ok: false, data: { workspaces: [] }, status: 401 };
  const expired = await POST(request());
  assert.equal(expired.status, 303);
  assert.match(expired.headers.get('location'), /auth\/login\?next=%2Fwork%2Fplan/);
  const personal = await POST(request('personal', 'https://adept.example.test', 'https://attacker.test'));
  assert.equal(personal.headers.get('location'), 'https://adept.example.test/app');
  assert.match(personal.headers.get('set-cookie'), /adept_org=;/);
});

test('signup with a join code still lands on onboarding; login keeps a join deep link', async () => {
  const { loadComponent } = await import('./harness/web-components.ts');
  let target = '';
  let nextPath = '/app/onboarding';
  const load = () => loadComponent('src/features/core/auth-actions.ts', {
    'next/cache': { revalidatePath: () => {} },
    'next/navigation': { redirect: (to: string) => { target = to; } },
    '@/lib/api': {
      getApi: async () => ({ POST: () => ({ token: 'v2.synthetic.signature', account: { org_id: null }, next_path: nextPath }) }),
      call: async (data: unknown) => ({ ok: true, data }),
    },
    '@/lib/auth/session': { setSessionToken: async () => {}, clearSession: async () => {} },
    '@/lib/auth/workspace': loadComponent('src/lib/auth/workspace.ts', { 'next/headers': {} }),
    '@/lib/navigation': { safeReturn },
  });
  const { signupAction, loginAction } = load();
  const form = new FormData();
  form.set('next', '/app/join?code=SYNTHETIC');
  form.set('workspace', 'individual');
  form.set('join_code', 'SYNTHETIC');
  await signupAction({}, form);
  assert.equal(target, '/app/onboarding');
  nextPath = '/app';
  await loginAction({}, form);
  assert.equal(target, '/app/join?code=SYNTHETIC');
});

test('new organisation admins get the workspace cookie at signup; other signups do not', async () => {
  const { loadComponent } = await import('./harness/web-components.ts');
  const signup = async (orgId: string | null, nextPath: string) => {
    const set: unknown[][] = [];
    let target = '';
    const { signupAction } = loadComponent('src/features/core/auth-actions.ts', {
      'next/cache': { revalidatePath: () => {} },
      'next/headers': { cookies: async () => ({ set: (...args: unknown[]) => { set.push(args); } }) },
      'next/navigation': { redirect: (to: string) => { target = to; } },
      '@/lib/api': {
        getApi: async () => ({ POST: () => ({ token: 'v2.synthetic.signature', account: { org_id: orgId }, next_path: nextPath }) }),
        call: async (data: unknown) => ({ ok: true, data }),
      },
      '@/lib/auth/session': { setSessionToken: async () => {}, clearSession: async () => {} },
      '@/lib/auth/workspace': loadComponent('src/lib/auth/workspace.ts', { 'next/headers': {} }),
      '@/lib/navigation': { safeReturn },
    }, { process: { env: { NODE_ENV: 'production' } } });
    await signupAction({}, new FormData());
    return { set, target };
  };
  const admin = await signup('synthetic-org', '/org');
  assert.equal(admin.target, '/org');
  assert.equal(admin.set.length, 1);
  const [name, value, options] = admin.set[0] as [string, string, Record<string, unknown>];
  assert.equal(name, 'adept_org');
  assert.equal(value, 'synthetic-org');
  assert.equal(options.path, '/');
  assert.equal(options.httpOnly, true);
  assert.equal(options.sameSite, 'lax');
  assert.equal(options.secure, true);
  assert.deepEqual((await signup(null, '/app/onboarding')).set, []);
  assert.deepEqual((await signup('synthetic-org', '/app/onboarding')).set, []);
  assert.deepEqual((await signup('Not An Id!', '/org')).set, []);
  assert.deepEqual((await signup('personal', '/org')).set, []);
});

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
  assert.equal((await POST(request('other-org'))).status, 403);
  assert.equal((await POST(request('demo-org', 'https://adept.example.test', '/org/settings'))).headers.get('location'), 'https://adept.example.test/work');
  result = { ok: false, data: { workspaces: [] }, status: 503 };
  const unavailable = await POST(request());
  assert.equal(unavailable.status, 503);
  assert.equal(unavailable.headers.get('set-cookie'), null);
  const personal = await POST(request('personal', 'https://adept.example.test', 'https://attacker.test'));
  assert.equal(personal.headers.get('location'), 'https://adept.example.test/app');
  assert.match(personal.headers.get('set-cookie'), /adept_org=;/);
});

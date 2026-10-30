import { spawn } from "node:child_process";
import { resolve } from "node:path";

// Test-only launcher: no .env defaults, ambient database, provider credentials or raw auth.
const env = { ...process.env,
  APP_ENV: "development", M3_BACKEND: "csv", DATABASE_URL: "postgresql://test:test@127.0.0.1:1/unreachable",
  AUTH_RAW_USER_IDS: "false", AUTH_DEFAULT_USER: "", SESSION_SECRET: "synthetic-e2e-session-secret-32-characters",
  LLM_PROVIDER: "none", LLM_API_KEY: "", RUNPOD_API_KEY: "", GEMINI_API_KEY: "",
  LLM_FALLBACK_PROVIDER: "", LLM_FALLBACK_API_KEY: "", EMBEDDINGS_PROVIDER: "none",
  SYNC_TOKEN: "", GITHUB_DISPATCH_TOKEN: "", ADMIN_USER_IDS: "", RATE_LIMIT_ENABLED: "false",
  API_URL: "http://127.0.0.1:18091", WEB_ORIGIN: "http://127.0.0.1:13091",
  PYTHONPATH: [resolve("src/api"), resolve("src")].join(process.platform === "win32" ? ";" : ":"),
  PROXY_SHARED_SECRET: "synthetic-e2e-proxy-secret", PORT: "13091", HOSTNAME: "127.0.0.1", NEXT_TELEMETRY_DISABLED: "1",
};
const children = [];
const start = (cmd, args, cwd) => {
  const child = spawn(cmd, args, { cwd, env, stdio: "inherit", windowsHide: true });
  children.push(child);
  child.on("exit", () => { for (const other of children) if (other !== child) other.kill(); });
  return child;
};
for (const signal of ["SIGTERM", "SIGINT"]) process.on(signal, () => {
  for (const child of children) child.kill();
  process.exit(0);
});
const python = resolve(process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
start(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18091"], process.cwd());
let ready = false;
for (let n = 0; n < 100; n++) {
  try { const r = await fetch(`${env.API_URL}/api/v1/health`); if (r.ok) { ready = true; break; } } catch {}
  await new Promise((r) => setTimeout(r, 200));
}
if (!ready) { for (const child of children) child.kill(); throw new Error("Isolated API did not start"); }
start(process.execPath, ["scripts/start-standalone.mjs"], resolve("src/web"));

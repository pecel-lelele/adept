import { lstat, rm } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(app, ".next");
// Stale standalone traces can point back into a previous build, especially on Windows.
// Delete only this application's generated output, never a linked cache elsewhere.
const existing = await lstat(output).catch((error) => {
  if (error.code !== "ENOENT") throw error;
});
if (existing?.isSymbolicLink()) throw new Error("Refusing to remove a linked .next directory.");
await rm(output, { recursive: true, force: true });
const require = createRequire(import.meta.url);
const result = spawnSync(process.execPath, [require.resolve("next/dist/bin/next"), "build", "--webpack"], {
  cwd: app, env: process.env, stdio: "inherit",
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
await import("./prepare-standalone.mjs");

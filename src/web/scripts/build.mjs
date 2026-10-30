import { lstat, rm, writeFile } from "node:fs/promises";
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
const identity = spawnSync("git", ["rev-parse", "HEAD"], { cwd: app, encoding: "utf8" });
const revision = identity.status === 0 ? identity.stdout.trim() : "";
if (/^[0-9a-f]{40}$/.test(revision)) await writeFile(path.join(output, "adept-revision.txt"), revision + "\n");
const changes = spawnSync("git", ["status", "--porcelain"], { cwd: app, encoding: "utf8" });
if (changes.status === 0) await writeFile(path.join(output, "adept-dirty.txt"), changes.stdout.trim() ? "true\n" : "false\n");

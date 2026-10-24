import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

/** Preserve the native PyMuPDF runtime lookup from the pre-migration Nix launcher. */
export function nativeLibraryEnv(
  env: NodeJS.ProcessEnv,
  nixPresent = existsSync("/nix/store"),
  locate = () => execFileSync("gcc", ["-print-file-name=libstdc++.so.6"], { encoding: "utf8", timeout: 5000 }).trim(),
  exists = existsSync,
): NodeJS.ProcessEnv {
  if (!nixPresent) return { ...env };
  let library: string;
  try { library = locate(); } catch { throw new Error("Cannot locate the Nix GCC runtime required by PyMuPDF. Add gcc to .replit packages."); }
  if (!path.isAbsolute(library) || !exists(library)) throw new Error("GCC did not return a valid PyMuPDF runtime library path.");
  return { ...env, LD_LIBRARY_PATH: [path.dirname(library), env.LD_LIBRARY_PATH].filter(Boolean).join(path.delimiter) };
}

/** One private API address for the supervisor and public proxy. */
export function privateApiPort(env: NodeJS.ProcessEnv = process.env): number {
  const raw = env.API_PORT ?? "8000";
  const port = Number(raw);
  if (!/^\d+$/.test(raw) || !Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new Error("API_PORT must be an integer between 1024 and 65535.");
  }
  return port;
}

export function privateApiUrl(): string {
  return `http://127.0.0.1:${privateApiPort()}`;
}

export async function waitForApi(url: string, timeoutMs = 45000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url + "/api/v1/health", {
        signal: AbortSignal.timeout(Math.max(1, Math.min(1000, deadline - Date.now()))),
      });
      const health = await response.json() as { status?: string; database?: string };
      if (response.ok && health.status === "ok" && health.database === "ok") return;
    } catch {
      // The child may still be importing or opening its first database connection.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Private API/database did not become healthy before the startup deadline. Check DATABASE_URL.");
}

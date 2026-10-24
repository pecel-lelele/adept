import app from "./app";
import { logger } from "./lib/logger";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { nativeLibraryEnv, privateApiPort, privateApiUrl, waitForApi } from "./backend";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (!Number.isInteger(port) || port <= 0 || port > 65535 || port === privateApiPort()) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const pythonRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const venv = path.resolve(pythonRoot, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const executable = existsSync(venv) ? venv : "python";
const python = spawn(executable, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(privateApiPort())], {
  cwd: pythonRoot,
  env: { ...nativeLibraryEnv(process.env), PYTHONPATH: [path.join(pythonRoot, "src/api"), path.join(pythonRoot, "src")].join(path.delimiter), API_URL: privateApiUrl() },
  stdio: "inherit",
});
python.on("error", () => { logger.error("Cannot launch the private Python API"); process.exit(1); });
python.on("exit", code => { logger.error({ code }, "Adept backend stopped"); process.exit(code || 1); });
for (const signal of ["SIGTERM", "SIGINT"] as const) process.on(signal, () => { python.kill(signal); process.exit(0); });
try {
  await waitForApi(privateApiUrl());
} catch {
  logger.error("Private API/database startup failed; check DATABASE_URL and the preceding API error.");
  python.kill();
  process.exit(1);
}
app.listen(port, "0.0.0.0", (err?: Error) => {
  if (err) {
    logger.error({ err }, "Error listening on port");
    python.kill();
    process.exit(1);
  }

  logger.info({ port }, "Server listening");
});

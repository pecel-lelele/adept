import app from "./app";
import { logger } from "./lib/logger";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const pythonRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../python");
process.env.API_URL = "http://127.0.0.1:8000";
const python = spawn("python", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], {
  cwd: pythonRoot,
  env: { ...process.env, PYTHONPATH: path.join(pythonRoot, "src/api") + ":" + path.join(pythonRoot, "src"), API_URL: process.env.API_URL },
  stdio: "inherit",
});
python.on("exit", code => { logger.error({ code }, "Adept backend stopped"); process.exit(code ?? 1); });
for (const signal of ["SIGTERM", "SIGINT"] as const) process.on(signal, () => { python.kill(signal); process.exit(0); });
for (let attempt = 0; attempt < 100; attempt++) {
  try { const response = await fetch("http://127.0.0.1:8000/api/v1/health"); if (response.status < 500) break; } catch {}
  await new Promise(resolve => setTimeout(resolve, 100));
}
app.listen(port, (err) => {
  if (err) {
    logger.error({ err }, "Error listening on port");
    process.exit(1);
  }

  logger.info({ port }, "Server listening");
});

import { cp, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const standaloneApp = path.join(appRoot, ".next", "standalone", "src", "web");
const staticTarget = path.join(standaloneApp, ".next", "static");
const publicTarget = path.join(standaloneApp, "public");

for (const target of [staticTarget, publicTarget]) {
  const relative = path.relative(path.join(appRoot, ".next", "standalone"), target);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Standalone assets must remain inside this app's build directory.");
  }
}

await mkdir(path.dirname(staticTarget), { recursive: true });
await rm(staticTarget, { recursive: true, force: true });
await rm(publicTarget, { recursive: true, force: true });
await cp(path.join(appRoot, ".next", "static"), staticTarget, { recursive: true });
await cp(path.join(appRoot, "public"), publicTarget, { recursive: true });

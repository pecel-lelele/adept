import { cp, mkdir, rm } from "node:fs/promises";
import path from "node:path";

const appRoot = process.cwd();
const standaloneApp = path.join(appRoot, ".next", "standalone", "artifacts", "adept");
const staticTarget = path.join(standaloneApp, ".next", "static");
const publicTarget = path.join(standaloneApp, "public");

await mkdir(path.dirname(staticTarget), { recursive: true });
await rm(staticTarget, { recursive: true, force: true });
await rm(publicTarget, { recursive: true, force: true });
await cp(path.join(appRoot, ".next", "static"), staticTarget, { recursive: true });
await cp(path.join(appRoot, "public"), publicTarget, { recursive: true });

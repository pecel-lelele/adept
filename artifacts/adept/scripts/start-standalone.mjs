import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { proxyConfig } from "../src/lib/api/proxy-config.ts";

// Fail before opening a public socket, rather than quietly sharing one visitor bucket.
proxyConfig({ ...process.env, APP_ENV: "production" });
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const server = path.join(web, ".next/standalone/artifacts/adept/server.js");
process.env.NODE_ENV = "production";
await import(pathToFileURL(server).href);

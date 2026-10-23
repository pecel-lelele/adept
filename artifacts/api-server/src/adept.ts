import express from "express";

/** Preserve the imported FastAPI service; Next.js owns its original BFF routes. */
export const adept = express.Router();
adept.use("/api/v1", async (req, res) => {
  const headers = new Headers();
  for (const key of ["content-type", "accept", "authorization", "x-demo-user", "x-workspace", "x-real-ip", "x-internal-proxy-secret"]) {
    const value = req.get(key);
    if (value) headers.set(key, value);
  }
  const init: any = { method: req.method, headers, signal: AbortSignal.timeout(35000) };
  if (!["GET", "HEAD"].includes(req.method)) { init.body = req; init.duplex = "half"; }
  const upstream = await fetch("http://127.0.0.1:8000" + req.originalUrl, init);
  res.status(upstream.status);
  upstream.headers.forEach((value, key) => {
    if (!["transfer-encoding", "content-length", "content-encoding"].includes(key)) res.setHeader(key, value);
  });
  res.send(Buffer.from(await upstream.arrayBuffer()));
});

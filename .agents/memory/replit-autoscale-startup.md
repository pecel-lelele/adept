---
name: Replit Autoscale startup probes
description: Keep the HTTP listener available promptly while API/database readiness checks run.
---

Start the public HTTP server before waiting on slower API or database readiness, but keep
those dependencies supervised and fail startup if they do not become healthy.

**Why:** Replit Autoscale probes `GET /` shortly after launch and its documented probe
timeout is five seconds. A launcher that blocks opening its HTTP port on a longer
database/API check can fail promotion even when its web server would otherwise serve `/`.

**How to apply:** When a deployment runs multiple processes, launch the lightweight
HTTP listener promptly, then start and verify its dependencies. Keep failure handling
for dependency startup and ensure the supervisor still stops the sibling process.

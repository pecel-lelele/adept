---
name: Nix subprocess test isolation
description: Why mocked server lifecycle tests can fail only on Replit's Nix runtime.
---

Isolate native-library probing from server-process mocks in launcher supervision tests.
Mocking `subprocess.Popen` also affects `subprocess.run`, not just long-lived servers.

**Why:** Replit's Nix environment probes GCC for the C++ runtime at startup. Server-only
process doubles cannot satisfy that probe's communication contract, even when the same
tests pass on non-Nix CI runners.

**How to apply:** In tests focused on supervision, stub the native environment probe
separately. Test the actual library probe independently with a command-runner double.
Avoid changing production startup behavior just to accommodate a server-process mock.

Scope Python's injected GCC library path to the Python process, not to the whole
quality-gate runner or the Node server.

**Why:** The GCC runtime used by PyMuPDF can be older than the C++ ABI required by
Node's ICU libraries. A global override caused Node to fail before executing its script.

**How to apply:** Run Python-only verification with the required native path and run
Node commands with their normal environment. Keep separate child environments in
multi-process launchers; preserve any inherited library paths.

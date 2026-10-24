---
name: Next.js preview origins
description: Why Next.js development allowlists must include the actual Replit preview hostname.
---

Use the exact runtime preview hostnames in Next.js development-origin allowlists, including loopback for the screenshot browser.

**Why:** A `*.replit.dev` wildcard did not admit the nested `…pike.replit.dev` preview hostname in Next.js 16.4, producing blocked HMR requests despite otherwise working page responses.

**How to apply:** When adjusting Next.js preview settings, derive the allowlist from the runtime development-domain variables rather than assuming a single-level wildcard matches every preview domain. Do not broaden production origin protections to fix development-only restrictions.

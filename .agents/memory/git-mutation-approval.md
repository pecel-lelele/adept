---
name: Git mutation approval
description: Replit workspace guard behavior for state-changing Git commands.
---

State-changing Git commands in this Replit workspace may be blocked until they are explicitly authorized with `DANGEROUSLY_ALLOW_GIT=1`.

**Why:** The workspace Git guard is designed to protect the user's checkout and rebase state from accidental mutation.

**How to apply:** Use the authorization prefix only for a Git operation the user has requested or clearly approved. Continue to inspect status and diffs before and after potentially destructive operations.

# Replit forwarding verification — issue #55

Status on 2026-10-30: **live chain unverified**. The maintainer does not have access to
the friend's Replit workspace or deployment logs. No deployment or live spoof-resistance
test is claimed. Keep #55 open until its owner completes and records the checks below.

## Implemented boundary

`TRUSTED_PROXY_HOPS=0` ignores XFF in both modes. The web server strips incoming
`X-Real-IP` and `X-Internal-Proxy-Secret`; it does not sign a caller-selected identity.
`best-effort` keeps serving via the private API's direct-peer bucket. This can cause
anonymous visitors to share rate limits; it does not establish per-visitor isolation.
Verified signed-in sessions retain their existing account-based limits.

A positive count selects a validated suffix from the right: one selects the last XFF
entry; two selects the second-last and requires both entries to be valid IP addresses.
Too few entries or any malformed address in that suffix omits the signed identity.
Caller-controlled prefixes outside the suffix never choose a bucket. Pages/server actions,
the general API relay, CV preview and Adi use the same `clientIpHeaders` boundary.

**The count is deployment configuration, never learned from a request.** Too large a count
can select a forged prefix. A positive count is safe only if every public ingress path
enforces that same suffix and direct access bypassing the edge is impossible. These are
the trust prerequisites described in [MDN's XFF security guidance](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For#security_and_privacy_concerns).

## Owner-run evidence collection

1. Review this change and deploy it through the existing release process. Check existing
   migration/session rollout requirements separately; this change needs no new migration.
   Leave hops at zero until the chain is verified. Set `PROXY_LOG_XFF_COUNT=true` temporarily
   on the web process. The only diagnostic is `proxy_xff_entry_count=<integer>`. It includes
   no header contents, addresses, tokens, cookies, user IDs or request URLs.
2. From one controlled client, send each probe below separately. Observe only the entry
   counts in deployment logs during its time window. `/api/healthz` requires no account,
   invokes no model and does not consume an authentication rate bucket. Repeat through
   the published Replit hostname and each configured custom domain. Use the exact deployed
   origin in place of `https://YOUR-DEPLOYED-ORIGIN`.

   ```powershell
   curl.exe -s -o NUL https://YOUR-DEPLOYED-ORIGIN/api/healthz
   curl.exe -s -o NUL -H "X-Forwarded-For: 192.0.2.10" https://YOUR-DEPLOYED-ORIGIN/api/healthz
   curl.exe -s -o NUL -H "X-Forwarded-For: 192.0.2.10, 198.51.100.20" https://YOUR-DEPLOYED-ORIGIN/api/healthz
   ```

3. Record baseline and forged-header counts, deployment revision, date, ingress domains and
   platform forwarding configuration/guarantee. Do **not** record IP values. For a single
   appending edge, baseline 1 and injected counts 2/3 are consistent with the synthetic
   one-hop regression. A constant count may mean overwrite or pass-through: counts alone
   do not distinguish them or prove the selected address is unspoofable. Likewise a baseline
   of two does not establish two trusted hops; one edge can write several entries.
4. Verify suffix integrity and bucket behavior in a controlled deployment using the same
   ingress configuration, with owner authorization. Use a low anonymous test limit and
   synthetic GET requests, no passwords/uploads/models: rotating caller XFF values must
   exhaust the **same** bucket (including forged multi-entry prefixes, IPv6 and malformed
   prefixes). A second independent client must retain a separate allowance. Test missing
   and malformed suffixes as direct-peer fallback. Do not exhaust production users' buckets.
   Confirm the API is private and test every alternate ingress path. If these prerequisites
   cannot be established, retain zero hops; do not enable trust from counts alone.
5. Only after verification, configure the proven count and `PROXY_CLIENT_IP_MODE=trusted`
   on the deployment. Disable `PROXY_LOG_XFF_COUNT` again. Add a regression with the observed
   **synthetic** chain shape and record the evidence/outcome here and in the decisions log.
   The current append-only-edge tests are simulations, not captured Replit evidence.

## Local checks

`node --experimental-strip-types --test tests/web-proxy.test.ts` exercises real loopback
HTTP relays, one- and two-hop append-only edges, prefix rotation without a new rate bucket,
zero-hop spoof rejection, malformed/short chains, and opt-in count-only logging. It does
not establish how Replit rewrites headers in the friend's deployment.

On 2026-10-30, after integrating latest main, the isolated full quality gate passed (1317 pytest tests and 54 subtests,
32 environment/opt-in skips), together with all 74 web regressions and the production
Next.js build. This includes attribution and generated-contract checks. Remote CI and
Greptile were not run. No live Replit evidence is implied by these local results.

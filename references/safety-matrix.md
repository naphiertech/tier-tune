# Safety Matrix & Change Classification

This document governs the decision boundary between automatic modifications (Class A) and human-approval-required recommendations (Class B), cache safety policies, and cross-provider trade-off evaluations.

---

## 1. Change Classification Matrix

Every proposed optimization must be assigned to either **Class A** or **Class B**.

| Category | Optimization Action | Class | Prerequisites & Safety Gate | Verification Method |
|---|---|---|---|---|
| **Supabase Query** | Narrowing `select('*')` to specific columns | **Class A** | Code analysis proves complete list of consumed fields across all callers. | Project build, typecheck, and component tests pass. |
| **Supabase Query** | Replacing row download with `{ count: 'exact', head: true }` | **Class A** | Caller only uses `.length` or count; no row data inspected. | Unit / integration tests pass. |
| **Supabase Storage** | Adding `cacheControl` to file upload calls | **Class A** | File is served publicly or has hashed/versioned URL; preserves intended freshness. | Verification of upload options. |
| **Supabase Realtime** | Adding missing `unsubscribe()` / `removeChannel()` in teardown | **Class A** | Component already creates a channel; teardown was omitted. | Component lifecycle tests. |
| **Vercel Middleware** | Narrowing `matcher` to exclude static assets (`_next/static`, images) | **Class A** | Middleware only contains auth/routing logic intended for pages/APIs. | Smoke test static asset delivery and auth routes. |
| **Vercel Compute** | Hoisting client/SDK initialization outside handler function | **Class A** | Client instance is stateless across requests or pool-managed. | Function invocation test. |
| **Vercel Image** | Adding `sizes` attribute to responsive `<Image>` components | **Class A** | Layout dimensions are known from CSS/markup. | Visual/build check. |
| **Vercel Compute** | Parallelizing independent sequential awaits via `Promise.all` | **Class A** | Requests are fully independent and have identical auth scope. | Unit / integration tests pass. |
| **Supabase Realtime** | Throttling Presence/Broadcast updates (>=1000ms debounce) | **Class A** | High-frequency mouse/keystroke events identified; UX preserved. | Manual / component test. |
| **Caching (Static)** | Long-term immutable caching for static versioned/hashed assets | **Class A** | Assets are immutable and content-hashed; zero freshness impact. | Verification of headers / config. |
| **Caching (Freshness)** | Materially adding/changing `s-maxage`, `stale-while-revalidate`, ISR intervals, CDN cache TTL, or browser cache TTL affecting application data freshness | **Class B (Default)** | Materially alters data freshness visible to end users. May be **Class A** only when existing project clearly establishes intended freshness semantics and fix merely restores/propagates that existing behavior. | Propose in report (or verify existing freshness contract). |
| **Sensitive Data Cache** | Request/query deduplication for sensitive authenticated data | **Class A** | Semantics stay identical; eliminates duplicate calls during render/view lifecycle without persistent stale data. | Verify component data flow and query keys. |
| **Sensitive Data Cache** | Persistent browser HTTP caching on sensitive authenticated data | **Class B** | Applies to billing, account details, security settings, private dashboards, tokens/session data, and user-specific sensitive responses. Class B unless clearly defined by existing application policy. Sensitive endpoints should preserve `no-store`. | Propose in report with security review. |
| **Image Preprocessing** | Correcting config/implementation of existing image optimization pipeline | **Class A** | Image pipeline already present in project; fix resolves obvious bug without altering intended output. | Verification of build and image output. |
| **Image Preprocessing** | Introducing new client-side or server-side image compression, resizing, format conversion, or preprocessing pipeline | **Class B** | Alters upload behavior, processing pipeline, and potentially image quality. Class B by default. | Propose in report with tradeoffs. |
| **Image Feature** | Supabase Storage Image Transformations (`/render/image/`) | **PROHIBITED** | Paid-only feature on Supabase. Never recommend or implement for Free plan. | Reject paid feature. |
| **Architecture** | Migrating logic from Server to Client or Client to Server | **Class B** | Must NOT be auto-fixed. Requires user architecture review. | Propose in report. |
| **Rendering** | Changing SSR to SSG / Prerendered | **Class B** | Affects data freshness and build pipeline. | Propose in report. |
| **Database DDL** | Adding or removing database indexes | **Class B** | Indexes consume disk storage. Requires query proof and user approval. | Propose in report. |
| **Database Retention**| Establishing table TTL / retention policies or purge jobs | **Class B** | Potential data lifecycle impact. Requires explicit approval. | Propose in report. |
| **Database Schema** | Modifying tables, constraints, RPC functions, or columns | **Class B** | Risk of schema breakage. Never run auto-DDL. | Propose in report. |
| **Realtime vs Poll** | Converting Realtime to Polling or Polling to Realtime | **Class B** | Alters fundamental UX/latency and network architecture. | Propose in report. |
| **Auth / Security** | Modifying RLS policies, Auth gates, or session tokens | **Class B** | Extreme security sensitivity. Never touch without explicit prompt. | Propose in report. |
| **Data Cleanup** | Deleting database rows, dropping tables, purging Storage files | **Class B** | Destructive operation. Never automate data deletion. | Propose in report. |

---

## 2. Absolute Prohibitions (Hard Red Lines)

The skill must **NEVER** under any circumstance:
1. **Break features** or alter application functionality to achieve lower resource usage.
2. **Weaken authentication or authorization** checks.
3. **Weaken Row Level Security (RLS)** or disable RLS on Supabase tables.
4. **Expose Supabase `service_role` keys** or private environment variables to client browsers.
5. **Move server-only logic** containing secrets to the client.
6. **Delete user data** or drop database tables automatically.
7. **Delete Supabase Storage objects** or purge buckets automatically.
8. **Recommend paid-tier features** (e.g. Supabase Storage Image Transformations, Vercel Pro features, paid add-ons) for free-tier users.
9. **Recommend migrating to alternative hosting or database providers** (e.g. Netlify, Cloudflare, Firebase, Railway, Render, Neon, AWS, Azure, GCP, Fly.io).
10. **Touch or optimize PHP projects.** PHP is **EXPLICITLY OUT OF SCOPE**. If the primary application is PHP, halt immediately with an out-of-scope notice. In monorepos containing mixed languages, strictly refuse to touch, optimize, or migrate the PHP portions.
11. **Install community runtimes** (such as `vercel-php`).
12. **Hardcode temporary quota numbers** as permanent factual constraints.
13. **Claim unverified or fabricated numeric resource savings.**
14. **Treat every dynamic page as a defect** to be converted to static.
15. **Treat every serverless route as an unnecessary proxy.**
16. **Treat every Realtime channel as resource waste.**
17. **Silently apply Class B architectural changes.**
18. **Optimize one provider by blindly transferring excessive burden to the other.**
19. **Publicly cache private or user-authenticated data.**

---

## 3. Cache Safety Protocol

Caching must be strictly data-aware. Shared Edge/CDN caching of sensitive responses is a critical security vulnerability.

### 3.1 Pre-Caching Security Checklist
Before applying any public or shared Edge cache header (`s-maxage`, `public`, or framework ISR):
- [ ] Does this endpoint check an `Authorization` header, session cookie, or bearer token? *(If YES → NEVER publicly cache).*
- [ ] Does the response contain user-specific profile data, billing data, or private user IDs? *(If YES → NEVER publicly cache).*
- [ ] Does the response differ depending on who makes the request? *(If YES → NEVER publicly cache).*
- [ ] Does the endpoint perform database mutations (POST/PUT/DELETE/PATCH)? *(If YES → NEVER cache).*
- [ ] Is the data strictly identical for 100% of anonymous visitors? *(Only if YES → Public caching permitted).*

### 3.2 Authenticated & Sensitive Data Cache Policy
Do not automatically add browser HTTP caching to sensitive authenticated data.

For:
- Billing
- Account details
- Security settings
- Private dashboards
- Tokens and session data
- User-specific sensitive responses

The non-negotiable caching rules are:
- **Shared / Public CDN Caching:** Strictly PROHIBITED automatically. Never apply `s-maxage`, `public`, or shared Edge/ISR caching to authenticated or user-specific endpoints.
- **Request / Query Deduplication:** **Class A** when semantics stay identical (e.g. React `cache()`, TanStack Query / SWR in-flight query deduplication, component prop hoisting). This eliminates redundant network round-trips within the same render pass or view lifecycle without persistent stale data or cross-user privacy risks.
- **Persistent Browser HTTP Caching:** **Class B** unless existing application policy clearly defines it. Do NOT automatically inject `Cache-Control: private, max-age=...` into sensitive authenticated routes.
- **Preserve `no-store`:** Sensitive endpoints should preserve `Cache-Control: no-store, no-cache, must-revalidate` when currently intended.

---

## 4. Cross-Provider Consequence Evaluator

Never optimize Vercel and Supabase in isolation. Always trace the complete request graph:

```
[Browser]
   │
   ├── (Direct Egress) ──────────────► [Supabase (DB/Storage/Realtime)]
   │
   └── (Edge Request / Data Transfer) ─► [Vercel Edge CDN]
                                               │
                                      (Function Invocation)
                                               ▼
                                      [Vercel Serverless Function]
                                               │
                                      (Fast Origin Transfer)
                                               ▼
                                      [Supabase PostgREST / DB]
```

### 4.1 Evidence-Based Proxy Analysis Protocol

Never remove or retain a Vercel ↔ Supabase proxy based solely on the assumption that proxies are good or bad.

For every Vercel ↔ Supabase proxy, systematically determine whether it provides any of the following server responsibilities:
- **Effective caching:** Edge CDN caching (`s-maxage`) that shields Supabase from thousands of repeated queries. (Note: For external origin proxies, new Vercel projects can respect upstream `Cache-Control` headers by default, while existing projects may have different configuration/opt-in behavior. Inspect actual project configuration rather than assuming manual CDN-Cache-Control configuration is always required).
- **Authentication / authorization:** Verifying server sessions, user permissions, or signing tokens before querying.
- **Secret protection:** Guarding `service_role` keys, third-party API secrets, or private environment variables.
- **Transformation:** Filtering, shaping, or projecting database data before sending it to the client.
- **Aggregation:** Combining results from multiple Supabase tables or external services into a unified payload.
- **Validation:** Enforcing business schema validation, sanitization, or input invariants before database mutations.
- **Rate limiting:** Throttling abusive requests before they reach the database origin.
- **Request coalescing:** Merging concurrent identical incoming requests to avoid thundering herds against Postgres.
- **Another meaningful server responsibility:** Logging, compliance auditing, or custom webhook dispatching.

**Decision Rules:**
1. **If the proxy provides one or more of these responsibilities:**
   - Calculate and describe why retaining it may lower total usage (e.g., Edge caching saves 95%+ of Supabase queries, or server aggregation avoids multiple client network round-trips).
   - Retain the proxy and optimize its internal execution (e.g. hoist client initialization, trim return payloads, tune memory allocation).
2. **If the proxy is only a pass-through (zero server responsibilities):**
   - Evaluate direct client access.
   - Check security: confirm client uses public `anon` key and Row Level Security (RLS) is active and verified.
   - Check Supabase load impact: ensure direct client traffic will not exhaust Postgres connection slots or pool limits.
   - Check Vercel transfer and function costs eliminated.
   - Check caching behavior: inspect actual cache behavior/config and verify that removing the proxy does not sacrifice an active, effective cache.
   - If direct access is superior, formulate the removal as a **Class B** architectural recommendation.

### 4.2 Cross-Provider Trade-off Matrix

| Optimization Idea | Impact on Vercel | Impact on Supabase | Net Verdict |
|---|---|---|---|
| **Bypass Vercel Function proxy to call Supabase directly from browser** | Lowers Vercel Function Invocations and Fast Origin Transfer. | Increases Supabase PostgREST requests directly; loses Edge CDN caching if previously cached. | **Evaluate with evidence (Class B):** Check security (RLS), Supabase load, Vercel transfer/function cost, and caching behavior. Safe only if proxy is purely a pass-through with no server responsibilities. Retain if proxy provides caching, auth, secrets, or transformation. |
| **Proxy Supabase Storage binary files through a Vercel Function** | High waste: increases Vercel Function execution duration, memory, and Fast Data Transfer. | Increases Supabase Storage egress to Vercel origin. | **REJECT:** Serve public Storage files directly from Supabase CDN with proper browser `cacheControl`. |
| **Add Vercel Edge CDN cache (`s-maxage`) to a public data API route** | Shields Vercel compute: subsequent hits served instantly from Edge cache with 0 Function invocations. | Shields Supabase: prevents repetitive database queries for public data. | **RECOMMENDED (WIN-WIN, Class B by default):** Substantially reduces resource consumption on BOTH providers. Must be proposed as Class B unless project already establishes intended freshness semantics. |
| **Convert Realtime channel to 2-second client polling via Vercel Function** | Drastically inflates Vercel Function invocations and Edge requests. | Spams Supabase PostgREST with repetitive polling queries. | **REJECT:** Destroys quotas on both platforms; degrading user experience. |

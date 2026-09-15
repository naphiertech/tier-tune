---
name: tier-tune
description: Use when a project deployed on Vercel or using Supabase needs resource consumption, egress, requests, functions, database queries, storage, Realtime, images, or free-plan usage reduced without changing intended application behavior.
---

# Tier-Tune: Optimizing Vercel & Supabase Free Tier

## Overview

The core objective of this skill is:
**"Reduce unnecessary Vercel and Supabase resource consumption without changing the application's intended behavior, security model, data correctness, or user-visible functionality. Eliminate waste before moving work between services."**

This skill audits finished or near-finished web applications targeting Vercel and Supabase free/hobby plans, identifies architectural resource leaks, safely executes high-confidence optimizations, and reports architecture-level recommendations for human approval.

---

## Supported Scope & Hard Boundaries

### In-Scope
- **Hosting / Platform:** Vercel (Edge, Functions, ISR, Static, Images, Middleware).
- **Backend / Database:** Supabase (Postgres, PostgREST, Storage, Realtime, Edge Functions, Auth).
- **Runtimes & Frameworks:** Any Vercel-compatible stack (Next.js, Vite/React, CRA, Vue, Nuxt, Svelte, SvelteKit, Astro, Remix, React Router, Angular, Solid, SolidStart, static HTML/CSS/JS, Node.js, Bun, Python, Go, Ruby, Rust, Wasm, Edge Runtime).

### Out-of-Scope (Strict Refusal)
- **Other Providers:** Netlify, Cloudflare, Firebase, Railway, Render, Neon, AWS, Azure, GCP, Fly.io. Do not add rules for these.
- **PHP Projects:** PHP is **EXPLICITLY OUT OF SCOPE**. If the primary application is detected as PHP:
  1. Do not apply optimizations.
  2. Explain that PHP is outside this skill's supported scope.
  3. Do not migrate PHP to another runtime.
  4. Do not install `vercel-php`.
  5. Halt immediately.
  *(In monorepos containing mixed codebases, strictly refuse to touch, optimize, or migrate any PHP subdirectories).*
- **Paid Tier Features:** NEVER recommend upgrading to Pro, purchasing add-ons, or using paid-tier features (such as Supabase Storage Image Transformations) for free-tier users.

---

## The 6-Stage Execution Flow

```
SCAN ────► TRACE ────► PRIORITIZE ────► OPTIMIZE ────► VERIFY ────► REPORT
```

### 1. SCAN: Project Fingerprint
Before modifying any files, inspect repository configuration:
- Inspect manifests: `package.json`, `pnpm-lock.yaml`, `bun.lockb`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`.
- Detect config: `vercel.json`, `next.config.*`, `vite.config.*`, `nuxt.config.*`, `svelte.config.*`, `astro.config.*`, `angular.json`, `app.config.*`.
- Detect Supabase structure: `supabase/`, `supabase/config.toml`, SQL migrations, environment examples. Note any wrangler files strictly as incidental evidence, never as optimization targets.
- Identify framework, language, rendering strategy (SSG, SSR, ISR, SPA), and server runtime.
- Detect Vercel config (middleware, API routes, functions memory/duration, images).
- Detect Supabase usage (PostgREST queries, direct SQL/ORMs, Storage calls, Realtime channels/presence, Auth listeners, Edge Functions). Do not assume finding `@supabase/supabase-js` means all features are used.
- Check for PHP files → If PHP is the primary application, abort immediately with an out-of-scope notice.
- Record the **Project Fingerprint** (see [report-format.md](references/report-format.md)).

### 2. TRACE: Cross-Provider Request & Waste Tracing
Trace data and request lifecycles from Browser ↔ Vercel Edge ↔ Vercel Functions ↔ Supabase:
- **Request Waste:** Duplicate identical queries, hydration double-fetches, unthrottled polling loops, requests on every render, waterfall requests that can safely run in parallel. *(Do not merge requests that have different authorization or freshness semantics).*
- **Database Egress:** Unfiltered `select('*')`, unbounded list queries missing pagination, downloading full rows to check `.length`, unused mutation returns (`Prefer: return=representation` vs `return=minimal`).
- **Storage Egress:** Missing browser `cacheControl`, repeated un-cached downloads, relaying large public storage files through Vercel Functions.
- **Compute & Function Duration:** Un-hoisted database connections, expensive in-handler parsing, sequential external waterfalls, un-scoped middleware matchers, function memory over-allocation.
- **Image Optimization:** Unbounded responsive sizes causing variant explosions, missing `sizes` attributes, raw uncompressed assets in `public/`.
- **Realtime Traffic:** Uncleaned WebSocket channels on component unmount, overly broad schema listeners, unthrottled Presence/Broadcast updates.
- **Cross-Provider Proxy Analysis:** For every Vercel ↔ Supabase proxy, evaluate evidence: determine whether it provides effective caching, authentication/authorization, secret protection, transformation, aggregation, validation, rate limiting, request coalescing, or another server responsibility.
- **Cache Safety Audit:** Check that sensitive/authenticated endpoints (billing, account details, security settings, private dashboards, tokens/sessions) are NEVER marked with shared `s-maxage` or public CDN cache headers. Use query/request deduplication (Class A) rather than introducing persistent browser caching by default (Class B), and preserve `no-store` when intended.

### 3. PRIORITIZE: Severity & Safety Classification
Rank findings by impact: **HIGH**, **MEDIUM**, or **LOW** based on request frequency, payload size, CPU cost, and traffic multiplication.

Assign each proposed change to its safety class (see [safety-matrix.md](references/safety-matrix.md)):
- **Class A (Safe / Auto-Fixable):** High confidence, zero behavioral change, security preserved, verifiable by tests (e.g. consumer-verified column narrowing, adding upload cache headers for immutable/versioned files, adding channel unmount cleanup, middleware matcher static exclusion, hoisting function client init, independent waterfall parallelization, presence throttling, request/query deduplication, correcting config of an existing image optimization pipeline without changing intended output).
- **Class B (Architectural / Approval Required):** Materially adding/changing `s-maxage`, `stale-while-revalidate`, ISR/revalidation intervals, CDN cache TTL, or browser cache TTL affecting application data freshness (Class A only if existing project established freshness semantics); introducing new client-side/server-side image compression, resizing, format conversion, or preprocessing pipelines; adding persistent browser HTTP caching on sensitive authenticated data; changing SSR to SSG; converting Realtime to Polling; introducing database indexes; modifying schema/RLS; or touching Auth. **NEVER automatically implement Class B changes.**

### 4. OPTIMIZE: Surgical Execution
- Apply only **Class A** changes directly to code.
- Follow surrounding code style and conventions.
- Do not perform unrelated refactoring.
- Keep diffs focused strictly on resource reduction.
- For **Class B** items, formulate concrete proposals with tradeoffs for the final report.

### 5. VERIFY: Real Verification
- Execute the project's actual verification commands using the detected package manager:
  `pnpm run typecheck` / `npm test` / `bun run build`.
- Never claim an optimization is verified if a command was not executed or failed.
- Do not fabricate numeric savings. If measured, report before/after numbers; otherwise, report evidence-based directional impact (**High**, **Medium**, **Low Expected Impact**).

### 6. REPORT: Standardized Final Report
- Output the complete, structured report according to the standard template in [report-format.md](references/report-format.md).

---

## Rationalization Table: Stopping Shortcuts

| Rationalization / Shortcut | Reality & Skill Counter |
|---|---|
| *"Disable Next.js Image Optimization (`unoptimized: true`) to save transformation credits."* | **REJECT:** Disabling optimization forces browsers to download raw multi-megabyte images, heavily increasing Vercel Fast Data Transfer and Supabase Storage egress. Constrain variant sizes with `sizes="..."` instead. |
| *"Use Supabase Storage Image Transformations (`/render/image/`) to resize avatars."* | **REJECT:** Storage Image Transformations are a **PAID-ONLY** feature. Free-tier projects can propose client-side downscaling before upload or storing pre-rendered variants as a Class B proposal (or correct an existing image pipeline as Class A). |
| *"Introduce a new client-side or server-side image compression/resizing pipeline as a Class A auto-fix."* | **REJECT AS AUTO-FIX:** Introducing a new image compression, resizing, format conversion, or preprocessing pipeline changes upload behavior and potentially image quality. Classify as Class B (Approval Required) by default. (Only correcting an existing pipeline's config without altering intended output is Class A). |
| *"Bypass the Vercel API proxy and call Supabase directly using `SUPABASE_SERVICE_ROLE_KEY` in the browser."* | **CRITICAL SECURITY VIOLATION:** Leaking the service role key bypasses Row Level Security entirely and grants full database control to any user. Never expose server secrets to client. |
| *"Blindly remove (or blindly retain) every Vercel ↔ Supabase serverless proxy."* | **EVALUATE WITH EVIDENCE:** Determine whether the proxy provides effective caching, auth, secret protection, transformation, aggregation, validation, rate limiting, request coalescing, or another server responsibility. Never remove or retain based on assumptions. |
| *"Add `s-maxage=3600` to the user billing/profile endpoint to eliminate function invocations."* | **CRITICAL PRIVACY VIOLATION:** Public CDN edge caching on authenticated routes serves the first user's private data to subsequent visitors. Never publicly cache user-specific data. Auto-optimize via query deduplication (Class A); persistent browser caching is Class B. |
| *"Add database indexes on all queried columns to make queries run faster."* | **REJECT AS AUTO-FIX:** Postgres disk storage is strictly bounded on the free tier. Indexes consume physical disk space and degrade write performance. Classify as Class B (Approval Required). |
| *"Replace `select('*')` with `select('id')` because line 10 only uses `.id`."* | **DANGEROUS:** Line 40 or a child component might consume `.title` and `.author`. You MUST trace all consumers before narrowing fields. |
| *"Convert this SSR app to a purely static site (SSG) automatically."* | **ARCHITECTURAL CHANGE:** Breaks real-time user auth and personalization. Must be proposed as Class B for human review. |
| *"Replace Realtime subscriptions with 2-second polling to save WebSocket connections."* | **COUNTER-PRODUCTIVE:** Spams Vercel Functions and Supabase PostgREST with 30 requests/minute, rapidly breaching request quotas. |
| *"Delete old log tables or storage objects to free up database and storage space."* | **PROHIBITED:** Never automatically delete data. Present data cleanup and retention policies for human approval. |
| *"The project uses PHP on Vercel; install `vercel-php` to optimize it."* | **STRICT PROHIBITION:** PHP is explicitly out of scope. Halt immediately and report exclusion. |

---

## Red Flags: STOP and Re-Evaluate

If you find yourself doing any of the following, **STOP IMMEDIATELY**:
- 🚩 Touching a file in a PHP project.
- 🚩 Recommending a paid plan or paid feature.
- 🚩 Adding `s-maxage` or public cache headers to an authenticated endpoint.
- 🚩 Automatically adding persistent browser HTTP caching to sensitive authenticated data.
- 🚩 Automatically introducing a new image compression/resizing pipeline without Class B approval.
- 🚩 Materially altering cache TTLs or data freshness without existing project policy.
- 🚩 Removing or retaining a proxy based on assumptions rather than evidence.
- 🚩 Narrowing database fields without inspecting child components and caller data flow.
- 🚩 Moving private environment variables or `service_role` keys into client code.
- 🚩 Automatically executing `DROP TABLE`, `DELETE FROM`, or Storage object deletions.
- 🚩 Silently converting SSR routes to static routes without user consent.
- 🚩 Inventing percentage or dollar savings numbers without before/after benchmarks.

---

## Detailed References

Refer to specialized documentation for in-depth rules:
- **Vercel Platform Rules:** [references/vercel.md](references/vercel.md)
- **Supabase Platform Rules:** [references/supabase.md](references/supabase.md)
- **Framework Adapters:** [references/frameworks.md](references/frameworks.md)
- **Safety Matrix & Classifications:** [references/safety-matrix.md](references/safety-matrix.md)
- **Report Template & Specifications:** [references/report-format.md](references/report-format.md)
- **Test Scenarios & Edge Cases:** [tests/scenarios.md](tests/scenarios.md)

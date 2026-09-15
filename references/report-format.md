# Standard Report Format: tier-tune

This specification defines the mandatory report structure produced upon completing the audit and optimization workflow. Every execution must generate this structured report.

---

## Final Report Template

```markdown
# Tier-Tune Optimization Report

## 1. Project Fingerprint
- **Framework:** [e.g. Next.js 14.2 (App Router) | Vite React 18 | Nuxt 3.10 | Astro 4.5 | SvelteKit 2.0 | Generic Express/Node | Static]
- **Language & Runtime:** [e.g. TypeScript 5.4 / Node.js 20 | Go 1.22 | Python 3.11]
- **Package & Build System:** [e.g. pnpm 9.1 | npm 10.5 | bun 1.1 | yarn 4.1]
- **Vercel Footprint:** [e.g. Edge Middleware, Serverless Functions (/api/*), Image Optimization, ISR]
- **Supabase Footprint:** [e.g. @supabase/ssr, Database (PostgREST), Storage (avatars bucket), Realtime (chat channel), Auth]
- **Rendering Strategy:** [e.g. Hybrid SSR + Static Routes | Pure Static SPA | Full SSR]
- **Data & Network Libraries:** [e.g. TanStack Query v5, SWR, Axios, Native Fetch]

---

## 2. Resource Findings

### Finding [ID]: [Short Descriptive Title]
- **Provider:** [Vercel | Supabase | Cross-Provider]
- **Resource Affected:** [e.g. Supabase Database Egress | Vercel Function Invocations | Vercel Fast Data Transfer | Supabase Storage Egress | Realtime Messages]
- **Severity:** [HIGH | MEDIUM | LOW]
- **Confidence:** [HIGH | MEDIUM | LOW]
- **Classification:** [Class A (Auto-Fixable) | Class B (Approval Required)]
- **Evidence:** `[File path and line numbers with matching code snippet]`
- **Root Cause:** [Clear explanation of why this code pattern causes unnecessary resource consumption]
- **Proposed Optimization:** [Specific technical remedy]
- **Behavior / Security Risk Analysis:** [Verification that functionality, data correctness, and security boundaries remain intact]

---

## 3. Auto-Applied Optimizations (Class A)

| File Changed | Line(s) | Resource Optimized | Rationale | Verification Status |
|---|---|---|---|---|
| `src/app/posts/page.tsx` | 24-28 | Supabase Database Egress | Replaced `select('*')` with explicitly consumed fields `select('id, title, slug')` after tracing child components. | PASSED (`pnpm typecheck`) |
| `src/middleware.ts` | 14 | Vercel Edge Requests | Added regex matcher exclusion for static assets and images. | PASSED (`pnpm build`) |
| `src/lib/storage.ts` | 42 | Supabase Storage Egress | Added `cacheControl: '31536000'` to immutable upload helper. | PASSED (`pnpm test`) |

---

## 4. Architectural Recommendations (Class B - Approval Required)

The following optimizations require human confirmation before implementation because they alter system architecture, caching semantics, or data models:

### [Rec-1]: [Title, e.g. Introduce Edge CDN Caching on Public Catalog API]
- **Provider & Resource:** Vercel Function Invocations & Supabase Database Egress
- **Proposed Change:** Add `Cache-Control: public, s-maxage=600, stale-while-revalidate=86400` to `GET /api/catalog`.
- **Architectural Impact:** Clients and CDN edge will receive catalog data up to 10 minutes old. Changes in Postgres won't reflect immediately for anonymous visitors.
- **Estimated Savings:** High expected impact. Eliminates ~98% of repetitive database and serverless executions for public catalog traffic.
- **User Action Required:** Reply "Approve Rec-1" to implement.

### [Rec-2]: [Title, e.g. Create Database Index for Event Timestamp Query]
- **Provider & Resource:** Supabase Postgres CPU / Disk Space Tradeoff
- **Proposed Change:** Propose index `CREATE INDEX idx_events_user_created ON events(user_id, created_at DESC)`.
- **Tradeoff:** Accelerates filtering by user_id and sort by date, but consumes ~15MB Postgres disk storage on the free tier.
- **User Action Required:** Reply "Approve Rec-2" to generate migration script.

---

## 5. Skipped Findings & Negative Constraints

- **PHP Projects:** [If detected, state: "PHP detected. Optimization halted per strict scope policy."]
- **Paid Tier Features:** [Explicitly note any avoided temptations, e.g. "Avoided Supabase Storage Image Transformations as they are unavailable on Free plan."]
- **Security Safeguards:** [e.g. "Maintained Serverless Function proxy on `/api/payment-intent` to prevent exposing server secret keys to browser."]
- **Low-Value Refactors:** [e.g. "Ignored micro-optimization in rarely called setup script to preserve maintainability."]

---

## 6. Verification Record

- **Package Manager Detected:** [e.g. `pnpm`]
- **Commands Executed:**
  ```bash
  $ pnpm run typecheck
  # Output: 0 errors found (Exit Code: 0)

  $ pnpm run test
  # Output: 34 passed, 0 failed (Exit Code: 0)

  $ pnpm run build
  # Output: Route tree compiled successfully; static/dynamic boundaries confirmed (Exit Code: 0)
  ```
- **Unverified Aspects:** [Exhaustive list of any aspect not directly validated by automated tests, e.g. live network load test or production analytics].

---

## 7. Expected Resource Impact

| Provider | Resource Vector | Baseline State | Optimized State | Expected Impact | Evidence |
|---|---|---|---|---|---|
| Supabase | Database Egress | Fetched 38 columns (`select('*')`) per row | Fetches 4 columns | **High Expected Impact** | Direct payload size reduction of ~85% on list queries. |
| Vercel | Edge Requests | Middleware executed on every `.png`/`.js` asset | Middleware bypasses static assets | **High Expected Impact** | Eliminates 10-30 Edge requests per page load. |
| Supabase | Realtime Channels | Duplicate channel created on every route change | Single channel with `onDestroy` cleanup | **Medium Expected Impact** | Prevents connection leaks and duplicate message charges. |
| Vercel | Image Optimization | Unbounded responsive widths requested | Constrained `sizes` attribute | **Medium Expected Impact** | Restricts variant generation to targeted viewports. |

> *Note: Percentages and values reflect measured code differences or directional estimates. No speculative production dollar amounts are claimed without live telemetry.*
```

# TierTune

TierTune is a reusable agent skill that audits and optimizes web applications deployed on Vercel and Supabase, with a focus on reducing unnecessary free-tier resource consumption without changing intended application behavior, security, or data correctness.

**Scope:** TierTune currently supports **ONLY** Vercel and Supabase. PHP projects are intentionally out of scope.

---

## Why TierTune

Finished or near-finished applications often consume platform resources unintentionally due to patterns that are hard to catch during initial development:

- Duplicate requests and hydration double-fetches
- Unnecessary serverless function invocations
- Excessive database queries and unindexed scans
- Column over-fetching (`select('*')`)
- Supabase database and storage egress
- Large, un-cached storage downloads
- Leaked Realtime channel subscriptions
- Inefficient responsive image sizing and transformation variant explosions
- Missing or misconfigured caching headers
- Multi-hop cross-provider request chains

TierTune systematically audits these areas and focuses on removing waste. It does not promise that an application will never hit free-tier quotas, nor does it make guaranteed percentage savings claims. Its goal is eliminating measurable, unnecessary platform usage.

---

## How It Works

TierTune executes a structured 6-stage optimization pipeline:

```
SCAN → TRACE → PRIORITIZE → OPTIMIZE → VERIFY → REPORT
```

1. **SCAN** — Detects project architecture, frameworks, runtime environments, package managers, Vercel configurations, and Supabase integration points.
2. **TRACE** — Traces end-to-end data and request flows across Browser ↔ Vercel Edge ↔ Vercel Functions ↔ Supabase.
3. **PRIORITIZE** — Evaluates and ranks findings by estimated resource impact (HIGH, MEDIUM, or LOW).
4. **OPTIMIZE** — Automatically applies only safe, high-confidence Class A code improvements.
5. **VERIFY** — Runs native project build, test, lint, and typecheck commands to validate that no functionality broke.
6. **REPORT** — Generates a clear summary documenting what was optimized, what was skipped, and what requires user approval.

---

## Safety Model

Every proposed optimization is categorized under a strict safety gate:

- **Class A — Safe / High Confidence:** Changes that preserve existing behavior, maintain security boundaries, and can be verified via build and test suites (e.g., consumer-verified column narrowing, adding teardown to unmounted Realtime channels, excluding static assets from middleware matchers, hoisting database client initialization). TierTune may apply these automatically.
- **Class B — Approval Required:** Changes that alter architecture, caching freshness semantics, database schema, table retention policies, indexes, Row Level Security, authentication, Realtime behavior, or image preprocessing pipelines. TierTune documents these in the final report and requires user approval before execution.

### Hard Rules

TierTune adheres to strict non-negotiable boundaries:

- Never weaken Row Level Security (RLS) policies.
- Never expose `service_role` keys or server secrets to client browsers.
- Never expose private environment variables.
- Never delete user data or storage objects automatically.
- Never silently modify application architecture or data freshness.
- Never fabricate savings metrics; only measured values or directional estimates are reported.
- Never recommend paid-tier features (e.g., paid image transformations, plan upgrades) as the default free-tier solution.

---

## Supported Stacks

TierTune is framework- and language-agnostic across stacks that target Vercel and Supabase:

- **Frontend & Meta-Frameworks:** Next.js, React / Vite, Create React App, Vue / Nuxt, Svelte / SvelteKit, Astro, Remix / React Router, Angular, Solid / SolidStart, static HTML/CSS/JavaScript.
- **Server Runtimes & Functions:** Node.js, Bun, Python, Go, Ruby, Rust, WebAssembly, and Edge Runtime.
- **Supabase Integrations:** Client SDKs, direct REST / PostgREST HTTP queries, SQL drivers, ORMs (Prisma, Drizzle, SQLAlchemy), Edge Functions, Storage, Realtime, and Auth.

> **Note:** PHP is intentionally not supported by TierTune v1. If a primary PHP application is detected, TierTune halts immediately.

---

## Installation

Because agent runtimes and IDEs use different skill directories, installation depends on your specific environment:

1. Clone the repository:

   ```bash
   git clone https://github.com/naphiertech/tier-tune.git
   ```

2. Copy or symlink the `tier-tune` directory into your agent's configured skills folder.

3. Restart or reload the agent if required.

### Example (Gemini / Antigravity on Windows)

```powershell
# Copy into the user skill directory:
Copy-Item -Recurse tier-tune "C:\Users\<username>\.gemini\config\skills\tier-tune"
```

*(Refer to your specific agent or IDE documentation for its skill discovery path.)*

---

## Usage

Run TierTune against an existing, finished or near-finished repository by prompting your agent:

- *"Use TierTune on this project."*
- *"Run TierTune and optimize this project for Vercel and Supabase free plans."*
- *"Audit this project with TierTune but do not make any changes."*

---

## What TierTune Checks

| Area | Checks |
|---|---|
| **Vercel** | Serverless function invocations, execution duration, memory allocation, Edge requests, Fast Data Transfer, Fast Origin Transfer, ISR revalidation frequency, middleware matchers, responsive image variant sizing, and static asset delivery. |
| **Supabase** | Unfiltered queries (`select('*')`), pagination limits, row count optimization, mutation payload return modes (`return=minimal`), Storage browser `cacheControl`, uncleaned Realtime channels, Presence/Broadcast throttling, Auth session loops, and unbounded log tables. |
| **Cross-Provider** | Request chains (Browser → Vercel Function → Supabase), evaluating proxy utility (caching, security, transformation) vs direct client access, ensuring optimizations do not merely shift consumption between providers. |

---

## Project Structure

```
tier-tune/
├── SKILL.md                 # Primary agent skill instructions and execution workflow
├── README.md                # Project documentation and usage guide
├── LICENSE                  # MIT License
├── references/
│   ├── frameworks.md        # Framework-specific optimization guides
│   ├── report-format.md     # Standardized markdown report template
│   ├── safety-matrix.md     # Class A/B classification matrix and safety rules
│   ├── supabase.md          # Supabase database, storage, realtime, and auth reference
│   └── vercel.md            # Vercel functions, edge, caching, and image reference
└── tests/
    ├── scenarios.md         # Behavioral pressure test specifications (Scenarios A–L)
    └── verify_skill.py      # Automated structural verification test suite
```

---

## Status

**TierTune v1**

- Scope: Vercel + Supabase only
- Structural verification: Completed (16/16 automated test suites passing)
- Behavioral scenarios: Scenarios A through L are formally specified with RED baseline and GREEN TierTune contracts for regression evaluation.
- Live agent behavior evaluation: Optional/future validation suite.

---

## License

TierTune is released under the [MIT License](LICENSE).

---

## Author

Created by **Naphier Awalie**  
GitHub: [https://github.com/naphiertech](https://github.com/naphiertech)

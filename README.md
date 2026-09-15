# tier-tune

A production-quality reusable agent skill that audits finished or near-finished web applications targeting Vercel and Supabase free/hobby plans, identifies resource waste vectors, safely executes high-confidence optimizations, and produces actionable architectural recommendations.

## Directory Structure

```
tier-tune/
├── SKILL.md                 # Primary skill definition, workflow, and safety gates
├── references/
│   ├── vercel.md            # In-depth Vercel resource architecture & optimization
│   ├── supabase.md          # In-depth Supabase database, storage, realtime, auth
│   ├── frameworks.md        # Framework adapters (Next.js, Vite, Nuxt, SvelteKit, Astro, Remix, etc.)
│   ├── safety-matrix.md     # Class A vs Class B matrix, cache safety, cross-provider evaluator
│   └── report-format.md     # Standardized final report format
└── tests/
    ├── scenarios.md         # Comprehensive test scenarios (Scenarios A through L)
    └── verify_skill.py      # Structural and behavior specification verification suite
```

## Quick Start

Invoke this skill when an application deployed on Vercel and/or Supabase is ready for cost/resource audit:
```
SCAN → TRACE → PRIORITIZE → OPTIMIZE → VERIFY → REPORT
```

### Core Principle
> "Reduce unnecessary Vercel and Supabase resource consumption without changing the application's intended behavior, security model, data correctness, or user-visible functionality. Eliminate waste before moving work between services."

### Non-Negotiable Boundaries
- **Supported Providers:** Exclusively Vercel and Supabase.
- **PHP Excluded:** Halts immediately if PHP is detected as the primary language.
- **Free-Tier Target:** Never recommends paid-tier upgrades or paid features (e.g. Supabase Storage Image Transformations).
- **Zero Hallucinated Metrics:** Directional estimates used unless benchmarked directly.

# Framework Adapters & Runtime Reference

This guide provides framework-specific optimization patterns and generic HTTP/network inspection rules across all environments supported on Vercel and Supabase.

---

## 1. Next.js (App Router & Pages Router)

### 1.1 App Router Data Fetching & Caching
- **React `cache()` Deduplication:** Wrap server-side data fetching functions in React's `cache()` to prevent duplicate requests across the server component tree during a single render pass.
  ```typescript
  import { cache } from 'react';
  import { createServerClient } from '@/lib/supabase/server';

  export const getProfile = cache(async (userId: string) => {
    const supabase = await createServerClient();
    return supabase.from('profiles').select('id, username, avatar_url').eq('id', userId).single();
  });
  ```
- **Avoid Server + Client Duplicate Fetches:** Never fetch data in a Server Component and immediately trigger an identical `useEffect` or React Query fetch for the same data in a child Client Component without passing the initial data as props or hydrated cache.
- **Route Segment Config:**
  - Mark static informational pages: `export const dynamic = 'force-static'`.
  - Mark user dashboards: `export const dynamic = 'force-dynamic'`. NEVER use ISR on authenticated private routes.

### 1.2 Image Optimization (Framework & Version Aware)
- **Next.js 13+ (App Router & Modern `next/image`):** Add `sizes` prop to all `<Image fill />` components:
  `sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"`
- **Next.js 12 & `next/legacy/image`:** Use `sizes` alongside `layout="fill"` or `layout="responsive"` (do not inject `fill` without verifying Next.js version in `package.json`):
  `<Image src={img} layout="responsive" width={800} height={600} sizes="(max-width: 768px) 100vw, 50vw" />`
- Restrict device sizes in `next.config.js`:
  ```javascript
  images: {
    deviceSizes: [640, 750, 1080, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128],
    formats: ['image/avif', 'image/webp'],
  }
  ```

### 1.3 Middleware Matcher Exclusion
- Ensure `middleware.ts` excludes `_next/static`, `_next/image`, and public static assets (SVG, PNG, ICO) to avoid unnecessary Edge Request invocations.

---

## 2. React + Vite / Create React App (SPA)

### 2.1 Client-Side Query Caching & Deduplication
- **TanStack Query / SWR Defaults:** Ensure query keys are consistent and `staleTime` is set appropriately to prevent aggressive refetching on every component remount or window refocus:
  ```typescript
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes fresh
        refetchOnWindowFocus: false, // Prevent wasteful background refetches
        retry: 1,
      },
    },
  });
  ```
- **Avoid Render-Triggered Fetches:** Ensure Supabase queries are not placed directly in component bodies without `useEffect` or query hooks.

### 2.2 Static Hosting on Vercel
- Vite outputs static SPA HTML/JS/CSS. In `vercel.json`, configure long-term cache headers for bundled assets:
  ```json
  {
    "headers": [
      {
        "source": "/assets/(.*)",
        "headers": [
          { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
        ]
      }
    ]
  }
  ```

---

## 3. Vue / Nuxt 3

### 3.1 Hydration & Data Fetching
- **`useAsyncData` Key Deduplication:** Always pass a unique key to `useAsyncData` or `useFetch` to ensure server-rendered data serializes into the payload and prevents client-side re-fetching on hydration:
  ```typescript
  const { data: posts } = await useAsyncData('posts-list', () =>
    supabase.from('posts').select('id, title, slug')
  );
  ```
- **Nitro Server Routes (Class B by default):** Materially adding or changing `defineCachedEventHandler` or `Cache-Control: public, s-maxage=..., stale-while-revalidate=...` alters catalog/data freshness visible to users and is **Class B** by default (propose for user confirmation with explicit freshness tradeoffs). It may be **Class A** only when the project already clearly establishes the intended freshness semantics and the fix merely restores or propagates that existing behavior:
  ```typescript
  // server/api/catalog.ts (Class B recommendation unless freshness policy pre-established)
  export default defineCachedEventHandler(async (event) => {
    // Cached at the server/CDN level
    return await fetchCatalog();
  }, { maxAge: 60 * 60 });
  ```
- **Nuxt Image (`@nuxt/image`):** When optimizing images in Nuxt, use `<NuxtImg>` with explicit `sizes` and format conversion:
  `<NuxtImg src="/hero.jpg" sizes="sm:100vw md:50vw lg:33vw" format="webp" />`

---

## 4. Svelte / SvelteKit

### 4.1 Server `load` Functions & Cache Headers
- In `+page.server.ts`, set `setHeaders` for public pages (Class B by default):
  Materially adding or changing `s-maxage` or CDN cache TTL alters data freshness and is **Class B** by default (eligible for Class A only if project already clearly establishes intended freshness semantics):
  ```typescript
  export const load = async ({ setHeaders }) => {
    // Propose for user approval (Class B default):
    setHeaders({
      'cache-control': 'public, max-age=3600, s-maxage=86400'
    });
    return { ... };
  };
  ```
- **Prerendering:** Set `export const prerender = true;` in `+page.ts` for marketing and documentation pages.

### 4.2 Realtime Subscription Teardown
- Always clean up Supabase channels in Svelte components using `onDestroy`:
  ```svelte
  <script>
    import { onDestroy } from 'svelte';
    // ... subscribe
    onDestroy(() => {
      supabase.removeChannel(channel);
    });
  </script>
  ```

---

## 5. Astro

### 5.1 Static-First Architecture & Assets
- Astro defaults to `output: 'static'`. Keep `output: 'static'` unless the entire site must be dynamic.
- For isolated dynamic endpoints or server-rendered pages in a static site:
  ```astro
  ---
  // src/pages/api/submit.ts
  export const prerender = false;
  ---
  ```
- Use selective hydration (`client:visible`, `client:idle`) rather than `client:load` for interactive UI components to minimize bundle overhead and execution cost.
- **Astro Image Optimization (`astro:assets`):** Use Astro's built-in `<Image>` component with responsive widths and `sizes`:
  ```astro
  ---
  import { Image } from 'astro:assets';
  import heroImg from '../assets/hero.jpg';
  ---
  <Image src={heroImg} widths={[400, 800, 1200]} sizes="(max-width: 800px) 100vw, 800px" alt="Hero" />
  ```

---

## 6. Remix / React Router (v7)

### 6.1 Loader Headers & Waterfall Elimination
- Return HTTP caching headers from loaders for public resources (Class B by default):
  Adding or changing `s-maxage` or CDN cache TTL in route loaders materially alters data freshness and is **Class B** by default (Class A only if existing project policy established freshness):
  ```typescript
  // Propose for user approval (Class B default):
  export const headers = () => ({
    'Cache-Control': 'public, max-age=300, s-maxage=3600',
  });
  ```
- Run independent data fetches in parallel using `Promise.all` inside loaders rather than sequential awaits.

---

## 7. Angular

### 7.1 HttpClient Interceptors & Caching
- Use an `HttpInterceptor` with `shareReplay(1)` or transfer state for SSR hydration to avoid duplicate client requests after server rendering.
- Configure `routes` with selective preloading strategies instead of prefetching all lazy chunks upfront.

---

---

## 8. Solid & SolidStart

### 8.1 Fine-Grained Reactivity & Signal Hygiene
- **Avoid Render-Loop Query Triggers:** Solid tracking scopes re-execute effects whenever tracked signals change. Never trigger Supabase queries inside `createEffect` without explicitly narrowing tracked signal dependencies to prevent runaway request loops.
- **`createResource` SSR Hydration Deduplication:** Pass server-fetched resource state into `createResource` to prevent client hydration from firing an identical secondary network call:
  ```typescript
  import { createResource } from 'solid-js';
  import { supabase } from '~/lib/supabase';

  // Using initialValue from server loader:
  const [data] = createResource(
    () => fetchId(),
    async (id) => {
      const { data } = await supabase.from('items').select('id, name, price').eq('id', id).single();
      return data;
    },
    { initialValue: props.initialItem }
  );
  ```

### 8.2 SolidStart Server Functions (`server$`)
- **Hoisting Initialization:** Hoist Supabase or database client instantiation outside the `server$()` closure so connections and clients are reused across requests rather than instantiated on every RPC call:
  ```typescript
  import { server$ } from '@solidjs/start/server';
  import { createClient } from '@supabase/supabase-js';

  // Hoisted module level:
  const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_ANON_KEY!);

  export const getItemSummary = server$(async (id: string) => {
    const { data } = await supabase.from('items').select('id, name').eq('id', id).single();
    return data;
  });
  ```

### 8.3 Prerendering Static Routes
- In `app.config.ts`, designate static informational or landing pages for build-time prerendering (`prerender: { routes: ['/', '/about', '/pricing'] }`) to eliminate serverless function invocations on public pages.

---

## 9. Static HTML / CSS / JavaScript

- Configure `vercel.json` with clean routing and explicit caching headers.
- Compress raw media assets before committing (WebP/AVIF).
- Prevent duplicate font and third-party script loads.

---

## 10. Generic Vercel Serverless Functions & Multi-Language Runtimes

Applicable across **Node.js, Bun, Python, Go, Ruby, Rust, WebAssembly, and Edge Runtime**:

### 10.1 Python Functions on Vercel (`api/*.py`)
- **Module-Level Client Hoisting:** Never initialize database engines or `supabase-py` clients inside handler functions. Initializing at module scope shares instances across warm container invocations:
  ```python
  # api/index.py
  import os
  from fastapi import FastAPI
  from supabase import create_client, Client

  app = FastAPI()

  # Hoisted once at module load:
  supabase_client: Client = create_client(
      os.environ["SUPABASE_URL"],
      os.environ["SUPABASE_ANON_KEY"]
  )

  @app.get("/api/articles")
  def get_articles():
      # Narrow column projection in Python
      response = supabase_client.table("articles").select("id, title, slug").execute()
      return response.data
  ```
- **Connection Pooling:** When connecting directly via SQLAlchemy, `psycopg3`, or `asyncpg`, connect via Supabase Supavisor pooler (port 6543, transaction mode) and limit connection pool size (`pool_size=3, max_overflow=2`) to avoid exhausting Postgres connection limits.

### 10.2 Go Functions on Vercel (`api/*.go`)
- **`sql.DB` Global Pool Management:** In Go serverless handlers, allocate `sql.DB` in `init()` or package scope with bounded connection pool settings:
  ```go
  package handler

  import (
      "database/sql"
      "net/http"
      "os"
      _ "github.com/jackc/pgx/v5/stdlib"
  )

  var db *sql.DB

  func init() {
      var err error
      db, err = sql.Open("pgx", os.Getenv("DATABASE_URL"))
      if err == nil {
          db.SetMaxOpenConns(4)
          db.SetMaxIdleConns(2)
      }
  }

  func Handler(w http.ResponseWriter, r *http.Request) {
      // Query specific columns only
      rows, err := db.Query("SELECT id, title FROM articles LIMIT 20")
      // ... process and return JSON
  }
  ```

### 10.3 Rust Functions on Vercel (`api/*.rs`)
- Use `std::sync::OnceLock` or `lazy_static!` to hoist asynchronous database pools (`sqlx::PgPool`) or HTTP clients (`reqwest::Client`) across invocations to avoid renegotiating TLS on every request.

### 10.4 Vercel Edge Runtime & Bun
- **Edge Runtime:** Avoid heavyweight Node-specific packages in Edge functions (`runtime = 'edge'`). Prefer lightweight PostgREST HTTP queries over direct TCP database drivers to keep bundle sizes under 1MB and minimize cold starts.
- **Bun:** Leverage Bun's fast native `fetch` and direct Postgres client; hoist clients at file level.

---

## 11. Fallback Protocol for Unfamiliar Frameworks

If a project uses an unfamiliar, emerging, or custom framework:
1. **Do NOT refuse to work.** Fall back to universal HTTP and network principles.
2. **Inspect Entry Points:** Find the server entry (`server.js`, `main.go`, `app.py`, `handler.ts`).
3. **Analyze Network Flow:** Trace HTTP route definitions, middleware chains, static file serving, and outbound database/Supabase calls.
4. **Inspect Asset Headers:** Verify static files carry `Cache-Control: public, max-age=31536000, immutable`.
5. **Inspect Supabase Usage:** Check for unbounded `select('*')`, missing limits, uncleaned Realtime channels, and client-side pre-upload hygiene.

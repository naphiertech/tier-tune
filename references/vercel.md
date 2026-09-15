# Vercel Free-Tier Optimization Reference

This guide details resource consumption vectors, architectural root causes, and optimization techniques for applications hosted on Vercel.

---

## 1. Resource Consumption Vectors

Vercel resource consumption spans compute, networking, edge routing, and media transformation:

| Resource Vector | Description | Common Waste Mechanisms |
|---|---|---|
| **Fast Data Transfer** | Public bandwidth served from Vercel Edge CDN to end-users | Uncompressed static assets, oversized images, large JSON payloads, lack of HTTP caching. |
| **Fast Origin Transfer** | Bandwidth between Vercel Functions/Edge and external services (e.g. Supabase, APIs) | Function querying and downloading unpruned database rows, relaying binary assets. |
| **Edge Requests** | Total HTTP requests hitting Vercel Edge network | Static asset requests matching un-scoped middleware, polling loops, lack of client cache. |
| **Function Invocations** | Count of Serverless / Edge Function executions | Uncached dynamic endpoints, dynamic SSR for static content, duplicate client/server fetch. |
| **Fluid Active CPU / Execution Time** | Wall-clock CPU time consumed during function execution | Un-hoisted database connections, expensive in-handler parsing, external API waterfalls. |
| **Image Optimization** | Source images transformed into modern formats (WebP/AVIF) | Missing `sizes` attributes generating variant explosions, unconstrained responsive widths. |
| **ISR / Edge Cache Reads & Writes** | Writes and reads against Vercel's distributed cache | Overly frequent revalidation intervals (`revalidate: 1`), non-deterministic cache keys. |

> **Official Reference:** Consult official Vercel documentation at [vercel.com/docs](https://vercel.com/docs) for current plan definitions and runtime specifications. Do not rely on hardcoded limits.

---

## 2. Serverless Function & Compute Optimization

### 2.1 Hoisting Initialization & Connection Reuse
Serverless function containers stay warm across consecutive invocations. Initializing clients, SDKs, or parsing schemas inside the request handler wastes CPU time on every call.

**Bad (Per-Request Initialization):**
```typescript
// api/data.ts
export default async function handler(req, res) {
  // Executed on every invocation: burns CPU & memory
  const client = new HeavyDatabaseClient({ ...config });
  const schema = compileComplexValidator();
  const data = await client.query('SELECT ...');
  res.json(data);
}
```

**Good (Hoisted Warm State):**
```typescript
// api/data.ts
// Initialized ONCE per container instance:
const client = new HeavyDatabaseClient({ ...config });
const schema = compileComplexValidator();

export default async function handler(req, res) {
  const data = await client.query('SELECT ...');
  res.json(data);
}
```

### 2.2 Evidence-Based Function Proxy Analysis
Never remove or retain a Vercel ↔ Supabase proxy based solely on the assumption that proxies are good or bad.

For every Vercel ↔ Supabase proxy, systematically determine whether it provides:
- **Effective caching:** Edge CDN caching (`s-maxage`) shielding Supabase from repeated hits. (Note: For external origin proxies, new Vercel projects can respect upstream `Cache-Control` headers by default, while existing projects may require specific configuration or opt-in. Inspect the project's actual cache behavior and configuration rather than assuming manual CDN-Cache-Control configuration is always required).
- **Authentication/authorization:** Verifying caller session, tokens, or permissions before querying.
- **Secret protection:** Guarding `service_role` keys or third-party secrets.
- **Transformation:** Shaping, filtering, or parsing data before delivery.
- **Aggregation:** Merging multiple table or service results into a single payload.
- **Validation:** Enforcing business rules or schema validation before mutations.
- **Rate limiting:** Throttling abusive requests before they reach Postgres.
- **Request coalescing:** Merging concurrent identical incoming requests to avoid thundering herds.
- **Another meaningful server responsibility:** Logging, telemetry, or webhook handling.

**Evaluation Process:**
- **If the proxy provides server responsibilities:** Calculate and describe why retaining it lowers total usage (e.g. Edge caching eliminates 95%+ of downstream database queries). Keep the proxy and optimize its compute and payload efficiency.
- **If it is purely a pass-through (zero server responsibilities):**
  1. Evaluate direct access from the browser/client.
  2. Check security: ensure public `anon` key is used and Row Level Security (RLS) is fully active and tested.
  3. Check Supabase load impact: ensure direct traffic will not exhaust connection limits or connection pool capacity.
  4. Check Vercel transfer and function cost savings.
  5. Check caching behavior: inspect actual project cache behavior/config and ensure removing the proxy does not sacrifice an existing effective cache.
  Formulate direct access as a **Class B** architectural recommendation.

### 2.3 Function Memory Sizing & Timeout Configuration
By default, Vercel allocates 1024MB of memory to Serverless Functions. Simple I/O-bound proxy routes or PostgREST fetchers rarely consume more than 128MB–256MB.
- Configure targeted function memory in `vercel.json`:
  ```json
  {
    "functions": {
      "api/**/*.ts": {
        "memory": 256,
        "maxDuration": 10
      }
    }
  }
  ```
- Right-sizing memory reduces cold start initialization and memory resource reservation.

### 2.4 Waterfall Request Elimination
Sequential `await` calls on independent external resources multiply function execution duration:
```typescript
// Bad: Sequential waterfall doubles execution duration (e.g. 300ms + 300ms = 600ms CPU duration)
const user = await fetchUser(userId);
const settings = await fetchSettings(userId);

// Good: Concurrent parallel execution runs in max(300ms, 300ms) = ~300ms
const [user, settings] = await Promise.all([fetchUser(userId), fetchSettings(userId)]);
```
*Note:* Do NOT merge or parallelize requests that have differing authorization scopes or freshness requirements.

### 2.5 Function Storage & Deployment Artifacts
Vercel has strict deployment bundle size limits (50MB compressed / 250MB uncompressed).
- **Prune Heavy Dependencies:** Never import entire monorepo packages, dev-only tools, or full utility libraries (e.g. import `lodash/get` or native methods rather than full `lodash`).
- **Exclude Non-Essential Files:** Use `.vercelignore` to exclude local documentation, tests, fixtures, and source assets from deployment bundles.

### 2.6 Preventing Function Recursion & Request Loops
- Never write Edge Middleware that rewrites a request to an internal route which subsequently triggers the same middleware.
- Never write API handlers that invoke other API routes on the same Vercel deployment over external HTTP. Import and call the internal shared logic directly.

### 2.7 In-Memory Caching for CPU-Heavy Pure Computations
Within warm serverless containers, memoize expensive pure computations (e.g. schema compilations, markdown AST generation) using an in-memory LRU cache to eliminate repeated CPU work across consecutive hits.

---

## 3. Middleware Scope & Edge Request Control

Vercel Middleware runs at the Edge before every matched request. Misconfigured matchers cause middleware to execute on every single CSS, JS, image, and favicon request.

### 3.1 Strict Matcher Filtering
Always exclude static files and image optimization paths from middleware execution.

```typescript
// middleware.ts
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files with extensions (e.g. .svg, .png, .jpg, .css, .js)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|css|js)$).*)',
  ],
};
```

---

## 4. Rendering Strategy & Cache Headers

### 4.1 Static vs Dynamic Route Selection
Do NOT convert pages to static if they require real-time personalization or authentication. However, pure marketing, legal, documentation, and blog pages should never run dynamic serverless execution.

| Rendering Mode | When Appropriate | Vercel Cost Impact |
|---|---|---|
| **SSG / Pre-rendered** | Content changes at build time (docs, landing pages, blogs). | 0 Function invocations; served directly from Edge CDN cache. |
| **ISR (Incremental Static Regeneration)** | Content updates periodically (hourly catalog, daily blog posts). | 1 invocation per revalidation window; all other hits served from CDN. |
| **Dynamic SSR** | Authenticated dashboards, user-specific search, personalized content. | 1 invocation per page hit. Requires caching query clients where possible. |

### 4.2 Cache-Control Header Standards
For API routes and server responses:

- **Public Static Content:**
  ```http
  Cache-Control: public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800
  ```
  *(Browser caches for 1h, Vercel Edge CDN caches for 24h, serves stale while regenerating in background. Note: Materially adding or changing `s-maxage`, `stale-while-revalidate`, or CDN cache TTL on application data endpoints alters data freshness and is **Class B by default**; eligible for Class A only when existing project policy already clearly establishes intended freshness semantics).*

- **Private / Authenticated Content:**
  ```http
  Cache-Control: private, no-cache, no-store, must-revalidate
  ```
  *(Shared/public CDN caching is strictly PROHIBITED automatically. Never specify `s-maxage` or `public` on user-specific or sensitive routes. For sensitive authenticated endpoints—such as billing, accounts, security settings, private dashboards, and tokens—safe optimization is in-flight query/request deduplication [Class A]. Persistent browser HTTP caching is Class B unless clearly defined by existing application policy; sensitive endpoints must preserve `no-store` when intended).*

- **Immutable Hashed Assets:**
  ```http
  Cache-Control: public, max-age=31536000, immutable
  ```

---

## 5. Image Optimization Hygiene

Vercel Image Optimization automatically resizes and converts images to WebP/AVIF. Waste occurs when applications request arbitrary widths or missing responsive descriptors. Recommendations must remain framework- and version-aware.

### 5.1 Responsive Sizes & Variant Control (Framework & Version Aware)
When image components are rendered without explicit responsive descriptors, browsers request full-width desktop variants on mobile screens, triggering unnecessary image transformations. Always inspect `package.json` and adapt to the project's framework and version:

- **Next.js 13+ (App Router & Modern `next/image`):**
  ```tsx
  <Image 
    src="/hero.jpg" 
    alt="Hero" 
    fill 
    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
    priority={false}
  />
  ```
- **Next.js 12 & `next/legacy/image`:** Use `sizes` with `layout="fill"` or `layout="responsive"` (never inject `fill` boolean on legacy Next.js):
  ```tsx
  <Image src="/hero.jpg" alt="Hero" layout="responsive" width={800} height={600} sizes="(max-width: 768px) 100vw, 50vw" />
  ```
- **Nuxt 3 (`@nuxt/image`):**
  ```vue
  <NuxtImg src="/hero.jpg" sizes="sm:100vw md:50vw lg:33vw" format="webp" alt="Hero" />
  ```
- **Astro (`astro:assets`):**
  ```astro
  <Image src={heroImg} widths={[400, 800, 1200]} sizes="(max-width: 800px) 100vw, 800px" alt="Hero" />
  ```
- **Vite / SvelteKit / Static HTML:** Use `<picture>` with responsive `<source srcset="..." sizes="...">` or native `<img>` with `srcset` and `sizes`.

### 5.2 Device Sizes in Configuration
Inspect `next.config.js` or framework configuration:
```javascript
module.exports = {
  images: {
    // Keep device sizes focused to avoid variant explosion:
    deviceSizes: [640, 750, 1080, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 31536000, // Cache transformed images aggressively
  },
};
```

> **Warning:** NEVER blindly set `unoptimized: true` globally. Disabling optimization forces clients to download uncompressed raw assets (e.g. 5MB camera photos), dramatically increasing Fast Data Transfer egress!

### 5.3 Local Static Asset Optimization (`public/`)
Static files in `public/` (e.g. logos, icons, illustrations) bypass Vercel Image Optimization when rendered via plain `<img>` tags:
- Convert uncompressed PNGs and JPEGs in `public/` to WebP or AVIF at build/pre-commit time.
- Minify SVGs (using tools like `svgo`) to strip editor metadata, lowering Fast Data Transfer.
- Configure immutable cache headers for hashed static assets in `vercel.json`.

---

## 6. Pre-fetching Control

Frameworks (e.g. Next.js, Nuxt, SvelteKit) often prefetch linked routes automatically when links appear in viewport.
- On large pages with hundreds of links (e.g. product catalogs or table rows), this causes dozens of simultaneous Edge requests and server invocations.
- Where appropriate, set `prefetch={false}` on below-the-fold links or non-critical secondary pages, while leaving prefetching active on primary user journeys.

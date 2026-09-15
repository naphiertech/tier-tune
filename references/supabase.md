# Supabase Free-Tier Optimization Reference

This guide details resource vectors, architectural waste patterns, and safe optimization methods for Supabase services (Database, Storage, Realtime, Edge Functions, Auth).

---

## 1. Resource Consumption Vectors

Supabase free-tier resource consumption spans multiple interconnected components:

| Resource Vector | Description | Common Waste Mechanisms |
|---|---|---|
| **Database Egress** | Network bandwidth leaving Postgres via PostgREST, direct SQL, or SDK queries | Unfiltered `select('*')`, wide joins, lack of pagination, fetching entire rows for counts. |
| **Storage Egress** | Outbound file transfer from Supabase Storage buckets | Missing browser `cacheControl`, repeated un-cached downloads, relaying files through Vercel. |
| **Realtime Messages & Concurrency** | Messages transmitted via WebSocket channels (Postgres Changes, Broadcast, Presence) | Unfiltered table subscriptions, forgotten channel cleanup, duplicate component mounts. |
| **Database Disk Size** | Total allocated disk storage for Postgres tables, indexes, and WAL | Log bloat, unbounded history tables, speculative over-indexing. |
| **Edge Function Invocations & Compute** | Wall-clock execution and memory of Deno/Node Edge Functions | Passing through raw Supabase payloads unchanged, cold-start re-initialization. |
| **Auth Operations** | Sign-up, sign-in, and token refresh requests | Invoking `getUser()` on every render loop, rapid refresh polling. |

> **Official Reference:** Consult official Supabase documentation at [supabase.com/docs](https://supabase.com/docs) for current architecture details. Do not rely on hardcoded limits.

---

## 2. Database Egress Optimization

Database egress is often the fastest resource to deplete when applications fetch full rows indiscriminately.

### 2.1 Consumer-Traced Column Narrowing
Replacing `select('*')` with targeted columns significantly cuts transfer size. However, **never remove fields blindly based on a single file**. You must trace consumers:
1. Inspect the query site.
2. Trace the returned object through state, props, helper functions, and child components.
3. Check if external APIs or child views rely on dynamic keys.
4. Only project the verified subset of columns.

**Bad (Full Row Egress):**
```typescript
// Fetches 40 columns including 50KB text bodies:
const { data } = await supabase
  .from('articles')
  .select('*')
  .order('created_at', { ascending: false });
```

**Good (Targeted Projection):**
```typescript
// Fetches only what the list view renders:
const { data } = await supabase
  .from('articles')
  .select('id, title, slug, published_at, author:authors(id, name)')
  .order('created_at', { ascending: false });
```

### 2.2 Counting Without Fetching Data
Applications frequently download hundreds or thousands of full rows just to display `data.length`.

**Bad (High Egress Count):**
```typescript
// Downloads all rows and columns across the network:
const { data } = await supabase.from('orders').select('*');
const orderCount = data?.length || 0;
```

**Good (Zero-Egress Count with Head Query):**
```typescript
// Performs a HEAD request returning only the count header in HTTP headers:
const { count } = await supabase
  .from('orders')
  .select('*', { count: 'exact', head: true });
```

### 2.3 Strict Pagination and Limits
Never leave unbounded `select()` calls on tables that grow over time.
- Always apply `.limit(PAGE_SIZE)` and `.range(from, to)`.
- Use cursor-based pagination (`.gt('id', lastId).limit(20)`) for high-volume infinite scroll.

### 2.4 Mutation Return Trimming
By default, some mutations request the full inserted or updated record back from Postgres:
```typescript
// Only include .select() if the caller actually consumes the returned record!
// If you only need confirmation of success:
const { error } = await supabase
  .from('audit_logs')
  .insert({ action: 'login', user_id: uid });
// Avoid trailing .select('*') if the response is ignored.
```

### 2.5 SDK-Independent & Direct PostgREST HTTP Protocols
Supabase is accessed across various languages via HTTP/REST (PostgREST). Do not assume `@supabase/supabase-js`. Universal PostgREST headers and URL query patterns eliminate egress in any language (Python, Go, Rust, curl):

- **Column Projection via Query Parameter:**
  `GET /rest/v1/articles?select=id,title,slug,author:authors(id,name)`
  *(Fetches only specified columns across joined tables without raw SQL).*
- **Zero-Egress Count with HEAD & Prefer Header:**
  `HEAD /rest/v1/orders?select=*` with HTTP Header `Prefer: count=exact`
  *(Returns total count in `Content-Range: 0-0/1250` response header with 0 body bytes).*
- **Mutation Return Egress Control:**
  `POST /rest/v1/audit_logs` with HTTP Header `Prefer: return=minimal`
  *(Instructs PostgREST to return HTTP 201 with an empty body instead of returning the inserted record).*
- **HTTP Range Pagination:**
  `GET /rest/v1/articles` with HTTP Header `Range: 0-19` or query params `?limit=20&offset=0`.

### 2.6 Direct SQL Drivers & ORM Patterns (Prisma, Drizzle, SQLAlchemy, GORM)
When applications connect directly to Postgres:
- **Raw SQL:** Replace `SELECT *` with explicit column projections `SELECT id, title, created_at FROM ...`. Omit `RETURNING *` from `INSERT`/`UPDATE` statements unless the returning data is actually consumed by the application.
- **Prisma ORM:** By default, `prisma.article.findMany()` selects all columns including heavy text/blob fields. Enforce `select`:
  ```typescript
  const articles = await prisma.article.findMany({
    select: { id: true, title: true, slug: true }, // Avoid default full model retrieval
  });
  ```
- **Drizzle ORM:** Avoid `db.select().from(...)`. Use explicit projection:
  ```typescript
  const result = await db.select({ id: articles.id, title: articles.title }).from(articles);
  ```
- **Python (SQLAlchemy / SQLModel):**
  Query specific model attributes (`session.execute(select(Article.id, Article.title))`) rather than loading full model objects.
- **Go (`database/sql` / `pgx`):**
  Query only needed columns and scan into targeted structs to reduce wire transfer from Supabase.

---

## 3. Storage Egress Optimization

### 3.1 Browser Cache-Control Headers
When files are uploaded without specifying `cacheControl`, browsers may refetch images and documents on every page load or session.
- **Versioned / Content-Hashed Objects:** Use aggressive immutable caching:
  ```typescript
  await supabase.storage.from('assets').upload(filePath, file, {
    cacheControl: '31536000', // 1 year cache
    upsert: false,
  });
  ```
- **Mutable User Avatars / Overwritten Files:** Use standard revalidation caching:
  ```typescript
  await supabase.storage.from('avatars').upload(filePath, file, {
    cacheControl: '3600', // 1 hour browser cache
    upsert: true,
  });
  ```

### 3.2 Pre-Upload Client-Side Optimization & Preprocessing Classification
**CRITICAL FREE TIER RULE:** Supabase Storage Image Transformations (`/render/image/`) are a **PAID-ONLY** feature.
- **NEVER** recommend or implement Supabase Storage Image Transformations as an optimization for free-tier projects.
- **Image Preprocessing Safety Classification:** Introducing a new client-side or server-side image compression, resizing, format conversion, or preprocessing pipeline changes upload behavior and potentially image quality.
  - **Class B by default:** Propose client-side downscaling/compression in the final report with quality/resolution tradeoffs for user authorization. Do NOT inject a new pipeline automatically.
  - **Class A exception:** Only when an existing image optimization pipeline is already present in the codebase and TierTune is correcting an obvious configuration or implementation defect without changing its intended output.
  - **Storage `cacheControl` (Class A):** Specifying or improving `cacheControl` headers for suitable immutable or versioned uploads remains a safe Class A auto-fix.
- **Free-Tier Client Downscale Pattern (Proposed for Class B Approval):**
  ```typescript
  // Client-side downscale snippet for Class B proposal:
  async function resizeImageBeforeUpload(file: File, maxWidth = 1200, quality = 0.82): Promise<Blob> {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxWidth / bitmap.width);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width * scale;
    canvas.height = bitmap.height * scale;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b!), 'image/webp', quality));
  }
  ```

### 3.3 Storage Access Architecture
- **Do NOT proxy public Supabase Storage files through Vercel Serverless Functions.** Serving public media through a Vercel Function burns both Supabase Storage egress and Vercel Fast Origin Transfer + Function duration. Serve public media directly via the Supabase Storage CDN URL.
- **Never automatically delete storage objects or alter bucket RLS policies** without explicit user consent.

---

## 4. Realtime Connection & Message Control

Realtime charges by concurrent connections and transmitted messages.

### 4.1 Strict Lifecycle Cleanup (Remove Channels on Unmount)
Every mounted component that creates a channel must clean it up when unmounted. Missing cleanups in SPAs cause channel leaks on every navigation.

**React / Next.js:**
```typescript
useEffect(() => {
  const channel = supabase.channel('room-' + roomId)
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages', filter: `room_id=eq.${roomId}` }, onMsg)
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}, [roomId]);
```

**Svelte / SvelteKit:**
```typescript
onDestroy(() => {
  supabase.removeChannel(channel);
});
```

**Vue / Nuxt:**
```typescript
onUnmounted(() => {
  supabase.removeChannel(channel);
});
```

### 4.2 Targeted Filters on Postgres Changes
- Never listen to all events on an entire schema: `{ event: '*', schema: 'public' }`.
- Restrict to specific tables, events (`INSERT` only if `UPDATE`/`DELETE` are ignored), and record IDs (`filter: 'user_id=eq.' + uid`).

### 4.3 Presence & Broadcast Traffic Throttling
Realtime Broadcast and Presence stream arbitrary JSON messages over WebSockets. Unconstrained usage burns message limits rapidly:
- **Presence Throttling:** Never broadcast cursor movements or window scroll positions on raw UI events (60fps). Throttle presence updates to a minimum interval of 1000ms, or sync only discrete status changes (`online`, `idle`).
- **Tab Inactivity Pause:** When the user switches tabs, pause Presence tracking:
  ```typescript
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      presenceChannel.untrack();
    } else {
      presenceChannel.track({ online_at: new Date().toISOString() });
    }
  });
  ```
- **Broadcast Debouncing:** Debounce high-frequency broadcast events (such as typing indicators or form field edits) by 2–3 seconds rather than streaming every keystroke.

### 4.4 Realtime vs Polling Policy
- **Do NOT silently replace Realtime with polling** to save messages; polling can rapidly inflate Vercel Function or PostgREST request volume.
- Changing product behavior between Realtime and on-demand fetching requires **Class B approval**.

---

## 5. Edge Functions & Backend Access

- **Payload Shaping:** Edge Functions querying Supabase should filter and aggregate data before sending the HTTP response. Never fetch 10,000 rows from Postgres in an Edge Function and stream all 10,000 rows to the browser if the browser only needs 10 items.
- **Connection Pooling:** For direct Postgres connections (via `postgres.js`, `pg`, or ORMs like Prisma/Drizzle), use Supabase Supavisor connection pooling (port 6543 / transaction mode) rather than direct port 5432 to avoid exhausting connection slots.
- **Secret Protection:** Never move server-only logic or `service_role` operations to the frontend.

---

## 6. Auth Hygiene

- **Prevent Session Refresh Loops:** Setting up `supabase.auth.onAuthStateChange()` inside a component without proper unmount teardown or using a callback that causes immediate re-mounting triggers rapid session refresh loops that exhaust Auth quotas.
- **`getUser()` vs `getSession()` in SSR / Server Components:**
  - `getSession()` reads local cookies without contacting the Supabase Auth server (fast, zero network overhead, but unvalidated for mutations).
  - `getUser()` performs an authenticated network round-trip to the Supabase Auth server to validate the token.
  - In Server Components and SSR frameworks (Next.js, SvelteKit, Nuxt), invoke `getUser()` once at the root layout or middleware layer, then propagate user context down rather than calling `getUser()` in every nested subcomponent.
- **Preserve Security Boundaries:**
  - Never weaken RLS or modify authentication gates to save requests.
  - Never attempt to manipulate MAU (Monthly Active User) counting mechanisms.

---

## 7. Database Disk Size & Conservative Retention Policy

Free-tier Postgres disk storage is strictly bounded. Disk growth cannot easily be shrunk without full table vacuums.

### 7.1 Conservative Index Policy
- **Indexes Cost Physical Disk Space:** Every index (`CREATE INDEX ...`) consumes Postgres disk blocks and adds I/O overhead to every write operation.
- **Do NOT add indexes blindly** with the rationale that "indexes make queries fast." Only recommend an index if:
  1. An exact slow query pattern is identified in code (e.g. unindexed foreign keys in high-volume joins).
  2. The table contains substantial rows.
  3. The storage impact is acknowledged.
- **Identify Unused Indexes:** Inspect `pg_stat_user_indexes` where `idx_scan = 0` to find dead indexes that consume storage without aiding queries. Propose removal as **Class B**.

### 7.2 Unbounded Tables & Log Bloat
- Identify unbounded application tables: `audit_logs`, `webhook_events`, `activity_history`, `error_logs`, `sessions`.
- **Retention Strategy (Class B Proposal):** Propose time-to-live (TTL) retention policies for human approval, such as a scheduled `pg_cron` rolling retention job:
  ```sql
  -- Propose for user approval (Class B):
  DELETE FROM webhook_events WHERE created_at < NOW() - INTERVAL '30 days';
  ```
- **Prohibition on Automated Deletions:** Never automatically execute `DROP TABLE`, `TRUNCATE`, or `DELETE FROM` on database tables. Always present data cleanup and retention policies for explicit user authorization.

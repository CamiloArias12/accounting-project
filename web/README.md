# accounting-web

Frontend of **Accounting Project**. Started from
[OwlByTech/nextjs-boilerplate](https://github.com/OwlByTech/nextjs-boilerplate),
brought up to the latest versions.

## Stack

| Package    | Version                          |
| ---------- | -------------------------------- |
| Next.js    | 16.2.11 (App Router + Turbopack) |
| React      | 19.2.8                           |
| Tailwind   | 4.3.3                            |
| next-intl  | 4.13.4                           |
| TypeScript | 5.9.3                            |
| ESLint     | 9 (flat config)                  |

## Requirements

Docker. No Node needed on the machine.

## Development

Brought up from the monorepo root compose, not from here:

```bash
cd ..                 # repo root
cp .env.example .env
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000). The code is mounted into
the container, so Next reloads on edit.

## Commands

All run from the repo root, inside the container:

| Command                                     | Description    |
| ------------------------------------------- | -------------- |
| `docker compose exec web npm run lint`      | ESLint         |
| `docker compose exec web npm run typecheck` | `tsc --noEmit` |
| `docker compose logs -f web`                | Logs           |

After changing `package.json`, rebuild: `docker compose up -d --build web`.

## Layout

```
web/
├── messages/                     # Translations: en.json, es.json
└── src/
    ├── app/
    │   ├── layout.tsx            # Locale + NextIntlClientProvider
    │   ├── page.tsx              # Landing
    │   └── accounts/
    │       ├── page.tsx          # Server Component: fetches the tree
    │       ├── actions.ts        # Server Actions (async functions only)
    │       └── action-state.ts   # Their types and idle constants
    ├── components/
    │   ├── AccountsWorkspace.tsx # UI state (selection, search, panel)
    │   ├── AccountTree.tsx       # Collapsible tree
    │   ├── AccountForm.tsx       # Create, edit, delete, restore
    │   └── ImportForm.tsx        # Spreadsheet upload and summary
    ├── i18n/                     # next-intl config and request handler
    ├── lib/api.ts                # API client, `server-only`
    └── types/account.ts          # Shared types
```

## Architecture

Data is fetched in **Server Components** and every mutation goes through a
**Server Action**, which revalidates `/accounts` with `revalidatePath`.
Consequences:

- The browser never calls the API: no CORS to configure, no public URL to
  expose.
- The chart arrives rendered in the HTML, without waiting for hydration.
- Only what needs interaction ships to the client: expanding the tree,
  searching, switching panels.

Forms use `useActionState` for the action result and `useFormStatus` for the
pending state, so there is no hand-rolled loading flag.

### Things that bite

- **`actions.ts` may only export async functions.** Its types and the `IDLE`
  constants live in `action-state.ts`; exporting an object from a `"use server"`
  module fails the whole route.
- **Delete and restore share one action**, dispatched by a hidden `intent`
  field. They are two directions of the same toggle, and each flips the
  condition that would choose between two separate `useActionState`s — so the
  confirmation used to vanish the moment it was earned.
- **Post-delete navigation happens on the server**, inside the action. A deleted
  account leaves the default tree, unmounting the form; reacting to that from a
  client effect races the revalidation and loses.
- **`AccountForm` remounts via `key={code}`.** Resetting fields with a
  `useEffect` is an anti-pattern that React's lint rejects; remounting makes
  `defaultValue` enough.
- **The tree expands while searching.** A match buried under collapsed ancestors
  reads as no result at all.

## Internationalization

next-intl **without locale routing**: the language comes from a `locale` cookie
instead of a URL segment, so adding a language never changes a route. Default is
`en`; `messages/es.json` ships alongside it.

Some values stay Spanish on purpose — `Debito`, `Clase`, `Subcuenta` — because
they are the contract with the API and the source spreadsheet. Only the labels
shown to the user are translated, through the `nature` and `level` message
namespaces.

## Environment

`API_URL` (set in the compose file) points at the API through its Docker service
name. **Deliberately not `NEXT_PUBLIC_*`**: the browser never sees it, it is not
baked into the bundle, and changing it does not require rebuilding the image.

`allowedDevOrigins` in `next.config.mjs` matters more than it looks. The dev
server rejects cross-origin requests, which silently breaks hydration — the page
renders and forms still submit through progressive enhancement, but nothing
interactive works. It costs an afternoon to diagnose. Production is unaffected.

## Image

Multi-stage `Dockerfile` with two targets:

- **`dev`** — `next dev` with the code mounted.
- **`prod`** — serves Next's `standalone` output with `node server.js`, as the
  unprivileged `nextjs` user. Requires `output: "standalone"` in
  `next.config.mjs`.

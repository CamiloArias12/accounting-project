# accounting-web

Frontend de **Accounting Project**. Basado en el boilerplate de
[OwlByTech/nextjs-boilerplate](https://github.com/OwlByTech/nextjs-boilerplate),
actualizado a las últimas versiones.

## Stack

| Paquete    | Versión                          |
| ---------- | -------------------------------- |
| Next.js    | 16.2.11 (App Router + Turbopack) |
| React      | 19.2.8                           |
| Tailwind   | 4.3.3                            |
| TypeScript | 5.9.3                            |
| ESLint     | 9 (flat config)                  |

## Requisitos

Docker. No hace falta Node en la máquina.

## Desarrollo

Se levanta desde el compose de la raíz del monorepo, no desde aquí:

```bash
cd ..                 # raíz del repo
cp .env.example .env
docker compose up -d
```

Abre [http://localhost:3000](http://localhost:3000). El código va montado en el
contenedor, así que Next recarga al editar.

## Comandos

Todos se ejecutan desde la raíz del repo, dentro del contenedor:

| Comando                                       | Descripción     |
| --------------------------------------------- | --------------- |
| `docker compose exec web npm run lint`        | ESLint          |
| `docker compose exec web npm run typecheck`   | `tsc --noEmit`  |
| `docker compose logs -f web`                  | Logs            |

Tras cambiar `package.json` hay que reconstruir: `docker compose up -d --build web`.

## Variables de entorno

Se definen en el `.env` de la raíz, no aquí. `NEXT_PUBLIC_API_URL` se inyecta en
el bundle del navegador **al construir la imagen**, no en runtime: si la cambias,
reconstruye la web.

## Estructura

```
web/
├── src/app/            # App Router (layout, page, globals.css)
├── public/             # Assets estáticos
├── Dockerfile          # Targets dev y prod
├── eslint.config.mjs   # ESLint flat config
├── postcss.config.mjs  # Tailwind v4 vía @tailwindcss/postcss
└── tsconfig.json       # Alias @/* -> ./src/*
```

## Imagen

`Dockerfile` multi-stage con dos targets:

- **`dev`** — `next dev` con el código montado.
- **`prod`** — sirve el output `standalone` de Next con `node server.js`, como
  usuario `nextjs` sin privilegios. Requiere `output: "standalone"` en
  `next.config.mjs`.

## Notas de la migración

- **Tailwind 4** usa configuración en CSS, no `tailwind.config.ts`. El tema se
  define con `@theme` dentro de `src/app/globals.css`.
- **ESLint 9, no 10**: `eslint-config-next@16` declara `eslint >=9`, pero su
  `eslint-plugin-react` todavía llama a APIs que ESLint 10 eliminó
  (`context.getFilename`). Subir a 10 rompe el lint.
- **`next lint` fue eliminado** en Next 16; el script `lint` invoca `eslint`
  directamente.

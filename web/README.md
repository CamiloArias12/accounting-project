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

- Node.js 20.9+

## Desarrollo

```bash
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000).

## Scripts

| Comando             | Descripción                  |
| ------------------- | ---------------------------- |
| `npm run dev`       | Servidor de desarrollo       |
| `npm run build`     | Build de producción          |
| `npm run start`     | Sirve el build de producción |
| `npm run lint`      | ESLint                       |
| `npm run typecheck` | `tsc --noEmit`               |

## Variables de entorno

Copia `.env.example` a `.env.local` y ajusta los valores:

```bash
cp .env.example .env.local
```

## Estructura

```
web/
├── src/app/            # App Router (layout, page, globals.css)
├── public/             # Assets estáticos
├── eslint.config.mjs   # ESLint flat config
├── postcss.config.mjs  # Tailwind v4 vía @tailwindcss/postcss
└── tsconfig.json       # Alias @/* -> ./src/*
```

## Notas de la migración

- **Tailwind 4** usa configuración en CSS, no `tailwind.config.ts`. El tema se
  define con `@theme` dentro de `src/app/globals.css`.
- **ESLint 9, no 10**: `eslint-config-next@16` declara `eslint >=9`, pero su
  `eslint-plugin-react` todavía llama a APIs que ESLint 10 eliminó
  (`context.getFilename`). Subir a 10 rompe el lint.
- **`next lint` fue eliminado** en Next 16; el script `lint` invoca `eslint`
  directamente.

# BIS SAATHI — Frontend

Next.js (App Router) web app for **BIS SAATHI**, the agentic AI assistant for Indian Standards and BIS certification. It talks to the FastAPI backend in `../backend`. See `../backend/README.md` for backend setup and architecture.

## Stack

Next.js 16, React 19, TypeScript, Tailwind CSS v4, Lucide icons, Recharts, React Markdown, Vitest + Testing Library.

## Setup on Windows (PowerShell)

Requires Node.js 20 or newer, and the backend running on http://localhost:8000.

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local    # change NEXT_PUBLIC_API_URL if the backend runs elsewhere
npm run dev
```

Open http://localhost:3000, register an account and sign in. Register with an email listed in the backend's `ADMIN_EMAILS` to get the **Knowledge Base** page for uploading documents.

Linux / macOS: the same commands, using `cp .env.example .env.local`.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server on port 3000 |
| `npm run build` then `npm start` | Production build and server |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript check |
| `npm test` | Component tests (Vitest) |

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Dashboard: activity, intent distribution, recent chats and reports |
| `/assistant` | Multilingual AI chat with agent activity, citations and verification status |
| `/standards` | Search, view clauses and compare Indian Standards |
| `/certification` | Guided certification pathway for a product |
| `/laboratories` | Laboratory directory, filters, AI recommendation, CSV import (admin) |
| `/hallmarking` | Hallmarking and HUID guidance |
| `/consumer-help` | Consumer questions and official complaint resources |
| `/compliance` | Compliance check of product specifications (optional PDF) with checklist |
| `/reports` | Generate, view, download (PDF) and delete reports |
| `/notifications`, `/profile`, `/settings` | Notifications, account details, system health and local data |
| `/admin/documents` | Knowledge Base (admin): upload, index status, reindex, delete, certification schemes |

## Structure

```
src/
├── app/            Routes (one folder per page)
├── components/     ui/ primitives, layout/, chat/, and feature components
├── context/        AuthContext (JWT session)
├── hooks/          useAsync, useHashId, useRecentStandards
├── services/       Typed API clients (api.ts, auth, chat, reports, bis)
├── lib/            Navigation config
├── types/          Shared API types
└── utils/          Formatting and label helpers
```

The JWT is kept in `localStorage`; any 401 response signs the user out. Deep links such as `/standards#standard-12`, `/reports#report-5` and `/assistant#session-3` open the matching item.

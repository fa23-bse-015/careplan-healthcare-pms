# CarePlan | Healthcare Project Control

CarePlan is a responsive project-management application for planning and controlling the five-hospital healthcare software development project in the assignment. It manages project scope and delivery work; it is not a patient care or hospital operations system.

## What is included

- Project charter, project plan, team, milestones, and closure records.
- Requirement approval, hierarchical WBS, and change control. Pending change scope stays outside the approved baseline; an approval applies the linked requirement, work package, activity, cost, and schedule once.
- Dependency-based Monday-Friday schedule, delay forecast, milestones, and Gantt timeline.
- Activity estimates, actual expenditure, and task-based PV, EV, AC, CPI, and SPI with zero-denominator handling and warning thresholds.
- Defect tracking, quality inspections, likelihood-impact risk matrix, and linked risk responses.
- Dashboard, live reports, and CSV/JSON export.
- Password-gated server routes, a shared SQLite-compatible database, and a mobile-responsive installable PWA.

Sample data preserves the PKR 5,000,000 / 16-week original baseline and its approved combined change of PKR 800,000 / 3 weeks. The revised approved plan is PKR 5,800,000 / 19 weeks. The seed records use synthetic project data only.

## Requirements

- Node.js 22 or later and npm.
- For local development, no external database account is required; the app creates `data/smart_healthcare.sqlite3`.
- For Vercel production, attach a persistent Turso database and configure the environment variables below. A local SQLite file is not persistent Vercel storage.

## Run locally

From this folder in PowerShell:

```powershell
npm install
npm run db:setup
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Sign in with the value of `APP_ADMIN_PASSWORD` in your private `.env.local`. Change that local value before sharing the app beyond this machine. `npm run db:setup` is safe to rerun: it checks the schema and seeds only an empty database, preserving existing records.

Useful commands:

```powershell
npm run typecheck
npm run build
npm run start
```

The sample project's status date and schedule estimates are fixed sample data for this case study. The schedule uses Monday-Friday working days and links successors to predecessor finish dates. Planned progress is elapsed working days over each activity's planned duration. Overall progress is the activity-budget-weighted actual completion percentage.

## Install on a phone

Deploy the app over HTTPS, open its URL in Chrome or Safari on the phone, and choose the browser's **Install app** or **Add to Home Screen** action. It adjusts the navigation, forms, tables, and charts for phone screens. It is a network-connected PWA; it does not cache private project data for offline use and it is not a native Android/iOS package.

## Deploy to Vercel

1. Create a free Turso database (or use an existing persistent Turso database) and keep its URL and auth token private.
2. In the Vercel project settings, add these Production environment variables:

   - `TURSO_DATABASE_URL` — the Turso database URL.
   - `TURSO_AUTH_TOKEN` — the database token.
   - `APP_ADMIN_PASSWORD` — a unique password of at least 12 characters.
   - `SESSION_SECRET` — a random secret of at least 32 characters.

3. From this directory, authenticate the Vercel CLI and deploy:

   ```powershell
   npx vercel login
   npx vercel --prod
   ```

   On the first run, link this folder to the intended Vercel account/project and use this directory as the project root. Set the production variables before opening the workspace. The app creates the schema and inserts the synthetic sample project on first access to the database. You can initialize the database explicitly with `npm run db:setup` after adding Turso credentials to `.env.local`.

Do not use the demonstration password in a public deployment. Vercel environment variables must be set in the Vercel project; `.env.local` is ignored by Git and must not be uploaded. If Vercel is available only through an organization requiring paid services or a billing step, choose the free Turso option or configure the account yourself before deployment.

## Database and source layout

- `database/schema.sql` — SQLite-compatible schema, including checks and foreign keys.
- `database/seed-data.json` — reproducible synthetic case-study data.
- `scripts/setup-database.mjs` — schema setup and seed-only-if-empty script.
- `src/app/api` — authenticated state and command handlers.
- `src/lib` — persistence, validation, schedule, and earned-value calculations.
- `src/components` — responsive dashboards, project modules, and forms.

The browser never connects directly to the database. Mutations pass through server-side validation and the shared database, and the dashboard refreshes from that data source.

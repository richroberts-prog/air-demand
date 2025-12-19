---
applies_to: infrastructure
---

# Paraform Dashboard

A Next.js dashboard for viewing and filtering Paraform job roles with automated scoring.

## Features

- **Role Cards**: Display 698 active roles with score, tier, compensation, location
- **Tier Filtering**: Filter by HOT, WARM, LUKEWARM, COLD tiers
- **Search**: Search by title, company, or location
- **Expandable Details**: View full description, requirements, and intake transcripts
- **Real-time Data**: Connected to FastAPI backend on localhost:8123
- **Mobile Responsive**: Works on desktop, tablet, and mobile

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Open browser
http://localhost:3000
```

## Backend Requirements

The FastAPI backend must be running on localhost:8123:

```bash
# From project root
cd /home/richr/air
uv run uvicorn app.main:app --reload --port 8123
```

## Testing & Iteration

```bash
# Run UI tests
npm run test:ui

# Capture screenshots for iteration
npx playwright test tests/screenshot.spec.ts

# Run functional tests
npx playwright test tests/dashboard.spec.ts

# Interactive test mode
npx playwright test --ui

# Quick iteration script
./iterate.sh
```

## Project Structure

```
dashboard/
├── app/
│   ├── globals.css       # Global styles
│   ├── layout.tsx        # Root layout with QueryClient
│   └── page.tsx          # Main dashboard page
├── components/
│   └── RoleCard.tsx      # Role card component
├── lib/
│   ├── api.ts            # API client functions
│   └── types.ts          # TypeScript types
└── tests/
    ├── dashboard.spec.ts    # Functional tests
    └── screenshot.spec.ts   # Screenshot tests
```

## API Endpoints Used

- `GET /jobs/roles` - List roles with filtering
- `GET /jobs/roles/{id}` - Get single role
- `GET /jobs/stats` - Get role statistics
- `GET /jobs/scrape-runs` - Get recent scrape runs
- `POST /jobs/scrape` - Trigger manual scrape

## Development Workflow

1. **Start Services**
   ```bash
   # Terminal 1: Backend
   uv run uvicorn app.main:app --reload --port 8123

   # Terminal 2: Frontend
   npm run dev
   ```

2. **Iterate on UI**
   - Make changes to components
   - View changes instantly (hot reload)
   - Run `./iterate.sh` to capture screenshots
   - Review screenshots in `test-results/screenshots/`

3. **Test Changes**
   ```bash
   # Run all tests
   npm run test:ui

   # Or run interactively
   npx playwright test --ui
   ```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: TailwindCSS
- **Data Fetching**: TanStack Query
- **Icons**: Lucide React
- **Testing**: Playwright
- **Type Safety**: TypeScript

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run test:ui` - Run Playwright tests
- `./iterate.sh` - Capture screenshots and run tests

## Deployment

For local use only. Future deployment options:
- Vercel (recommended for Next.js)
- Netlify
- Docker container
- Digital Ocean Droplet

## Notes

- Dashboard connects to FastAPI backend via CORS (localhost:3000 allowed)
- 698 roles currently in database (mostly COLD tier)
- Tier filters default to HOT + WARM + LUKEWARM for relevance
- Mobile-responsive by default (TailwindCSS)
- Screenshots help iterate on UI without manual clicking

## Future Enhancements

- "New Since Last Visit" tracking (localStorage)
- Individual role detail pages (`/roles/{id}`)
- Company detail pages
- Intake transcript viewer with highlighting
- Dark mode
- User accounts and preferences
- Email digest preferences
- Slack/Discord integration

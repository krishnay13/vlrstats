# VLR Stats Frontend

A modern, animated frontend for Valorant esports statistics built with Next.js, shadcn/ui, and Framer Motion.

## Features

- 🎨 Modern UI with shadcn/ui components
- ✨ Smooth animations powered by Framer Motion
- 📱 Fully responsive design
- 🎯 Type-safe component system
- 🚀 Optimized performance with Next.js 14

## Tech Stack

- **Next.js 14** - React framework with App Router
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Beautiful, accessible component library
- **Framer Motion** - Production-ready motion library
- **Lucide React** - Beautiful icon library

## Getting Started

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── app/
│   ├── api/              # API routes
│   ├── components/       # App-specific components
│   ├── matches/          # Matches pages
│   ├── teams/            # Teams pages
│   ├── players/          # Players pages
│   ├── layout.js         # Root layout
│   ├── page.js           # Homepage
│   └── globals.css       # Global styles
├── components/
│   └── ui/               # shadcn/ui components
├── lib/
│   └── utils.js          # Utility functions
└── jsconfig.json         # Path aliases configuration
```

## Components

The project uses shadcn/ui components located in `components/ui/`:
- Button
- Card
- Badge
- Table
- Tabs
- Avatar

## Animations

All pages feature smooth animations using Framer Motion:
- Page transitions
- Staggered list animations
- Hover effects
- Loading states

## Styling

The project uses Tailwind CSS with a custom theme configuration. Color scheme and design tokens are defined in `app/globals.css`.

## API Routes

The frontend communicates with the database through Next.js API routes:
- `/api/matches` - Get all matches
- `/api/matches/[match_id]` - Get match details
- `/api/teams` - Get all teams
- `/api/teams/[team_id]` - Get team details
- `/api/players` - Get all players
- `/api/stats` - Get statistics summary

## Development

### Building for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Notes

- The database file (`valorant_esports.db`) should be in the `frontend/` directory
- All components are client components where needed (using 'use client' directive)
- Path aliases are configured in `jsconfig.json` for cleaner imports

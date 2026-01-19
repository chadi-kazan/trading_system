# Trading System Dashboard - Frontend

React + Vite + TypeScript dashboard for the Small-Cap Growth Trading System.

## Environment Configuration

The dashboard uses environment variables for configuration. These are loaded by Vite at build time.

### Environment Files

- **`.env`** - Default environment variables (committed to git)
- **`.env.local`** - Local overrides (gitignored, for development)
- **`.env.example`** - Template for required variables

### Available Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend FastAPI server URL | `http://localhost:8000` |

### Setup

1. **Development (default)**:
   The `.env` file is already configured for local development. No changes needed.

2. **Development (custom API URL)**:
   Create a `.env.local` file:
   ```bash
   VITE_API_BASE_URL=http://your-custom-api:8000
   ```

3. **Production Build**:
   Set environment variables before building:
   ```bash
   # Windows
   set VITE_API_BASE_URL=https://api.yourdomain.com
   npm run build

   # Linux/macOS
   VITE_API_BASE_URL=https://api.yourdomain.com npm run build
   ```

   Or create a `.env.production` file:
   ```
   VITE_API_BASE_URL=https://api.yourdomain.com
   ```

## Development

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## How Environment Variables Work

- All environment variables **must** be prefixed with `VITE_` to be exposed to the client
- Variables are embedded at **build time** (not runtime)
- Access variables in code: `import.meta.env.VITE_VARIABLE_NAME`
- The Vite config ([vite.config.ts](vite.config.ts:1)) automatically loads `.env` files
- Priority: `.env.local` > `.env` > defaults in code

## API Integration

The dashboard communicates with the FastAPI backend defined in `VITE_API_BASE_URL`. See [api.ts](src/api.ts:1) for all API endpoints.

## Project Structure

```
dashboard_web/
├── src/
│   ├── api.ts              # API client functions
│   ├── types.ts            # TypeScript type definitions
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # React entry point
│   ├── pages/              # Page components (Symbol, Watchlist, Momentum)
│   ├── components/         # Reusable UI components
│   └── hooks/              # Custom React hooks
├── public/                 # Static assets
├── .env                    # Default environment variables
├── .env.example            # Environment template
├── vite.config.ts          # Vite configuration
└── tailwind.config.ts      # Tailwind CSS configuration
```

## Notes

- The proxy configuration in `vite.config.ts` forwards `/api/*` requests to the backend during development
- Environment variables are **public** - never store secrets in `VITE_*` variables
- Changes to `.env` files require restarting the dev server

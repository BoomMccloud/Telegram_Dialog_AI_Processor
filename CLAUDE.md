# Telegram Dialog AI Processor Commands & Guidelines

## Build/Test/Lint Commands

### Backend (Python)
- Run server: `cd backend && uvicorn app.main:app --reload`
- Init DB: `cd backend && python scripts/init_db.py`
- Run migrations: `cd backend && python scripts/run_migrations.py`
- Run all tests: `cd backend && python -m pytest`
- Run single test: `cd backend && python -m pytest tests/test_file.py::test_function`

### Frontend (Next.js)
- Dev: `cd frontend && npm run dev`
- Build: `cd frontend && npm run build`
- Lint: `cd frontend && npm run lint`

### Frontend-UI (Vite/React/Electron)
- Dev: `cd frontend-ui && npm run dev`
- Electron Dev: `cd frontend-ui && npm run electron:dev`
- Build: `cd frontend-ui && npm run build`
- Lint: `cd frontend-ui && npm run lint`
- Package: `cd frontend-ui && npm run electron:package`

## Code Style Guidelines

- **Python**: Use type hints, PEP 8 style, async/await for I/O operations
- **TypeScript**: Use strict mode, prefer functional components with hooks
- **Error Handling**: Always catch exceptions appropriately and provide context
- **Imports**: Group imports (stdlib, third-party, local) with a blank line between
- **Naming**: snake_case for Python, camelCase for JS/TS (except components: PascalCase)
- **UI Components**: Use Tailwind in frontend, MUI in frontend-ui
- **Types**: Use TypeScript interfaces, Python type hints via typing module
- **Testing**: Follow test-driven development with pytest and async testing
# Lessons

- For website image paths, always use the correct relative path (e.g., 'images/filename.png') and ensure the images directory exists
- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- When using Jest, a test suite can fail even if all individual tests pass, typically due to issues in suite-level setup code or lifecycle hooks

# Scratchpad

In backend folder: 
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

APP_ENV=development JWT_SECRET_KEY=your-secure-key PYTHONPATH=. uvicorn app.main:app --reload --port 8000

database name is telegram_dialog_dev

Backend:
NODE_ENV=development npm run dev
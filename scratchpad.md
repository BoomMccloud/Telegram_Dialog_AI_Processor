# Lessons


# Scratchpad

APP_ENV=development JWT_SECRET_KEY=your-secure-key PYTHONPATH=. uvicorn app.main:app --reload --port 8000

database name is telegram_dialog_dev

telegramID: 6761933542
+6596456152

tree -L 4 -I 'sessions|tests|scripts|__*|token_logs|response_storage|message_storage|node_modules|frontend'

Next Steps:
- Convert application to live, use click on run, then it runs
- For each message, show the summary first, then allow user to see actual message
- Integrate MiniCPM for local inference



Files to Create


modify query_llm to use model_settings.json

frontend-ui/src/pages/Models/index.tsx
Add new endpoints for config management:

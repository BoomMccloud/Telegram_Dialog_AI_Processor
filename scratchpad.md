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

config/model_settings.json
JSON file storing user-configurable model settings
Contains active provider, model selections, and parameters
Does NOT contain API keys or sensitive information

modify query_llm to use model_settings.json

frontend-ui/src/pages/Models/index.tsx
Add new endpoints for config management:

 FastAPI app:
 @app.get("/api/config")
def get_model_config():
    """Get the current model configuration"""
    from app.services.llm_api import get_config
    return get_config()

@app.post("/api/config")
def update_model_config(config: dict):
    """Update the model configuration"""
    from app.services.llm_api import save_config
    save_config(config)
    return {"status": "success", "config": config}
# Project Overview

# Core Functionality

# Doc

# Current File Structure

backend
├── Dockerfile
├── alembic.ini
├── app
│   ├── api
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dependencies.py
│   │   ├── dialogs.py
│   │   ├── messages.py
│   │   └── responses.py
│   ├── core
│   │   ├── error_handlers.py
│   │   ├── exceptions.py
│   │   └── logging_config.py
│   ├── db
│   │   ├── README.md
│   │   ├── check_db.py
│   │   ├── database.py
│   │   ├── init_db.py
│   │   ├── migrations
│   │   ├── models
│   │   ├── schema_validator.py
│   │   ├── update_schema.py
│   │   └── utils.py
│   ├── main.py
│   ├── middleware
│   │   ├── __init__.py
│   │   └── session.py
│   ├── services
│   │   ├── auth.py
│   │   ├── background_tasks.py
│   │   ├── cleanup.py
│   │   ├── mock_telegram.py
│   │   ├── telegram.py
│   │   └── telegram_bot.py
│   └── utils
│       ├── __init__.py
│       └── logging.py
├── instructions.md
├── logs
├── requirements.txt
├── scripts
│   ├── __init__.py
│   ├── add_test_data.py
│   ├── drop_tables.py
│   ├── init_db.py
│   └── run_migrations.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_auth_dev.py
    ├── test_auth_endpoints.py
    ├── test_db_connection.py
    ├── test_error_handlers.py
    ├── test_exceptions.py
    ├── test_manual_db.py
    ├── test_session.py
    ├── test_session_management.py
    ├── test_session_middleware.py
    └── test_session_simple.py



# Data Model
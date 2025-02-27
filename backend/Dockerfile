FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create sessions directory
RUN mkdir -p sessions

# Create a script to initialize the database
RUN echo '#!/usr/bin/env python\n\
import asyncio\n\
import asyncpg\n\
import os\n\
import time\n\
\n\
async def init_db():\n\
    # Get database connection parameters from environment variables\n\
    user = os.getenv("POSTGRES_USER", "postgres")\n\
    password = os.getenv("POSTGRES_PASSWORD", "postgres")\n\
    database = os.getenv("POSTGRES_DB", "telegram_dialog")\n\
    host = os.getenv("POSTGRES_HOST", "postgres")\n\
    port = os.getenv("POSTGRES_PORT", "5432")\n\
    \n\
    # Wait for PostgreSQL to be ready\n\
    max_retries = 10\n\
    retry_interval = 5\n\
    \n\
    for i in range(max_retries):\n\
        try:\n\
            print(f"Attempting to connect to PostgreSQL (attempt {i+1}/{max_retries})...")\n\
            conn = await asyncpg.connect(\n\
                user=user,\n\
                password=password,\n\
                database=database,\n\
                host=host,\n\
                port=port\n\
            )\n\
            await conn.close()\n\
            print("Successfully connected to PostgreSQL")\n\
            break\n\
        except Exception as e:\n\
            print(f"Failed to connect to PostgreSQL: {str(e)}")\n\
            if i < max_retries - 1:\n\
                print(f"Retrying in {retry_interval} seconds...")\n\
                time.sleep(retry_interval)\n\
            else:\n\
                print("Max retries reached. Could not connect to PostgreSQL.")\n\
                raise\n\
    \n\
    # Create tables if they don\'t exist\n\
    try:\n\
        conn = await asyncpg.connect(\n\
            user=user,\n\
            password=password,\n\
            database=database,\n\
            host=host,\n\
            port=port\n\
        )\n\
        \n\
        # Check if tables exist\n\
        tables_exist = await conn.fetchval(\n\
            """\n\
            SELECT EXISTS (\n\
                SELECT FROM information_schema.tables \n\
                WHERE table_name = \'message_history\'\n\
            )\n\
            """\n\
        )\n\
        \n\
        if not tables_exist:\n\
            print("Creating database tables...")\n\
            \n\
            # Create message_history table\n\
            await conn.execute("""\n\
            CREATE TABLE IF NOT EXISTS message_history (\n\
                message_id UUID PRIMARY KEY,\n\
                dialog_id BIGINT NOT NULL,\n\
                telegram_message_id BIGINT NOT NULL,\n\
                dialog_name VARCHAR(255),\n\
                message_date TIMESTAMP WITH TIME ZONE,\n\
                sender_name VARCHAR(255),\n\
                message_text TEXT,\n\
                is_processed BOOLEAN DEFAULT false,\n\
                UNIQUE(dialog_id, telegram_message_id)\n\
            )\n\
            """)\n\
            \n\
            # Create processing_results table\n\
            await conn.execute("""\n\
            CREATE TABLE IF NOT EXISTS processing_results (\n\
                result_id UUID PRIMARY KEY,\n\
                message_id UUID NOT NULL,\n\
                processed_text TEXT,\n\
                response_text TEXT,\n\
                context_messages JSONB,\n\
                processing_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n\
                auto_reply_sent BOOLEAN DEFAULT false,\n\
                user_interaction_status VARCHAR(20) DEFAULT \'pending\',\n\
                edited_response_text TEXT,\n\
                interaction_date TIMESTAMP WITH TIME ZONE,\n\
                user_feedback TEXT,\n\
                FOREIGN KEY (message_id) REFERENCES message_history(message_id)\n\
            )\n\
            """)\n\
            \n\
            # Create authentication_data table\n\
            await conn.execute("""\n\
            CREATE TABLE IF NOT EXISTS authentication_data (\n\
                auth_id UUID PRIMARY KEY,\n\
                telegram_id BIGINT UNIQUE NOT NULL,\n\
                session_data JSONB,\n\
                encrypted_credentials BYTEA,\n\
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n\
                last_active_at TIMESTAMP WITH TIME ZONE,\n\
                is_active BOOLEAN DEFAULT true\n\
            )\n\
            """)\n\
            \n\
            # Create processing_queue table\n\
            await conn.execute("""\n\
            CREATE TABLE IF NOT EXISTS processing_queue (\n\
                queue_id UUID PRIMARY KEY,\n\
                message_id UUID NOT NULL,\n\
                priority INTEGER DEFAULT 0,\n\
                status VARCHAR(20) DEFAULT \'pending\',\n\
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n\
                started_at TIMESTAMP WITH TIME ZONE,\n\
                completed_at TIMESTAMP WITH TIME ZONE,\n\
                error_message TEXT,\n\
                FOREIGN KEY (message_id) REFERENCES message_history(message_id)\n\
            )\n\
            """)\n\
            \n\
            # Create auto_reply_rules table\n\
            await conn.execute("""\n\
            CREATE TABLE IF NOT EXISTS auto_reply_rules (\n\
                rule_id UUID PRIMARY KEY,\n\
                dialog_id BIGINT NOT NULL,\n\
                pattern TEXT,\n\
                response_template TEXT,\n\
                is_active BOOLEAN DEFAULT true,\n\
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n\
                last_triggered_at TIMESTAMP WITH TIME ZONE\n\
            )\n\
            """)\n\
            \n\
            # Create indexes\n\
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_message_history_date ON message_history (message_date DESC)")\n\
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_message_history_dialog ON message_history (dialog_id, message_date DESC)")\n\
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_queue_status ON processing_queue (status, priority DESC)")\n\
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_data_active ON authentication_data (is_active, last_active_at DESC)")\n\
            \n\
            print("Database tables created successfully")\n\
        else:\n\
            print("Database tables already exist")\n\
        \n\
        await conn.close()\n\
    except Exception as e:\n\
        print(f"Error initializing database: {str(e)}")\n\
        raise\n\
\n\
if __name__ == "__main__":\n\
    asyncio.run(init_db())\n\
' > app/db/init_db.py

# Make the script executable
RUN mkdir -p app/db
RUN mv app/db/init_db.py app/db/init_db.py
RUN chmod +x app/db/init_db.py

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
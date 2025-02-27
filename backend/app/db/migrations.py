import asyncio
import logging
import os
from typing import Dict, List, Set, Tuple

import asyncpg

from app.db.database import get_raw_connection

logger = logging.getLogger(__name__)

# Define the expected schema
EXPECTED_TABLES = {
    "message_history": {
        "columns": {
            "message_id": "uuid",
            "dialog_id": "bigint",
            "telegram_message_id": "bigint",
            "dialog_name": "character varying",
            "message_date": "timestamp with time zone",
            "sender_name": "character varying",
            "message_text": "text",
            "is_processed": "boolean",
            "embedding_vector": "vector",
            "message_type": "character varying"
        },
        "constraints": [
            "message_history_pkey",  # Primary key constraint
            "message_history_dialog_id_telegram_message_id_key"  # Unique constraint
        ],
        "indexes": [
            "message_history_pkey",
            "idx_message_history_date",
            "idx_message_history_dialog"
        ]
    },
    "processing_results": {
        "columns": {
            "result_id": "uuid",
            "message_id": "uuid",
            "processed_text": "text",
            "response_text": "text",
            "context_messages": "jsonb",
            "processing_date": "timestamp with time zone",
            "auto_reply_sent": "boolean",
            "user_interaction_status": "character varying",
            "edited_response_text": "text",
            "interaction_date": "timestamp with time zone",
            "user_feedback": "text"
        },
        "constraints": [
            "processing_results_pkey",  # Primary key constraint
            "processing_results_message_id_fkey"  # Foreign key constraint
        ],
        "indexes": [
            "processing_results_pkey"
        ]
    },
    "authentication_data": {
        "columns": {
            "auth_id": "uuid",
            "telegram_id": "bigint",
            "session_data": "jsonb",
            "encrypted_credentials": "bytea",
            "created_at": "timestamp with time zone",
            "last_active_at": "timestamp with time zone",
            "is_active": "boolean"
        },
        "constraints": [
            "authentication_data_pkey",  # Primary key constraint
            "authentication_data_telegram_id_key"  # Unique constraint
        ],
        "indexes": [
            "authentication_data_pkey",
            "idx_auth_data_active"
        ]
    },
    "processing_queue": {
        "columns": {
            "queue_id": "uuid",
            "message_id": "uuid",
            "priority": "integer",
            "status": "character varying",
            "created_at": "timestamp with time zone",
            "started_at": "timestamp with time zone",
            "completed_at": "timestamp with time zone",
            "error_message": "text"
        },
        "constraints": [
            "processing_queue_pkey",  # Primary key constraint
            "processing_queue_message_id_fkey"  # Foreign key constraint
        ],
        "indexes": [
            "processing_queue_pkey",
            "idx_processing_priority",
            "idx_processing_queue_status"
        ]
    },
    "auto_reply_rules": {
        "columns": {
            "rule_id": "uuid",
            "dialog_id": "bigint",
            "pattern": "text",
            "response_template": "text",
            "is_active": "boolean",
            "created_at": "timestamp with time zone",
            "last_triggered_at": "timestamp with time zone"
        },
        "constraints": [
            "auto_reply_rules_pkey"  # Primary key constraint
        ],
        "indexes": [
            "auto_reply_rules_pkey"
        ]
    },
    "user_selected_dialogs": {
        "columns": {
            "selection_id": "uuid",
            "user_id": "bigint",
            "dialog_id": "bigint",
            "dialog_name": "character varying",
            "is_active": "boolean",
            "processing_enabled": "boolean",
            "auto_reply_enabled": "boolean",
            "response_approval_required": "boolean",
            "priority": "integer",
            "created_at": "timestamp with time zone",
            "updated_at": "timestamp with time zone",
            "last_processed_at": "timestamp with time zone",
            "processing_settings": "jsonb"
        },
        "constraints": [
            "user_selected_dialogs_pkey",  # Primary key constraint
            "user_selected_dialogs_user_id_dialog_id_key"  # Unique constraint
        ],
        "indexes": [
            "user_selected_dialogs_pkey",
            "idx_user_selected_dialogs_user"
        ]
    }
}

# SQL statements for creating tables
CREATE_TABLE_STATEMENTS = {
    "message_history": """
    CREATE TABLE message_history (
        message_id UUID PRIMARY KEY,
        dialog_id BIGINT NOT NULL,
        telegram_message_id BIGINT NOT NULL,
        dialog_name VARCHAR(255),
        message_date TIMESTAMP WITH TIME ZONE,
        sender_name VARCHAR(255),
        message_text TEXT,
        is_processed BOOLEAN DEFAULT false,
        embedding_vector vector(1536),
        message_type VARCHAR(50),
        UNIQUE(dialog_id, telegram_message_id)
    )
    """,
    "processing_results": """
    CREATE TABLE processing_results (
        result_id UUID PRIMARY KEY,
        message_id UUID NOT NULL,
        processed_text TEXT,
        response_text TEXT,
        context_messages JSONB,
        processing_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        auto_reply_sent BOOLEAN DEFAULT false,
        user_interaction_status VARCHAR(20) DEFAULT 'pending' CHECK (user_interaction_status IN ('pending', 'used', 'rejected', 'edited')),
        edited_response_text TEXT,
        interaction_date TIMESTAMP WITH TIME ZONE,
        user_feedback TEXT,
        FOREIGN KEY (message_id) REFERENCES message_history(message_id)
    )
    """,
    "authentication_data": """
    CREATE TABLE authentication_data (
        auth_id UUID PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        session_data JSONB,
        encrypted_credentials BYTEA,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_active_at TIMESTAMP WITH TIME ZONE,
        is_active BOOLEAN DEFAULT true
    )
    """,
    "processing_queue": """
    CREATE TABLE processing_queue (
        queue_id UUID PRIMARY KEY,
        message_id UUID NOT NULL,
        priority INTEGER DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        error_message TEXT,
        FOREIGN KEY (message_id) REFERENCES message_history(message_id)
    )
    """,
    "auto_reply_rules": """
    CREATE TABLE auto_reply_rules (
        rule_id UUID PRIMARY KEY,
        dialog_id BIGINT NOT NULL,
        pattern TEXT,
        response_template TEXT,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_triggered_at TIMESTAMP WITH TIME ZONE
    )
    """,
    "user_selected_dialogs": """
    CREATE TABLE user_selected_dialogs (
        selection_id UUID PRIMARY KEY,
        user_id BIGINT NOT NULL,
        dialog_id BIGINT NOT NULL,
        dialog_name VARCHAR(255),
        is_active BOOLEAN DEFAULT true,
        processing_enabled BOOLEAN DEFAULT true,
        auto_reply_enabled BOOLEAN DEFAULT false,
        response_approval_required BOOLEAN DEFAULT true,
        priority INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_processed_at TIMESTAMP WITH TIME ZONE,
        processing_settings JSONB,
        UNIQUE(user_id, dialog_id)
    )
    """
}

# SQL statements for creating indexes
CREATE_INDEX_STATEMENTS = [
    "CREATE INDEX idx_message_history_date ON message_history (message_date DESC)",
    "CREATE INDEX idx_message_history_dialog ON message_history (dialog_id, message_date DESC)",
    "CREATE INDEX idx_processing_priority ON processing_queue USING BTREE (status, priority DESC, created_at)",
    "CREATE INDEX idx_processing_queue_status ON processing_queue (status, priority DESC)",
    "CREATE INDEX idx_auth_data_active ON authentication_data (is_active, last_active_at DESC)",
    "CREATE INDEX idx_user_selected_dialogs_user ON user_selected_dialogs (user_id, is_active, priority DESC)"
]

# SQL statements for creating extensions
CREATE_EXTENSION_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector"
]

async def get_current_schema(conn) -> Dict[str, Dict]:
    """
    Get the current database schema
    """
    # Get all tables
    tables = await conn.fetch("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    """)
    
    schema = {}
    
    for table_record in tables:
        table_name = table_record['table_name']
        schema[table_name] = {"columns": {}, "constraints": [], "indexes": []}
        
        # Get columns for this table
        columns = await conn.fetch("""
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        """, table_name)
        
        for column in columns:
            data_type = column['data_type']
            if data_type == 'USER-DEFINED':
                data_type = column['udt_name']
            schema[table_name]["columns"][column['column_name']] = data_type
        
        # Get constraints for this table
        constraints = await conn.fetch("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND table_name = $1
        """, table_name)
        
        for constraint in constraints:
            schema[table_name]["constraints"].append(constraint['constraint_name'])
        
        # Get indexes for this table
        indexes = await conn.fetch("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = $1
        """, table_name)
        
        for index in indexes:
            schema[table_name]["indexes"].append(index['indexname'])
    
    return schema

async def compare_schemas(current_schema: Dict, expected_schema: Dict) -> Tuple[bool, List[str]]:
    """
    Compare the current schema with the expected schema
    Returns a tuple of (is_valid, differences)
    """
    differences = []
    is_valid = True
    
    # Check for missing tables
    for table_name in expected_schema:
        if table_name not in current_schema:
            differences.append(f"Missing table: {table_name}")
            is_valid = False
            continue
        
        # Check for missing columns
        for column_name, expected_type in expected_schema[table_name]["columns"].items():
            if column_name not in current_schema[table_name]["columns"]:
                differences.append(f"Missing column: {table_name}.{column_name}")
                is_valid = False
            elif not current_schema[table_name]["columns"][column_name].startswith(expected_type):
                differences.append(f"Column type mismatch: {table_name}.{column_name} " +
                                  f"(expected: {expected_type}, got: {current_schema[table_name]['columns'][column_name]})")
                is_valid = False
        
        # Check for missing indexes (simplified check)
        expected_indexes = set(expected_schema[table_name]["indexes"])
        current_indexes = set(current_schema[table_name]["indexes"])
        missing_indexes = expected_indexes - current_indexes
        
        for idx in missing_indexes:
            differences.append(f"Missing index: {idx} on table {table_name}")
            is_valid = False
    
    return is_valid, differences

async def create_extension(conn, extension_name: str):
    """
    Create a PostgreSQL extension if it doesn't exist
    """
    try:
        await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension_name}")
        logger.info(f"Created extension: {extension_name}")
    except Exception as e:
        logger.error(f"Error creating extension {extension_name}: {str(e)}")
        raise

async def create_table(conn, table_name: str, create_statement: str):
    """
    Create a table if it doesn't exist
    """
    try:
        await conn.execute(create_statement)
        logger.info(f"Created table: {table_name}")
    except Exception as e:
        logger.error(f"Error creating table {table_name}: {str(e)}")
        raise

async def create_index(conn, index_statement: str):
    """
    Create an index
    """
    try:
        await conn.execute(index_statement)
        logger.info(f"Created index with statement: {index_statement}")
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        # Don't raise exception for index creation failures
        # as they might be due to the index already existing
        pass

async def add_column(conn, table_name: str, column_name: str, column_type: str):
    """
    Add a column to a table if it doesn't exist
    """
    try:
        # Check if column exists
        column_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = $1 
            AND column_name = $2
        )
        """, table_name, column_name)
        
        if not column_exists:
            await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            logger.info(f"Added column {column_name} to table {table_name}")
    except Exception as e:
        logger.error(f"Error adding column {column_name} to table {table_name}: {str(e)}")
        raise

async def check_and_migrate_database():
    """
    Check if the database schema matches the expected schema and perform migrations if needed
    """
    conn = None
    try:
        # Connect to the database
        conn = await get_raw_connection()
        
        # Create extensions first
        for extension_stmt in CREATE_EXTENSION_STATEMENTS:
            extension_name = extension_stmt.split()[-1]
            await create_extension(conn, extension_name)
        
        # Get the current schema
        current_schema = await get_current_schema(conn)
        
        # Compare with expected schema
        is_valid, differences = await compare_schemas(current_schema, EXPECTED_TABLES)
        
        if is_valid:
            logger.info("Database schema is valid")
            return True
        
        logger.warning("Database schema is invalid. Differences:")
        for diff in differences:
            logger.warning(f"  - {diff}")
        
        logger.info("Performing database migration...")
        
        # Create missing tables
        for table_name, create_statement in CREATE_TABLE_STATEMENTS.items():
            if table_name not in current_schema:
                await create_table(conn, table_name, create_statement)
        
        # Update current schema after creating tables
        current_schema = await get_current_schema(conn)
        
        # Add missing columns
        for table_name, table_def in EXPECTED_TABLES.items():
            if table_name in current_schema:
                for column_name, column_type in table_def["columns"].items():
                    if column_name not in current_schema[table_name]["columns"]:
                        # Convert SQLAlchemy-style types to PostgreSQL types
                        pg_type = column_type
                        if column_type == "vector":
                            pg_type = "vector(1536)"
                        
                        await add_column(conn, table_name, column_name, pg_type)
        
        # Create missing indexes
        for index_stmt in CREATE_INDEX_STATEMENTS:
            await create_index(conn, index_stmt)
        
        logger.info("Database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        return False
    finally:
        if conn:
            await conn.close()

async def wait_for_postgres(max_retries=10, retry_interval=5):
    """
    Wait for PostgreSQL to be ready
    """
    for i in range(max_retries):
        try:
            logger.info(f"Attempting to connect to PostgreSQL (attempt {i+1}/{max_retries})...")
            conn = await get_raw_connection()
            await conn.close()
            logger.info("Successfully connected to PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            if i < max_retries - 1:
                logger.info(f"Retrying in {retry_interval} seconds...")
                await asyncio.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Could not connect to PostgreSQL.")
                return False

async def init_db():
    """
    Initialize the database
    """
    # Wait for PostgreSQL to be ready
    if not await wait_for_postgres():
        raise Exception("Could not connect to PostgreSQL")
    
    # Check and migrate database
    if not await check_and_migrate_database():
        raise Exception("Database migration failed")
    
    logger.info("Database initialization completed successfully")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db()) 
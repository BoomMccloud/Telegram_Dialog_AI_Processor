"""
Migration script to move system_prompt data from user_selected_dialogs to user_selected_models
and clean up the user_selected_dialogs table by removing model_id and system_prompt columns
"""

import asyncio
import logging
from datetime import datetime

import asyncpg
from app.db.database import get_raw_connection

logger = logging.getLogger(__name__)

async def migrate_model_data():
    """
    Migrate model and system prompt data:
    1. For each user, get their model_id and system_prompt from a dialog
    2. Store it in user_selected_models
    3. Then drop the columns from user_selected_dialogs
    """
    conn = await get_raw_connection()
    try:
        logger.info("Starting model data migration...")
        
        # Get all users with selected dialogs
        users = await conn.fetch(
            """
            SELECT DISTINCT user_id 
            FROM user_selected_dialogs
            """
        )
        
        migrated_count = 0
        for user_row in users:
            user_id = user_row['user_id']
            logger.info(f"Migrating data for user {user_id}...")
            
            # Check if we already have a model for this user
            existing_model = await conn.fetchrow(
                """
                SELECT model_id FROM user_selected_models
                WHERE user_id = $1
                """,
                user_id
            )
            
            if existing_model:
                logger.info(f"User {user_id} already has a model, skipping...")
                continue
            
            # Get the most recent dialog with model_id and system_prompt
            # Note: We're checking if these columns exist first
            columns_exist = await conn.fetchrow(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_selected_dialogs'
                    AND column_name = 'model_id'
                ) AS model_id_exists,
                EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_selected_dialogs'
                    AND column_name = 'system_prompt'
                ) AS system_prompt_exists
                """
            )
            
            if not columns_exist['model_id_exists'] or not columns_exist['system_prompt_exists']:
                logger.info("Columns don't exist in user_selected_dialogs, skipping migration...")
                return
            
            dialog = await conn.fetchrow(
                """
                SELECT model_id, system_prompt 
                FROM user_selected_dialogs
                WHERE user_id = $1 AND model_id IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                user_id
            )
            
            if not dialog or not dialog['model_id']:
                logger.info(f"No model data found for user {user_id}, skipping...")
                continue
            
            # Get model name from the model_id
            model_name = "llama3"  # Default
            model_record = await conn.fetchrow(
                """
                SELECT model_name FROM user_selected_models
                WHERE model_id = $1
                """,
                dialog['model_id']
            )
            
            if model_record:
                model_name = model_record['model_name']
            
            # Insert into user_selected_models
            await conn.execute(
                """
                INSERT INTO user_selected_models (
                    model_id,
                    user_id, 
                    model_name,
                    is_default,
                    system_prompt,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                dialog['model_id'],
                user_id,
                model_name,
                True,
                dialog['system_prompt'],
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            migrated_count += 1
            logger.info(f"Migrated model data for user {user_id}")
        
        # Check if we need to drop columns
        if migrated_count > 0:
            logger.info(f"Successfully migrated data for {migrated_count} users")
            
            # Now check if we need to drop the columns
            try:
                await conn.execute("ALTER TABLE user_selected_dialogs DROP COLUMN IF EXISTS model_id")
                await conn.execute("ALTER TABLE user_selected_dialogs DROP COLUMN IF EXISTS system_prompt")
                logger.info("Successfully dropped model_id and system_prompt columns from user_selected_dialogs")
            except Exception as e:
                logger.error(f"Error dropping columns: {str(e)}")
        else:
            logger.info("No data migration needed")
        
        return True
    
    except Exception as e:
        logger.error(f"Error during model data migration: {str(e)}")
        return False
    
    finally:
        await conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate_model_data()) 
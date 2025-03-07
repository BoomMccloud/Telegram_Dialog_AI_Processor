#!/usr/bin/env python3
"""
Script to inject test data into the database.
Creates 2 test users with 4 dialogs each for testing purposes.
"""

import asyncio
import os
import sys
import random
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from app.db.models import User, Dialog, DialogType
from app.db.connection import get_db

async def add_test_data():
    """
    Add test users and dialogs to the database.
    Creates 2 users with 4 dialogs each.
    """
    async for db in get_db():
        try:
            # Create 2 test users
            users = []
            for i in range(1, 3):
                user = User(
                    telegram_id=random.randint(100000000, 999999999),  # Random 9-digit Telegram ID
                    username=f"test_user_{i}",
                    first_name=f"Test{i}",
                    last_name=f"User{i}"
                )
                db.add(user)
                users.append(user)
            
            # Commit to get the user IDs
            await db.commit()
            
            # Dialog types for variety
            dialog_types = [
                DialogType.PRIVATE, 
                DialogType.GROUP, 
                DialogType.CHANNEL, 
                DialogType.PRIVATE
            ]
            
            # Create 4 dialogs for each user
            for idx, user in enumerate(users):
                for j in range(1, 5):
                    dialog_type = dialog_types[j-1]
                    
                    # Generate appropriate name based on dialog type
                    if dialog_type == DialogType.PRIVATE:
                        name = f"Private Chat {j} for User {idx+1}"
                        telegram_dialog_id = str(random.randint(1000000000, 9999999999))
                    elif dialog_type == DialogType.GROUP:
                        name = f"Test Group {j} for User {idx+1}"
                        telegram_dialog_id = f"-{random.randint(1000000000, 9999999999)}"
                    else:  # CHANNEL
                        name = f"Test Channel {j} for User {idx+1}"
                        telegram_dialog_id = f"-100{random.randint(1000000000, 9999999999)}"
                    
                    dialog = Dialog(
                        telegram_dialog_id=telegram_dialog_id,
                        user_id=user.id,
                        name=name,
                        type=dialog_type,
                        is_processing_enabled=random.choice([True, False]),
                        auto_send_enabled=random.choice([True, False]),
                        last_message={
                            "text": f"This is the last message in {name}",
                            "date": datetime.now().isoformat()
                        },
                        unread_count=random.randint(0, 5)
                    )
                    db.add(dialog)
            
            # Commit all changes
            await db.commit()
            
            print("Successfully added 2 test users with 4 dialogs each to the database.")
            
            # Print some details about what was created
            print("\nCreated Users:")
            for user in users:
                print(f"  - {user.first_name} {user.last_name} (@{user.username}, Telegram ID: {user.telegram_id})")
            
            # Now retrieve and print the dialogs
            for user in users:
                print(f"\nDialogs for {user.first_name} {user.last_name}:")
                # Use SQLAlchemy's select statement instead of raw SQL
                query = select(Dialog).where(Dialog.user_id == user.id)
                result = await db.execute(query)
                dialogs = result.scalars().all()
                
                for dialog in dialogs:
                    print(f"  - {dialog.name} (Type: {dialog.type}, Processing: {dialog.is_processing_enabled})")
            
        except Exception as e:
            await db.rollback()
            print(f"Error adding test data: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_test_data()) 
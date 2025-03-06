#!/usr/bin/env python
"""
Populate the development database with test data for development and testing purposes.

This script inserts:
- Test users
- Test dialogs
- Test messages
- Test processing results

Usage:
    cd backend
    PYTHONPATH=. python scripts/populate_test_data.py
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
import json
import random

import asyncpg
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Import models
from app.models.user import User
from app.models.dialog import Dialog, Message
from app.models.processing import ProcessingResult, ProcessingStatus
from app.db.base import Base

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "telegram_dialog_dev"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}

# Construct database URL
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Create engine and session factory
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Test data
TEST_USERS = [
    {
        "telegram_id": 12345678,
        "username": "test_user_1",
        "first_name": "Test",
        "last_name": "User"
    },
    {
        "telegram_id": 87654321,
        "username": "test_user_2",
        "first_name": "Another",
        "last_name": "Tester"
    }
]

TEST_DIALOGS = [
    {
        "telegram_dialog_id": "123456789",
        "name": "Test Private Chat",
        "type": "private",
        "unread_count": 5,
        "last_message": {"text": "Hello there", "date": datetime.now().isoformat()},
    },
    {
        "telegram_dialog_id": "987654321",
        "name": "Test Group Chat",
        "type": "group",
        "unread_count": 10,
        "last_message": {"text": "Group message", "date": datetime.now().isoformat()},
    }
]

def generate_test_messages(dialogs, users):
    """Generate test messages for the given dialogs and users"""
    messages = []
    now = datetime.now()
    
    # Conversation in the private chat
    private_dialog = dialogs[0]
    messages.extend([
        {
            "telegram_message_id": "1001",
            "dialog_id": private_dialog.id,
            "text": "Hello, how are you?",
            "sender_id": str(users[0].telegram_id),
            "sender_name": f"{users[0].first_name} {users[0].last_name}",
            "date": now - timedelta(days=1, hours=2),
            "is_outgoing": False
        },
        {
            "telegram_message_id": "1002",
            "dialog_id": private_dialog.id,
            "text": "I'm doing well, thanks! What about that project we discussed?",
            "sender_id": str(users[1].telegram_id),
            "sender_name": f"{users[1].first_name} {users[1].last_name}",
            "date": now - timedelta(days=1, hours=1),
            "is_outgoing": True
        },
        {
            "telegram_message_id": "1003",
            "dialog_id": private_dialog.id,
            "text": "I've made some progress. The initial prototype is ready for review.",
            "sender_id": str(users[0].telegram_id),
            "sender_name": f"{users[0].first_name} {users[0].last_name}",
            "date": now - timedelta(hours=12),
            "is_outgoing": False
        },
        {
            "telegram_message_id": "1004",
            "dialog_id": private_dialog.id,
            "text": "Great! Can you send me the details?",
            "sender_id": str(users[1].telegram_id),
            "sender_name": f"{users[1].first_name} {users[1].last_name}",
            "date": now - timedelta(hours=11),
            "is_outgoing": True
        }
    ])
    
    # Conversation in the group chat
    group_dialog = dialogs[1]
    messages.extend([
        {
            "telegram_message_id": "2001",
            "dialog_id": group_dialog.id,
            "text": "Welcome everyone to the group!",
            "sender_id": str(users[0].telegram_id),
            "sender_name": f"{users[0].first_name} {users[0].last_name}",
            "date": now - timedelta(days=2),
            "is_outgoing": False
        },
        {
            "telegram_message_id": "2002",
            "dialog_id": group_dialog.id,
            "text": "Thanks for setting this up. Let's discuss the project timeline.",
            "sender_id": str(users[1].telegram_id),
            "sender_name": f"{users[1].first_name} {users[1].last_name}",
            "date": now - timedelta(days=1, hours=12),
            "is_outgoing": False
        },
        {
            "telegram_message_id": "2003",
            "dialog_id": group_dialog.id,
            "text": "I think we should aim to complete the first milestone by end of month.",
            "sender_id": str(users[0].telegram_id),
            "sender_name": f"{users[0].first_name} {users[0].last_name}",
            "date": now - timedelta(days=1, hours=10),
            "is_outgoing": False
        },
        {
            "telegram_message_id": "2004",
            "dialog_id": group_dialog.id,
            "text": "That's ambitious but doable if we prioritize properly.",
            "sender_id": str(users[1].telegram_id),
            "sender_name": f"{users[1].first_name} {users[1].last_name}",
            "date": now - timedelta(hours=8),
            "is_outgoing": False
        }
    ])
    
    return messages

def generate_processing_results(messages):
    """Generate processing results for some messages"""
    results = []
    statuses = [status for status in ProcessingStatus]
    
    # Only process a subset of messages
    for i, message in enumerate(messages[:5]):
        status = statuses[i % len(statuses)]
        
        # Create different results based on status
        if status == ProcessingStatus.COMPLETED:
            result = {
                "generated_text": f"AI response to: {message.text}",
                "confidence": random.uniform(0.7, 0.99),
                "processing_time_ms": random.randint(500, 3000),
                "model": "claude-3-sonnet"
            }
            error = None
            completed_at = datetime.now()
        elif status == ProcessingStatus.ERROR:
            result = None
            error = "Error processing message: model unavailable"
            completed_at = datetime.now()
        else:
            result = None
            error = None
            completed_at = None
        
        results.append({
            "message_id": message.id,
            "model_name": "claude-3-sonnet",
            "status": status,
            "result": result,
            "error": error,
            "completed_at": completed_at
        })
    
    return results

async def create_test_users(session):
    """Create test users in the database"""
    users = []
    for user_data in TEST_USERS:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.telegram_id == user_data["telegram_id"])
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"User with telegram_id {user_data['telegram_id']} already exists")
            users.append(existing_user)
        else:
            user = User(
                telegram_id=user_data["telegram_id"],
                username=user_data["username"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"]
            )
            session.add(user)
            users.append(user)
            print(f"Created user: {user_data['username']}")
    
    await session.commit()
    return users

async def create_test_dialogs(session, user):
    """Create test dialogs in the database"""
    dialogs = []
    for dialog_data in TEST_DIALOGS:
        # Check if dialog already exists
        result = await session.execute(
            select(Dialog).where(Dialog.telegram_dialog_id == dialog_data["telegram_dialog_id"])
        )
        existing_dialog = result.scalar_one_or_none()
        
        if existing_dialog:
            print(f"Dialog with telegram_dialog_id {dialog_data['telegram_dialog_id']} already exists")
            dialogs.append(existing_dialog)
        else:
            dialog = Dialog(
                id=uuid.uuid4(),
                telegram_dialog_id=dialog_data["telegram_dialog_id"],
                name=dialog_data["name"],
                type=dialog_data["type"],
                unread_count=dialog_data["unread_count"],
                last_message=dialog_data["last_message"]
            )
            session.add(dialog)
            dialogs.append(dialog)
            print(f"Created dialog: {dialog_data['name']}")
    
    await session.commit()
    return dialogs

async def create_test_messages(session, messages_data):
    """Create test messages in the database"""
    messages = []
    for message_data in messages_data:
        # Check if message already exists
        result = await session.execute(
            select(Message).where(
                (Message.telegram_message_id == message_data["telegram_message_id"]) &
                (Message.dialog_id == message_data["dialog_id"])
            )
        )
        existing_message = result.scalar_one_or_none()
        
        if existing_message:
            print(f"Message with telegram_message_id {message_data['telegram_message_id']} already exists")
            messages.append(existing_message)
        else:
            message = Message(
                id=uuid.uuid4(),
                telegram_message_id=message_data["telegram_message_id"],
                dialog_id=message_data["dialog_id"],
                text=message_data["text"],
                sender_id=message_data["sender_id"],
                sender_name=message_data["sender_name"],
                date=message_data["date"],
                is_outgoing=message_data["is_outgoing"]
            )
            session.add(message)
            messages.append(message)
            print(f"Created message: {message_data['text'][:20]}...")
    
    await session.commit()
    return messages

async def create_processing_results(session, results_data):
    """Create processing results in the database"""
    results = []
    for result_data in results_data:
        # Check if result already exists
        result_query = await session.execute(
            select(ProcessingResult).where(
                (ProcessingResult.message_id == result_data["message_id"]) &
                (ProcessingResult.model_name == result_data["model_name"])
            )
        )
        existing_result = result_query.scalar_one_or_none()
        
        if existing_result:
            print(f"Processing result for message {result_data['message_id']} already exists")
            results.append(existing_result)
        else:
            proc_result = ProcessingResult(
                id=uuid.uuid4(),
                message_id=result_data["message_id"],
                model_name=result_data["model_name"],
                status=result_data["status"],
                result=result_data["result"],
                error=result_data["error"],
                completed_at=result_data["completed_at"]
            )
            session.add(proc_result)
            results.append(proc_result)
            print(f"Created processing result for message {result_data['message_id']}")
    
    await session.commit()
    return results

async def populate_database():
    """Populate the database with test data"""
    print(f"Connecting to database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    try:
        # Use a single session for all operations
        async with async_session() as session:
            # Create test users
            print("\nCreating test users...")
            users = await create_test_users(session)
            
            # Create test dialogs
            print("\nCreating test dialogs...")
            dialogs = await create_test_dialogs(session, users[0])
            
            # Generate and create test messages
            print("\nCreating test messages...")
            messages_data = generate_test_messages(dialogs, users)
            messages = await create_test_messages(session, messages_data)
            
            # Generate and create processing results
            print("\nCreating test processing results...")
            results_data = generate_processing_results(messages)
            results = await create_processing_results(session, results_data)
            
            print("\nDatabase populated successfully!")
            
            # Print summary
            print("\nSummary:")
            print(f"- Created {len(users)} users")
            print(f"- Created {len(dialogs)} dialogs")
            print(f"- Created {len(messages)} messages")
            print(f"- Created {len(results)} processing results")
            
            # Print instructions for testing
            print("\nYou can now use this data for testing the background worker implementation.")
            print("Example dialog IDs:")
            for dialog in dialogs:
                print(f"- {dialog.name}: {dialog.id}")
            
    except Exception as e:
        print(f"Error populating database: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(populate_database()) 
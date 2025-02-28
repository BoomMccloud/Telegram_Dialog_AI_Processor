"""
Dependencies for FastAPI endpoints.
These are common functions and dependencies used across API routes.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

def get_mock_dialogs() -> List[Dict[str, Any]]:
    """
    Generate a list of mock dialog data for development and testing.
    
    Returns:
        List of mock dialog dictionaries
    """
    return [
        {
            "id": "123456789",
            "name": "Group Chat Example",
            "type": "group",
            "unread_count": 5,
            "last_message": {
                "id": "msg_1001",
                "text": "Hey everyone, what's the plan for tomorrow?",
                "sender": {"id": "87654321", "name": "Jane Doe"},
                "date": (datetime.utcnow() - timedelta(hours=2)).isoformat()
            }
        },
        {
            "id": "987654321",
            "name": "John Smith",
            "type": "private",
            "unread_count": 2,
            "last_message": {
                "id": "msg_1002",
                "text": "Can you send me the project files?",
                "sender": {"id": "987654321", "name": "John Smith"},
                "date": (datetime.utcnow() - timedelta(hours=5)).isoformat()
            }
        },
        {
            "id": "567891234",
            "name": "Work Announcements",
            "type": "channel",
            "unread_count": 0,
            "last_message": {
                "id": "msg_1003",
                "text": "New company policy regarding remote work",
                "sender": {"id": "admin", "name": "Admin"},
                "date": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
        },
        {
            "id": "456789123",
            "name": "Alice Johnson",
            "type": "private",
            "unread_count": 0,
            "last_message": {
                "id": "msg_1004",
                "text": "Thanks for your help!",
                "sender": {"id": "456789123", "name": "Alice Johnson"},
                "date": (datetime.utcnow() - timedelta(days=2)).isoformat()
            }
        },
        {
            "id": "321456789",
            "name": "Project X Team",
            "type": "group",
            "unread_count": 12,
            "last_message": {
                "id": "msg_1005",
                "text": "Meeting has been moved to 3PM",
                "sender": {"id": "12345678", "name": "Team Lead"},
                "date": (datetime.utcnow() - timedelta(hours=1)).isoformat()
            }
        }
    ]

def get_mock_messages() -> List[Dict[str, Any]]:
    """
    Generate a list of mock messages for development and testing.
    
    Returns:
        List of mock message dictionaries
    """
    mock_messages = []
    
    # Current time as baseline
    now = datetime.utcnow()
    
    # Sample messages for the group chat
    group_messages = [
        {"id": "g1", "text": "Hey everyone, what's the plan for tomorrow?", "sender_id": "87654321", "sender_name": "Jane Doe", "time_offset": 2},
        {"id": "g2", "text": "I'm free after 2PM", "sender_id": "12345678", "sender_name": "Team Lead", "time_offset": 1.9},
        {"id": "g3", "text": "How about we meet at the cafe at 3?", "sender_id": "87654321", "sender_name": "Jane Doe", "time_offset": 1.8},
        {"id": "g4", "text": "Sounds good to me", "sender_id": "56781234", "sender_name": "Bob Wilson", "time_offset": 1.7},
        {"id": "g5", "text": "I'll be there", "sender_id": "12345678", "sender_name": "Team Lead", "time_offset": 1.6},
    ]
    
    # Sample messages for the private chat
    private_messages = [
        {"id": "p1", "text": "Can you send me the project files?", "sender_id": "987654321", "sender_name": "John Smith", "time_offset": 5},
        {"id": "p2", "text": "Sure, I'll send them this evening", "sender_id": "12345678", "sender_name": "You", "time_offset": 4.9},
        {"id": "p3", "text": "Thanks!", "sender_id": "987654321", "sender_name": "John Smith", "time_offset": 4.8},
        {"id": "p4", "text": "No problem. Do you need anything else?", "sender_id": "12345678", "sender_name": "You", "time_offset": 4.7},
        {"id": "p5", "text": "That's all for now, thanks", "sender_id": "987654321", "sender_name": "John Smith", "time_offset": 4.6},
    ]
    
    # Convert to the expected format and add to the result list
    for msg in group_messages:
        mock_messages.append({
            "id": msg["id"],
            "dialog_id": "123456789",
            "dialog_name": "Group Chat Example",
            "dialog_type": "group",
            "text": msg["text"],
            "sender": {"id": msg["sender_id"], "name": msg["sender_name"]},
            "date": (now - timedelta(hours=msg["time_offset"])).isoformat(),
            "is_outgoing": msg["sender_id"] == "12345678"
        })
    
    for msg in private_messages:
        mock_messages.append({
            "id": msg["id"],
            "dialog_id": "987654321",
            "dialog_name": "John Smith",
            "dialog_type": "private",
            "text": msg["text"],
            "sender": {"id": msg["sender_id"], "name": msg["sender_name"]},
            "date": (now - timedelta(hours=msg["time_offset"])).isoformat(),
            "is_outgoing": msg["sender_id"] == "12345678"
        })
    
    # Sort by date (newest first)
    mock_messages.sort(key=lambda x: x["date"], reverse=True)
    
    return mock_messages 
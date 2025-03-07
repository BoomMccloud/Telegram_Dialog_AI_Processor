"""
Mock Telegram service for development and testing.
Provides mock dialogs, messages, and other Telegram-like functionality.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
from uuid import uuid4

class MockTelegramService:
    """
    Mock implementation of Telegram service for testing and development.
    Provides realistic-looking mock data for dialogs and messages.
    """
    
    def __init__(self, user_id: str = "test_user"):
        self.user_id = user_id
        self._mock_users = self._generate_mock_users()
        self._mock_groups = self._generate_mock_groups()
        self._mock_channels = self._generate_mock_channels()
        self._mock_messages = self._generate_mock_messages()
        
    def _generate_mock_users(self) -> List[Dict]:
        """Generate a list of mock users"""
        return [
            {"id": "user_1", "name": "Alice Johnson", "status": "online"},
            {"id": "user_2", "name": "Bob Smith", "status": "offline"},
            {"id": "user_3", "name": "Carol White", "status": "recently"},
            {"id": "user_4", "name": "David Brown", "status": "last_week"},
            {"id": "user_5", "name": "Eve Anderson", "status": "online"},
        ]
    
    def _generate_mock_groups(self) -> List[Dict]:
        """Generate a list of mock group chats"""
        return [
            {"id": "group_1", "name": "Project Alpha Team", "members_count": 15},
            {"id": "group_2", "name": "Family Group", "members_count": 6},
            {"id": "group_3", "name": "Tech Discussion", "members_count": 120},
            {"id": "group_4", "name": "Weekend Planners", "members_count": 8},
        ]
    
    def _generate_mock_channels(self) -> List[Dict]:
        """Generate a list of mock channels"""
        return [
            {"id": "channel_1", "name": "Company Announcements", "subscribers": 500},
            {"id": "channel_2", "name": "Tech News", "subscribers": 1200},
            {"id": "channel_3", "name": "Daily Updates", "subscribers": 300},
        ]
    
    def _generate_mock_messages(self) -> Dict[str, List[Dict]]:
        """Generate mock messages for each dialog"""
        messages = {}
        now = datetime.utcnow()
        
        # Generate messages for users
        for user in self._mock_users:
            messages[user["id"]] = [
                {
                    "id": f"msg_{uuid4().hex[:8]}",
                    "text": f"Hey, how are you?",
                    "sender": {"id": user["id"], "name": user["name"]},
                    "date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "is_read": bool(random.getrandbits(1))
                },
                {
                    "id": f"msg_{uuid4().hex[:8]}",
                    "text": "Let's meet tomorrow!",
                    "sender": {"id": self.user_id, "name": "You"},
                    "date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "is_read": True
                }
            ]
        
        # Generate messages for groups
        for group in self._mock_groups:
            messages[group["id"]] = [
                {
                    "id": f"msg_{uuid4().hex[:8]}",
                    "text": "Next meeting on Monday",
                    "sender": {"id": "user_1", "name": "Alice Johnson"},
                    "date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "is_read": bool(random.getrandbits(1))
                },
                {
                    "id": f"msg_{uuid4().hex[:8]}",
                    "text": "I'll prepare the presentation",
                    "sender": {"id": "user_2", "name": "Bob Smith"},
                    "date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "is_read": bool(random.getrandbits(1))
                }
            ]
        
        # Generate messages for channels
        for channel in self._mock_channels:
            messages[channel["id"]] = [
                {
                    "id": f"msg_{uuid4().hex[:8]}",
                    "text": "Important announcement!",
                    "sender": {"id": channel["id"], "name": channel["name"]},
                    "date": (now - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "is_read": bool(random.getrandbits(1))
                }
            ]
        
        return messages
    
    async def get_dialogs(self) -> List[Dict]:
        """
        Get mock dialogs list.
        
        Returns:
            List of dialog dictionaries containing dialog information
        """
        dialogs = []
        now = datetime.utcnow()
        
        # Add user chats
        for user in self._mock_users:
            messages = self._mock_messages.get(user["id"], [])
            last_message = messages[0] if messages else None
            dialogs.append({
                "id": user["id"],
                "name": user["name"],
                "type": "private",
                "unread_count": sum(1 for m in messages if not m.get("is_read", True)),
                "last_message": last_message,
                "is_user": True,
                "is_group": False,
                "is_channel": False
            })
        
        # Add group chats
        for group in self._mock_groups:
            messages = self._mock_messages.get(group["id"], [])
            last_message = messages[0] if messages else None
            dialogs.append({
                "id": group["id"],
                "name": group["name"],
                "type": "group",
                "unread_count": sum(1 for m in messages if not m.get("is_read", True)),
                "last_message": last_message,
                "is_user": False,
                "is_group": True,
                "is_channel": False
            })
        
        # Add channels
        for channel in self._mock_channels:
            messages = self._mock_messages.get(channel["id"], [])
            last_message = messages[0] if messages else None
            dialogs.append({
                "id": channel["id"],
                "name": channel["name"],
                "type": "channel",
                "unread_count": sum(1 for m in messages if not m.get("is_read", True)),
                "last_message": last_message,
                "is_user": False,
                "is_group": False,
                "is_channel": True
            })
        
        return dialogs
    
    async def get_messages(self, dialog_id: str, limit: int = 20) -> List[Dict]:
        """
        Get mock messages for a specific dialog.
        
        Args:
            dialog_id: The ID of the dialog to get messages for
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        messages = self._mock_messages.get(dialog_id, [])
        return messages[:limit]
    
    async def send_message(self, dialog_id: str, text: str) -> Dict:
        """
        Simulate sending a message.
        
        Args:
            dialog_id: The ID of the dialog to send the message to
            text: The message text
            
        Returns:
            Dictionary containing the sent message details
        """
        now = datetime.utcnow()
        message = {
            "id": f"msg_{uuid4().hex[:8]}",
            "text": text,
            "sender": {"id": self.user_id, "name": "You"},
            "date": now.isoformat(),
            "is_read": True
        }
        
        if dialog_id in self._mock_messages:
            self._mock_messages[dialog_id].insert(0, message)
        else:
            self._mock_messages[dialog_id] = [message]
        
        return message

# Create a singleton instance for the mock service
mock_telegram = MockTelegramService() 
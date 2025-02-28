#!/usr/bin/env python3
"""
Generate mock dialog data for development.

This script provides functions to generate mock dialogs for testing purposes.
It can be imported and used by other modules to get consistent mock data.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

# Sample names for mock data generation
FIRST_NAMES = ["John", "Emma", "Michael", "Sophia", "William", "Olivia", "James", "Ava", "Alexander", "Isabella", 
              "David", "Mia", "Joseph", "Charlotte", "Daniel", "Amelia", "Matthew", "Harper", "Andrew", "Evelyn"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", 
             "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"]

GROUP_WORDS = ["Team", "Project", "Group", "Club", "Community", "Network", "Association", "Society", "Circle", "Guild",
              "Enthusiasts", "Experts", "Professionals", "Developers", "Engineers", "Designers", "Managers", "Leaders"]

GROUP_TOPICS = ["Development", "Design", "Marketing", "Engineering", "Product", "Research", "Support", "Operations",
               "Analytics", "Strategy", "Communications", "Management", "Sales", "Finance", "HR", "Legal"]

# Fixed list of example dialogs for consistency across tests
EXAMPLE_DIALOGS = [
    {"id": -10000000, "name": "Laura", "is_group": False, "last_message": "Hi, how are you?", "unread_count": 3},
    {"id": -10000001, "name": "Development Team", "is_group": True, "last_message": "Meeting tomorrow at 10am", "unread_count": 15},
    {"id": -10000002, "name": "Mike Brown", "is_group": False, "last_message": "Did you see the latest report?", "unread_count": 0},
    {"id": -10000003, "name": "Product Design", "is_group": True, "last_message": "New mockups are ready", "unread_count": 7},
    {"id": -10000004, "name": "Jason", "is_group": False, "last_message": "Let's catch up next week", "unread_count": 1},
    {"id": -10000005, "name": "Marketing Group", "is_group": True, "last_message": "Campaign stats look great!", "unread_count": 5},
    {"id": -10000006, "name": "Sarah Johnson", "is_group": False, "last_message": "Thanks for your help", "unread_count": 0},
    {"id": -10000007, "name": "Engineering Team", "is_group": True, "last_message": "Who's handling the deployment?", "unread_count": 12},
    {"id": -10000008, "name": "David Wilson", "is_group": False, "last_message": "Check out this article", "unread_count": 2},
    {"id": -10000009, "name": "Operations", "is_group": True, "last_message": "Server maintenance tonight", "unread_count": 8}
]

def get_mock_dialogs() -> List[Dict]:
    """
    Get a consistent list of mock dialogs
    
    Returns:
        List of dialog dictionaries with id, name, is_group, last_message, and unread_count
    """
    return EXAMPLE_DIALOGS.copy()

def get_mock_dialog_by_id(dialog_id: int) -> Optional[Dict]:
    """
    Get a specific mock dialog by ID
    
    Args:
        dialog_id: The dialog ID to find
        
    Returns:
        The dialog dictionary or None if not found
    """
    for dialog in EXAMPLE_DIALOGS:
        if dialog["id"] == dialog_id:
            return dialog.copy()
    return None

def generate_mock_messages(dialog_id: int, count: int = 20) -> List[Dict]:
    """
    Generate mock messages for a specific dialog
    
    Args:
        dialog_id: The dialog ID to generate messages for
        count: Number of messages to generate
        
    Returns:
        List of message dictionaries
    """
    dialog = get_mock_dialog_by_id(dialog_id)
    if not dialog:
        return []
    
    messages = []
    now = datetime.utcnow()
    
    # Get sender name based on dialog
    if dialog["is_group"]:
        senders = [f"{first} {last}" for first, last in zip(random.sample(FIRST_NAMES, 5), random.sample(LAST_NAMES, 5))]
        senders.append("You")
    else:
        senders = [dialog["name"], "You"]
    
    # Generate message texts based on dialog type
    if dialog["is_group"]:
        topics = ["project", "meeting", "deadline", "update", "issue", "solution", "plan", "review", "feedback", "question"]
        text_templates = [
            "Let's discuss the {topic} in our next meeting.",
            "Has anyone looked at the {topic} yet?",
            "I need help with the {topic}, who can assist?",
            "Great progress on the {topic} everyone!",
            "The {topic} needs more attention before Friday.",
            "We should prioritize the {topic} this week.",
            "Any updates on the {topic}?",
            "I've updated the {topic} documentation.",
            "Who's responsible for the {topic}?",
            "Can we schedule a call about the {topic}?"
        ]
    else:
        topics = ["idea", "plan", "question", "update", "request", "proposal", "recommendation", "consideration", "thought", "suggestion"]
        text_templates = [
            "I had an {topic} I wanted to share with you.",
            "What do you think about this {topic}?",
            "Can you help me with a {topic}?",
            "Let me know what you think of this {topic}.",
            "I'd like your feedback on my {topic}.",
            "Have you considered this {topic}?",
            "I'm working on a new {topic}.",
            "Do you have time to discuss a {topic}?",
            "I wanted to follow up on our {topic}.",
            "Just checking in about the {topic}."
        ]
    
    # Generate messages
    for i in range(count):
        sender = random.choice(senders)
        topic = random.choice(topics)
        text_template = random.choice(text_templates)
        text = text_template.replace("{topic}", topic)
        
        # Add some random words to make messages more varied
        if random.random() > 0.5:
            extra_words = ["Also", "By the way", "Additionally", "Oh", "And", "Plus", "Remember", "Don't forget", "FYI", "Just so you know"]
            extra_text = random.choice(extra_words) + ", " + random.choice(text_templates).replace("{topic}", random.choice(topics)).lower()
            text += " " + extra_text
        
        messages.append({
            "id": random.randint(1000000, 9999999),
            "dialog_id": dialog_id,
            "date": (now - timedelta(minutes=i*10)).isoformat(),
            "sender": sender,
            "text": text,
            "is_read": i > 5,  # First 5 messages are unread
            "is_outgoing": sender == "You"
        })
    
    # Sort messages by date (newest first)
    messages.sort(key=lambda x: x["date"], reverse=True)
    return messages

def save_mock_data():
    """Save mock dialogs and messages to files for testing"""
    dialogs = get_mock_dialogs()
    
    # Generate sample messages for each dialog
    all_messages = []
    for dialog in dialogs:
        messages = generate_mock_messages(dialog["id"], count=20)
        all_messages.extend(messages)
    
    # Save to files
    output_dir = Path(__file__).resolve().parent
    
    with open(output_dir / "mock_dialogs.json", "w") as f:
        json.dump(dialogs, f, indent=2)
    
    with open(output_dir / "mock_messages.json", "w") as f:
        json.dump(all_messages, f, indent=2)
    
    print(f"Saved mock data to:")
    print(f"  {output_dir / 'mock_dialogs.json'}")
    print(f"  {output_dir / 'mock_messages.json'}")

if __name__ == "__main__":
    # If run directly, save mock data to files
    save_mock_data() 
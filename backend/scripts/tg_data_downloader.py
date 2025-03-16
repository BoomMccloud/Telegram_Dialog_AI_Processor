import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

load_dotenv()

import sys
print(sys.executable)


class TelegramDataDownloader:
    def __init__(self):
        print("Initializing TelegramProcessor instance...")
        self.client = TelegramClient(
            'session_name',
            int(os.getenv('API_ID')),
            os.getenv('API_HASH')
        )
        print("TelegramProcessor instance initialized.")

    async def start(self):
        print("Starting Telegram client...")
        await self.client.start()
        print("Telegram client started successfully.")
        all_responses = await self.process_all_messages()
        
        self.call_local_data_processor()  

    async def check_mentions(self, message):
        """Check if the message mentions the target keyword"""
        text = message.text if message.text else ""
        target_keyword = os.getenv('TARGET_KEYWORD', '').lower()
        if target_keyword in text.lower():
            print(f"The target keyword was found in message ID {message.id}.")
            return True
        print(f"The target keyword was not found in message ID {message.id}.")
        return False

    async def process_all_messages(self):
        print("Getting all dialogs...")
        dialogs = await self.client.get_dialogs()
        print(f"Successfully obtained {len(dialogs)} dialogs.")

        relevant_messages = []
        now = datetime.now(timezone.utc)
        twenty_four_hours_ago = now - timedelta(hours=24)
        # Define data_path
        data_path = Path(os.getenv('DATA_DIR', '.'))

        # Process group chats
        group_dialogs = [dialog for dialog in dialogs if not dialog.is_user]
        for dialog in group_dialogs:
            if dialog.unread_count > 0:
                async for message in self.client.iter_messages(dialog.id, limit=dialog.unread_count):
                    message_date = message.date.replace(tzinfo=timezone.utc) if message.date.tzinfo is None else message.date
                    if message_date >= twenty_four_hours_ago and await self.check_mentions(message):
                        relevant_messages.append((dialog.name, message))

        # Process private messages
        private_dialogs = [dialog for dialog in dialogs if dialog.is_user]
        for dialog in private_dialogs:
            if dialog.unread_count > 0:
                async for message in self.client.iter_messages(dialog.id, limit=dialog.unread_count):
                    message_date = message.date.replace(tzinfo=timezone.utc) if message.date.tzinfo is None else message.date
                    if message_date >= twenty_four_hours_ago:
                        relevant_messages.append((dialog.name, message))

        # Save unread messages and the last 20 historical messages for each dialog
        dialog_messages = {}
        for dialog_name, message in relevant_messages:
            if dialog_name not in dialog_messages:
                dialog_messages[dialog_name] = []
            dialog_messages[dialog_name].append(message)

        # Get the last 20 historical messages for each dialog
        dialog_history = {}
        for dialog_name, _ in relevant_messages:
            # Find the corresponding dialog object
            dialog_obj = next((dialog for dialog in dialogs if dialog.name == dialog_name), None)
            if dialog_obj:
                history_messages = []
                async for msg in self.client.iter_messages(dialog_obj.id, limit=20):
                    history_messages.append(msg)
                dialog_history[dialog_name] = history_messages

        # Merge unread messages and historical messages, and remove duplicates
        for dialog_name, messages in dialog_messages.items():
            if dialog_name in dialog_history:
                # First, store the message IDs in a set for deduplication
                message_ids = set(msg.id for msg in messages)
                for msg in dialog_history[dialog_name]:
                    if msg.id not in message_ids:
                        messages.append(msg)
                        message_ids.add(msg.id)

        # Get the last 20 messages for each dialog
        recent_messages = {}
        for dialog_name, messages in dialog_messages.items():
            recent_messages[dialog_name] = sorted(messages, key=lambda m: m.date, reverse=True)[:20]

        # Export the last 20 messages for each dialog to telegram_data.json
        if recent_messages:
            export_data = []
            for dialog_name, messages in recent_messages.items():
                dialog_data = {
                    "dialog_name": dialog_name,
                    "messages": []
                }
                for message in messages:
                    # Add sender information
                    sender_name = message.sender.first_name if message.sender else "Unknown"
                    message_data = {
                        "message_id": message.id,
                        "sender_name": sender_name,
                        "message_text": message.text,
                        "message_date": str(message.date)
                    }
                    dialog_data["messages"].append(message_data)
                export_data.append(dialog_data)
            print("Starting to process dialog data...")
            data_path.mkdir(parents=True, exist_ok=True)
            with open(data_path / 'telegram_data.json', 'w', encoding='utf-8') as file:
                json.dump(export_data, file, ensure_ascii=False, indent=4)
            print("The last 20 messages of each dialog have been exported to telegram_data.json")
        return recent_messages

    def call_local_data_processor(self):
        import subprocess
        import os

        # Define the full path of the script
        script_name = os.getenv('PROCESSOR_SCRIPT_NAME', 'reply_only_llama3.2.py')
        script_path = Path(os.getenv('DATA_DIR', '.')) / script_name
        if not script_path.exists():
            print(f"❌ The target script does not exist: {script_path}")
            return

        # Construct the complete environment variables
        my_env = os.environ.copy()
        python_path = os.getenv('PYTHON_PATH', 'python3')
        try:
            if not script_path.exists():
                print(f"The script file {script_path} does not exist")
                return
            print(f"Calling {script_name}...")
            result = subprocess.run([python_path, str(script_path)], check=True, env=my_env, cwd=script_path.parent,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"{script_name} called successfully")
            print("Standard output:", result.stdout.decode('utf-8'))  # Decode the output
            print("Standard error:", result.stderr.decode('utf-8'))  # Decode the error information
        except subprocess.CalledProcessError as e:
            print(f"An error occurred when calling {script_name}: {e}")
            print("Standard output:", e.stdout.decode('utf-8') if e.stdout else None)  # Decode the output
            print("Standard error:", e.stderr.decode('utf-8') if e.stderr else None)  # Decode the error information


if __name__ == '__main__':
    print("The program starts running...")
    downloader = TelegramDataDownloader()
    asyncio.run(downloader.start())
    print("The program has finished running.")

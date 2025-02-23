import os
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict
from llama_cpp import Llama

import sys
print(sys.executable)

try:
    from llama_cpp import Llama
except ImportError:
    print("Unable to import llama_cpp library. Please check if it is installed correctly.")
    exit(1)

# --------------------------
# Configuration Constants
# --------------------------
MODEL_CONFIG = {
    "model_path": "",  # You need to fill in the correct model path
    "n_gpu_layers": -1,  # Automatically detect the optimal number of layers
    "n_ctx": 4096, 
    "chat_format": "llama-3",  # Must specify the correct format
    "verbose": False
}

GENERATION_PARAMS = {
    "max_tokens": 256,
    "temperature": 0.8, 
    "top_p": 0.95,
    "top_k": 50,
    "stop": ["<|eot_id|>", "\n## End", "```end"],
    "repeat_penalty": 1.1,
    "mirostat_tau": 5
}


# --------------------------
# Core Functional Class
# --------------------------
class DialogProcessor:
    def __init__(self, iam: str = "Laura"):
        self.iam = iam
        self.llm = self._init_model()

    def _init_model(self):
        """Initialize the language model"""
        try:
            return Llama(**MODEL_CONFIG)
        except Exception as e:
            raise RuntimeError(f"Model initialization failed: {str(e)}")

    def process(self, data: List[Dict]) -> List[Tuple]:
        """Process all dialog data"""
        print("Start processing dialog data...")
        return [self._process_single_dialog(dialog) for dialog in data if self._validate_dialog(dialog)]

    def _validate_dialog(self, dialog: Dict) -> bool:
        """Validate the validity of a single dialog"""
        if not isinstance(dialog, dict):
            print(f"⚠️ Illegal dialog format: {type(dialog)}")
            return False

        if not all(key in dialog for key in ['dialog_name', 'messages']):
            print(f"🔍 Missing dialog fields: {dialog.keys()}")
            return False

        return True

    def _process_single_dialog(self, dialog: Dict) -> Tuple:
        """Process a single dialog"""
        messages = self._preprocess_messages(dialog.get('messages', []))
        if not messages:
            return ("", "", "[No valid messages]")

        context_messages = messages[-5:]
        prompt = self._build_prompt(context_messages)

        try:
            response = self._generate_response(prompt)
            return (
                dialog.get("dialog_name", ""),
                context_messages[-1].get('message_date', ""),
                self._post_process(response)
            )
        except Exception as e:
            print(f"Generation failed: {str(e)}")
            return (dialog.get("dialog_name", ""), "", "[Generation error]")

    def _preprocess_messages(self, messages: List[Dict]) -> List[Dict]:
        """Preprocess message data"""
        valid_messages = []
        for m in messages:
            if not self._is_valid_message(m):
                continue

            # Clean the message content
            m['message_text'] = self._clean_text(m.get('message_text', ''))
            valid_messages.append(m)

        try:
            return sorted(valid_messages, key=lambda x: x['message_date'])
        except KeyError:
            return []

    def _is_valid_message(self, msg: Dict) -> bool:
        """Validate the validity of a message"""
        if not isinstance(msg, dict):
            return False

        required_keys = ['message_date', 'sender_name', 'message_text']
        if any(key not in msg for key in required_keys):
            return False

        text = msg.get('message_text', '')
        return isinstance(text, str) and len(text.strip()) >= 1

    def _clean_text(self, text: str) -> str:
        """Text cleaning process"""
        # Uniformly handle null values
        text = str(text) if text is not None else ""

        # Safety filtering
        text = re.sub(r'[^\x00-\x7F\u4e00-\u9fa5]', '', text)  # Basic character set
        text = re.sub(r'@\w+\b', '[User mention]', text)  # Fuzzify mentions
        text = re.sub(r'http\S+', '[Link]', text)  # Replace links
        return text[:500].strip()

    def _build_prompt(self, messages: List[Dict]) -> str:
        system_directives = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    # Role Definition
    You are [xxxx], respond to [xxxxx] with:

    # Critical Directives
    ✦ MUST analyze ALL historical messages
    ✦ ALWAYS prioritize context-based responses
    ✦ If context is unclear: Ask SPECIFIC follow-up questions
    ✦ Minimum action verbs per response: 1 (e.g. "confirm", "schedule", "review")

    # Tone Guidelines
    ✦ Professional yet approachable
    ✦ Balanced formality (avoid both stiff and casual extremes)
    ✦ Show appreciation when appropriate
    ✦ Use concise but complete sentences

    # Response Strategy
    1. Extract key entities (names/dates/actions)
    2. Mirror the partner's communication style
    3. Propose concrete next steps when possible

    # Response Template Examples
    [Positive] "Confirmed, the materials will reach you by EOD Wednesday. Appreciate your patience."
    [Neutral] "Let's schedule a brief sync tomorrow AM. Please share your availability."
    [Urgent] "Need the signed docs by 3PM CST today. Will follow up via email."

    # Strict Prohibitions
    1. Never use emoticons or slang
    2. Avoid jargon like "leverage" or "synergy"
    3. Never make promises beyond authority

    Current context: "{messages[-1]['message_text'][:130]}"<|eot_id|>"""

        message_history = []
        for m in messages[-5:]:
            role_type = "user" if m['sender_name'] != self.iam else "assistant"
            message_block = [
                f"<|start_header_id|>{role_type}<|end_header_id|>",
                m['message_text'][:200].strip(),
                "<|eot_id|>"
            ]
            message_history.append("\n".join(message_block))

        return (
            system_directives +
            "\n".join(message_history) +
            "\n<|start_header_id|>assistant<|end_header_id|>\n"
        )

    def _generate_response(self, prompt: str) -> str:
        """Call the model to generate a reply"""
        result = self.llm.create_completion(prompt=prompt, **GENERATION_PARAMS)
        return result['choices'][0]['text'].strip()

    def _post_process(self, text: str) -> str:
        """Safety filtering strategy"""
        # Basic cleaning
        text = re.sub(r'\s+', ' ', text).strip()

        # Keep the minimum response
        if len(text.split()) < 3:
            return "Please provide more details."

        # Filter only obviously invalid content
        invalid_patterns = [
            r'\[\w+\]',  # Filter marked content
            r'\.{3,}',  # Delete ellipsis
            r'\b(n/a|undefined)\b'
        ]
        for p in invalid_patterns:
            text = re.sub(p, '', text)

        return text[:250].strip() or "Awaiting your further instructions."


# --------------------------
# Utility Functions
# --------------------------
def load_data(file_path: str) -> List[Dict]:
    """Load JSON data"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Data loading failed: {str(e)}")
        return []


# --------------------------
# Main Program
# --------------------------
if __name__ == '__main__':
    print("🚀 Dialog processing system started")

    processor = DialogProcessor()
    data_path = ""  # You need to fill in the correct data file path
    if not data_path:
        print("❌ Data file path is not provided")
        exit(1)

    raw_data = load_data(data_path)
    results = processor.process(raw_data)

    print("\n📝 Processing results:")
    for name, _, reply in results:
        print(f"\n▨ {name}")
        print("-" * 50)
        print(f"{reply}\n")

<ProjectDoc>
    <ProjectOverview>
        <Description>
            This document outlines a multi-step plan to implement a simple background worker that fetches unread Telegram messages,
            generates AI-based responses, and stores them for user review. The approach focuses on a standalone worker process
            with minimal complexity, utilizing existing database tables for data storage. Future iterations will integrate with
            the background_tasks infrastructure for more advanced features.
        </Description>
    </ProjectOverview>

    <!-- ========================================================= -->
    <!-- TIMELINE & TASK BREAKDOWN                                -->
    <!-- ========================================================= -->
    <TimelineAndTaskBreakdown>
        <Phase name="Phase 1: Worker Skeleton & Basic Telegram Fetch">
            <EstimatedDuration>1-2 days</EstimatedDuration>
            <Tasks>
                <Task>
                    <Name>Create worker.py file</Name>
                    <Details>
                        - Implement the basic scheduling function (e.g., via APScheduler or Celery)
                        - Ensure single concurrency (using a global or DB-based lock)
                    </Details>
                </Task>
                <Task>
                    <Name>Database and Telegram integration</Name>
                    <Details>
                        - Fetch the user-selected dialogs from the DB
                        - Implement a function to call telegram.py's fetch_unread_messages for each dialog
                        - Implement a retry mechanism (3 attempts) for network/API failures
                    </Details>
                </Task>
                <Task>
                    <Name>Basic Logging</Name>
                    <Details>
                        - Log successes/failures at each step
                        - Create placeholders for storing partial or full failure status
                    </Details>
                </Task>
                <Deliverable>
                    A functioning worker that runs every 30 minutes, pulls unread messages,
                    and logs them. No AI suggestions yet.
                </Deliverable>
            </Tasks>
        </Phase>

        <Phase name="Phase 2: AI Integration & Context Building">
            <EstimatedDuration>2-3 days</EstimatedDuration>
            <Tasks>
                <Task>
                    <Name>Context Retrieval</Name>
                    <Details>
                        - Extend worker.py to fetch the last 20 messages for context from telegram.py
                        - Combine unread messages with context messages
                        - Ensure minimal local storage (store context only in memory)
                    </Details>
                </Task>
                <Task>
                    <Name>AI Suggestion Generation</Name>
                    <Details>
                        - Integrate calls to llm_api.py in the worker
                        - Implement the retry logic (3 attempts) for AI generation failures
                        - Store suggestion text in the DB (e.g., processed_responses table with status)
                    </Details>
                </Task>
                <Task>
                    <Name>Partial Success Handling</Name>
                    <Details>
                        - Continue processing other dialogs even if one fails
                        - Only log a "global sync failure" if all dialogs fail in a cycle
                    </Details>
                </Task>
                <Deliverable>
                    The worker now generates an AI-based suggestion for each dialog,
                    storing it in the DB. The user can see partial or complete successes.
                </Deliverable>
            </Tasks>
        </Phase>

        <Phase name="Phase 3: Overwriting Logic & Robust Logging">
            <EstimatedDuration>2 days</EstimatedDuration>
            <Tasks>
                <Task>
                    <Name>Overwrite on Next Poll</Name>
                    <Details>
                        - Ensure that suggestions are NOT overwritten within the same poll
                        - If new messages appear in the next cycle, overwrite the old suggestion
                    </Details>
                </Task>
                <Task>
                    <Name>Enhanced Logging & Cycle Summary</Name>
                    <Details>
                        - Implement a final log/record summarizing the total dialogs processed, 
                          failures, and partial successes at the end of each cycle
                    </Details>
                </Task>
                <Task>
                    <Name>Mid-Cycle Crash Recovery</Name>
                    <Details>
                        - Clarify how partial suggestions remain in the DB if the worker crashes
                        - On next startup, re-check unread messages and proceed with fresh suggestions
                    </Details>
                </Task>
                <Deliverable>
                    A fully robust MVP worker that strictly follows the "overwrite on next poll" logic,
                    has detailed logs, and gracefully recovers from mid-cycle failures.
                </Deliverable>
            </Tasks>
        </Phase>
    </TimelineAndTaskBreakdown>

    <!-- ========================================================= -->
    <!-- IMPLEMENTATION GUIDANCE                                  -->
    <!-- ========================================================= -->
    <ImplementationGuidance>
        <Overview>
            The final MVP will include:
            1) A single worker process (worker.py) that runs every 30 minutes.
            2) A 3x retry strategy for both Telegram fetches and AI generation calls.
            3) "One suggestion per dialog" stored in the DB, overwritten only when new messages appear in the next cycle.
            4) Thorough logging for partial failures and global sync failures.
        </Overview>
        
        <SimplifiedApproach>
            <Note>
                This implementation focuses on a simple standalone worker without utilizing the background_tasks
                infrastructure initially. A future iteration will refactor this implementation to leverage the
                background_tasks table and QueueManager for advanced task management.
            </Note>
            
            <FileStructure>
                - app/services/worker.py: Main worker implementation with scheduling logic
                - app/services/dialog_processor.py: Logic for processing dialog messages
                - app/utils/retry.py: Simple retry mechanism for API calls
            </FileStructure>
        </SimplifiedApproach>
        
        <ExistingStructureUtilization>
            <Component name="Database Models">
                - Use Dialog model with is_processing_enabled flag to determine which dialogs to process
                - Use ProcessedResponse model for storing generated responses
                - Use user_selected_models for determining AI model preferences
            </Component>
            
            <Component name="API Services">
                - Utilize existing telegram.py for fetching messages
                - Use llm_api.py for generating AI responses
            </Component>
        </ExistingStructureUtilization>
        
        <MarkAsRead>
            Note: The worker does NOT mark messages as read. When the user sends the AI suggestion through the app,
            the main application logic handles marking the Telegram dialog as read.
        </MarkAsRead>
        
        <POCCodeIntegration>
            The DialogProcessor POC code (reply_only_llama3.2.py) provides valuable guidance for constructing effective
            prompts for the AI models. This logic should be adapted and incorporated into the dialog processing logic.
        </POCCodeIntegration>
    </ImplementationGuidance>

    <!-- ========================================================= -->
    <!-- INTEGRATION WITH EXISTING DATABASE                        -->
    <!-- ========================================================= -->
    <DatabaseIntegration>
        <ExistingTables>
            <Table name="dialogs">
                <RelevantFields>
                    <Field name="id" notes="Primary UUID key" />
                    <Field name="telegram_dialog_id" notes="Unique identifier from Telegram" />
                    <Field name="user_id" notes="Reference to the user" />
                    <Field name="is_processing_enabled" notes="Boolean flag to indicate if this dialog should be processed" />
                    <Field name="auto_send_enabled" notes="Boolean flag to indicate if responses should be auto-sent" />
                    <Field name="last_processed_message_id" notes="ID of the last message that was processed" />
                    <Field name="last_processed_at" notes="Timestamp of when the dialog was last processed" />
                </RelevantFields>
                <Usage>
                    The worker should query for dialogs where is_processing_enabled=True to determine which
                    dialogs to process. After processing, update last_processed_message_id and last_processed_at.
                </Usage>
            </Table>

            <Table name="processed_responses">
                <RelevantFields>
                    <Field name="id" notes="Primary UUID key" />
                    <Field name="dialog_id" notes="Reference to the dialog" />
                    <Field name="last_message_id" notes="ID of the last message in the dialog when processed" />
                    <Field name="suggested_response" notes="AI-generated response text" />
                    <Field name="status" notes="Current status (PENDING_APPROVAL, APPROVED, REJECTED, SENT, FAILED)" />
                    <Field name="model_name" notes="Name of the AI model used for generation" />
                    <Field name="error" notes="Error details if processing failed" />
                </RelevantFields>
                <Usage>
                    Store AI-generated responses in this table with status=PENDING_APPROVAL initially.
                    Update existing records if new messages arrive in a dialog that already has a response.
                    The unique constraint on dialog_id ensures one response per dialog.
                </Usage>
            </Table>

            <Table name="user_selected_models">
                <RelevantFields>
                    <Field name="user_id" notes="Reference to the user" />
                    <Field name="model_id" notes="ID of the selected AI model" />
                    <Field name="is_active" notes="Whether this model selection is active" />
                </RelevantFields>
                <Usage>
                    Query this table to determine which AI model to use for generating responses based on
                    user preferences. Fall back to a default model if no selection exists.
                </Usage>
            </Table>
        </ExistingTables>
    </DatabaseIntegration>
    
    <!-- ========================================================= -->
    <!-- FUTURE IMPROVEMENTS                                      -->
    <!-- ========================================================= -->
    <FutureImprovements>
        <BackgroundTasksIntegration>
            After the initial MVP is working correctly, a future iteration should refactor the implementation to:
            
            1) Utilize the background_tasks table for task tracking
            2) Implement a proper QueueManager for task prioritization and scheduling
            3) Add task monitoring and management API endpoints
            4) Implement more advanced error recovery mechanisms
            
            This will provide better scalability, monitoring, and management capabilities while maintaining
            the core functionality established in the MVP.
        </BackgroundTasksIntegration>
        
        <AdvancedFeatures>
            <AutoResponseSending>
                For dialogs with auto_send_enabled=True, implement logic to automatically send responses
                without requiring user approval.
            </AutoResponseSending>
            
            <DialogPrioritization>
                Add logic to prioritize processing of dialogs based on factors like unread count or importance.
            </DialogPrioritization>
        </AdvancedFeatures>
    </FutureImprovements>

    <!-- ========================================================= -->
    <!-- POC CODE SNIPPET: reply_only_llama3.2.py                  -->
    <!-- ========================================================= -->
    <POCFile name="reply_only_llama3.2.py">
        <![CDATA[
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
        """Validate the format of a single dialog"""
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

            m['message_text'] = self._clean_text(m.get('message_text', ''))
            valid_messages.append(m)

        try:
            # Sort by message_date
            return sorted(valid_messages, key=lambda x: x['message_date'])
        except KeyError:
            return []

    def _is_valid_message(self, msg: Dict) -> bool:
        """Validate the structure of a message"""
        if not isinstance(msg, dict):
            return False

        required_keys = ['message_date', 'sender_name', 'message_text']
        if any(key not in msg for key in required_keys):
            return False

        text = msg.get('message_text', '')
        return isinstance(text, str) and len(text.strip()) >= 1

    def _clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        text = str(text) if text is not None else ""
        # Remove non-ASCII except basic extended sets, fuzzify mentions, etc.
        text = re.sub(r'[^\x00-\x7F\u4e00-\u9fa5]', '', text)
        text = re.sub(r'@\w+\b', '[User mention]', text)
        text = re.sub(r'http\S+', '[Link]', text)
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
        """Final safety filtering"""
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text.split()) < 3:
            return "Please provide more details."

        invalid_patterns = [
            r'\[\w+\]',
            r'\.{3,}',
            r'\b(n/a|undefined)\b'
        ]
        for p in invalid_patterns:
            text = re.sub(p, '', text)

        return text[:250].strip() or "Awaiting your further instructions."


if __name__ == '__main__':
    print("🚀 Dialog processing system started")

    processor = DialogProcessor()
    data_path = ""  # Fill in an actual path to JSON containing dialogs
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
        ]]>
    </POCFile>

    <!-- ========================================================= -->
    <!-- END OF PROJECT DOC                                       -->
    <!-- ========================================================= -->

</ProjectDoc>
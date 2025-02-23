# telegram_AI_Processor
Project Overview
This project contains two main Python scripts: tg_data_downloader.py and reply_only_llama3.2.py, which jointly complete the task of downloading data from Telegram and processing conversations.
Project Structure
tg_data_downloader.py
This script is mainly responsible for downloading data from Telegram. The specific functions are as follows:
Initialize the Telegram client: Use the Telethon library to initialize a Telegram client. You need to provide API_ID and API_HASH.
Get unread messages: Obtain all conversations in Telegram, filter out unread messages, including group chats and private messages.
Filter relevant messages: Check whether the message contains the target keyword (set through the environment variable TARGET_KEYWORD), and filter out relevant messages within the last 24 hours.
Merge messages: Merge the unread messages of each conversation with the last 20 historical messages, and remove duplicate messages.
Export data: Export the last 20 messages of each conversation to the telegram_data.json file.
Call the local data processor: Call the reply_only_llama3.2.py script to process the exported data.
reply_only_llama3.2.py
This script is mainly responsible for processing the conversation data downloaded from Telegram. The specific functions are as follows:
Initialize the language model: Use the llama_cpp library to initialize a language model. You need to provide configuration information such as the model path.
Verify and process conversation data: Verify the format of the conversation data, and preprocess the messages, including cleaning the message content, sorting, etc.
Generate replies: Build prompts based on the preprocessed messages, call the language model to generate replies, and post-process the replies, including basic cleaning, filtering out invalid content, etc.
Output results: Print and output the processed results.
Environment Configuration
Environment Variables
Create a .env file in the root directory of the project with the following content:

API_ID=your_api_id
API_HASH=your_api_hash
TARGET_KEYWORD=your_target_keyword
DATA_DIR=your_data_directory
PROCESSOR_SCRIPT_NAME=reply_only_llama3.2.py
PYTHON_PATH=python3
